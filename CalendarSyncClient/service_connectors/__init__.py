import configparser
import logging
import os
from abc import abstractmethod, ABCMeta
from enum import IntEnum, unique, auto
from pathlib import Path
from sys import exit
from typing import Any, NewType, Mapping, Sequence

SERVICE_DATA_ROOT = "data/"

# Type that identifies a calendar on the remote service.
CalendarID = NewType("CalendarID", Any)
# Type representing an event returned by the remote service.
RemoteEvent = NewType("RemoteEvent", Any)
# Type representing an event parsed from the AddOn SavedVariables.
AddonEvent = NewType("AddonEvent", Mapping[str, Any])
"""AddonEvent spec:
["title"] = "Some Title",
["startTime"] = 1000000000,
["endTime"] = 1000000000,
["eventID"] = 1111111,
["creator"] = "Player Name",
["description"] = "Event description",
"""


@unique
class EventComparisonResult(IntEnum):
    EQUAL = auto()
    UPDATED = auto()
    DIFFERENT = auto()


class ServiceConnector(metaclass=ABCMeta):
    """ Base class for API services."""

    def __init__(self, service_file, config):
        self.service_name = os.path.splitext(os.path.basename(service_file))[0]
        self.data_path = os.path.join(SERVICE_DATA_ROOT, self.service_name)
        self.config = config
        self.logger = logging.getLogger(self.service_name)

    def get_data_file_path(self, file_name):
        if not os.path.exists(self.data_path):
            Path(self.data_path).mkdir(parents=True, exist_ok=True)
        return os.path.join(self.data_path, file_name)

    def get_config_option(self, option):
        try:
            return self.config[option]
        except (KeyError, configparser.NoSectionError, configparser.NoOptionError) as e:
            self.logger.error("{0} not found in service config, check options.ini. See example_options for help.".format(option, self.service_name))
            input()
            exit()

    @abstractmethod
    def get_calender_id_by_name(self, calendar_name: str) -> CalendarID:
        """Return a calendar identifier for the specified calendar name,
        or None if the requested calendar doesn't exist.
        """
        ...

    @abstractmethod
    def create_calendar(self, calendar_name: str) -> CalendarID:
        """Create a calendar on the remote service with the specified name.
        Return an identifier for making requests to that calendar."""
        ...

    @abstractmethod
    def create_event(self, calendar_id: CalendarID, addon_event: AddonEvent):
        """Create an event on the remote service with the specified name.
        Return an identifier for making requests to that calendar."""
        ...

    @abstractmethod
    def remove_event(self, calendar_id: CalendarID, remote_event: RemoteEvent):
        """Remove the specified event, as returned from get_events, from the specified calendar."""
        ...

    @abstractmethod
    def update_event(self, calendar_id: CalendarID, remote_event: RemoteEvent, addon_event: AddonEvent):
        """Update the specified remote event to match the new addon_event data."""
        ...

    @abstractmethod
    def get_event(self, calendar_id: CalendarID, addon_event: AddonEvent) -> RemoteEvent or None:
        """Get the remote event for an addon event, or None if it doesn't exist."""
        ...

    @abstractmethod
    def get_events(self, calendar_id: CalendarID, lookahead_days: int) -> Sequence[RemoteEvent]:
        ...

    @abstractmethod
    def compare_events(self, addon_event: AddonEvent, remote_event: RemoteEvent) -> EventComparisonResult:
        """Return the relationship between the addon_event and the relating remote event from get_events."""
        ...

    @abstractmethod
    def event_tostring(self, remote_event: RemoteEvent) -> str:
        """Return a string representation of the specified remote event from get_events."""
        ...
