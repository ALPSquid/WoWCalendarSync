from typing import Sequence

from . import ServiceConnector, EventComparisonResult, CalendarID, RemoteEvent, AddonEvent


class ExampleServiceConnector(ServiceConnector):
    """An example connector showing structure and setup."""

    def __init__(self, config):
        # Pass __file__ here as we want the service name to match the file name throughout configs, dirs, logging etc.
        super().__init__(__file__, config)

    def get_calender_id_by_name(self, calendar_name: str) -> CalendarID:
        pass

    def create_calendar(self, calendar_name: str) -> CalendarID:
        pass

    def create_event(self, calendar_id: CalendarID, addon_event: AddonEvent):
        pass

    def remove_event(self, calendar_id: CalendarID, remote_event: RemoteEvent):
        pass

    def update_event(self, calendar_id: CalendarID, remote_event: RemoteEvent, addon_event: AddonEvent):
        pass

    def get_events(self, calendar_id: CalendarID, lookahead_days: int) -> Sequence[RemoteEvent]:
        pass

    def compare_events(self, addon_event: AddonEvent, remote_event: RemoteEvent) -> EventComparisonResult:
        pass

    def event_tostring(self, remote_event: RemoteEvent) -> str:
        pass


# Called when the module gets imported. Config is the service specific config section.
def get_connector(config) -> ServiceConnector:
    return ExampleServiceConnector(config)
