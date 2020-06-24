import os
import pickle
from datetime import datetime
from functools import wraps
from typing import Sequence

import pytz
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from . import ServiceConnector, CalendarID, EventComparisonResult, RemoteEvent, AddonEvent

CLIENT_SCOPES = ['https://www.googleapis.com/auth/calendar']
# Custom addition to append to the description as GCal doesn't support arbitrary creator strings.
CREATED_BY_STRING = "\n\n~ Created by"


def requires_google_auth(f):
    """ Decorator for methods requiring google OAuth authorisation.
    "credentials" and "api" will be set on the calling object.
    """
    @wraps(f)
    def wrapper(service_connector: ServiceConnector, *args, **kwargs):
        reauth_required = False
        token_file_path = service_connector.get_data_file_path("token.pickle")
        credentials_file_path = service_connector.get_config_option("CredentialsFile")

        if not service_connector.credentials:
            if os.path.exists(token_file_path):
                with open(token_file_path, "rb") as token_file:
                    service_connector.credentials = pickle.load(token_file)

        if not service_connector.credentials or not service_connector.credentials.valid:
            if service_connector.credentials and service_connector.credentials.expired and service_connector.credentials.refresh_token:
                service_connector.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, CLIENT_SCOPES)
                service_connector.credentials = flow.run_local_server(port=8080)

            with open(token_file_path, "wb") as token_file:
                pickle.dump(service_connector.credentials, token_file)
            reauth_required = True

        if not service_connector.api or reauth_required:
            service_connector.api = build("calendar", "v3", credentials=service_connector.credentials, cache_discovery=False)

        return f(service_connector, *args, **kwargs)

    return wrapper


class GoogleCalendarServiceConnector(ServiceConnector):

    def __init__(self, config):
        super().__init__(__file__, config)
        self.api = None
        self.credentials = None

    @requires_google_auth
    def get_calender_id_by_name(self, calendar_name: str) -> CalendarID:
        calendars = self.api.calendarList().list().execute()
        for calendar in calendars["items"]:
            if calendar["summary"] == calendar_name:
                return calendar["id"]

        return None

    @requires_google_auth
    def create_calendar(self, calendar_name: str) -> CalendarID:
        new_calendar = {
            "summary": calendar_name,
            "timeZone": "UTC"
        }
        return self.api.calendars().insert(body=new_calendar).execute()["id"]

    @requires_google_auth
    def create_event(self, calendar_id: CalendarID, addon_event: AddonEvent):
        start_datetime = datetime.fromtimestamp(addon_event["startTime"], tz=pytz.utc)
        end_datetime = datetime.fromtimestamp(addon_event["endTime"], tz=pytz.utc)

        event_data = {
            "id": addon_event["eventID"],
            "summary": addon_event["title"],
            "description": "{0} {1} {2}".format(addon_event["description"], CREATED_BY_STRING, addon_event["creator"]),
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": "UTC"
            }
        }
        self.api.events().insert(calendarId=calendar_id, body=event_data).execute()

    @requires_google_auth
    def remove_event(self, calendar_id: CalendarID, remote_event: RemoteEvent):
        self.api.events().delete(calendarId=calendar_id, eventId=remote_event["id"]).execute()

    @requires_google_auth
    def update_event(self, calendar_id: CalendarID, remote_event: RemoteEvent, addon_event: AddonEvent):
        event_data = {
            "summary": addon_event["title"],
            "description": "{0} {1} {2}".format(addon_event["description"], CREATED_BY_STRING, addon_event["creator"]),
        }
        self.api.events().patch(calendarId=calendar_id, eventId=remote_event["id"], body=event_data).execute()

    @requires_google_auth
    def get_event(self, calendar_id: CalendarID, addon_event: AddonEvent) -> RemoteEvent or None:
        try:
            return self.api.events().get(calendarId=calendar_id, eventId=addon_event["eventID"]).execute()
        except HttpError:
            return None

    @requires_google_auth
    def get_events(self, calendar_id: CalendarID, lookahead_days: int) -> Sequence[RemoteEvent]:
        now = datetime.utcnow().isoformat() + "Z"
        events = self.api.events().list(calendarId=calendar_id, timeMin=now,
                                        # Assume max of 10 events a day for results
                                        maxResults=lookahead_days * 10, singleEvents=True,
                                        orderBy="startTime").execute()
        return events.get("items")

    def compare_events(self, addon_event: AddonEvent, remote_event: RemoteEvent) -> EventComparisonResult:
        # Note: if an event is deleted on the remote, we won't be able to recreate it as IDs aren't released.
        # For now, we'll stick with this and assume the user complies with the no remote changes policy.
        # The alternative is to compare times and titles, which allows reuse but is messier and
        # may result in incorrect results when updating or removing events.
        if int(addon_event["eventID"]) == int(remote_event["id"]):
            if addon_event["description"].strip() == remote_event["description"].split(CREATED_BY_STRING)[0].strip():
                return EventComparisonResult.EQUAL
            else:
                return EventComparisonResult.UPDATED

        return EventComparisonResult.DIFFERENT

    def event_tostring(self, remote_event: RemoteEvent) -> str:
        return "{0} - {1}".format(remote_event["summary"], remote_event["start"]["dateTime"])


def get_connector(config) -> ServiceConnector:
    return GoogleCalendarServiceConnector(config)
