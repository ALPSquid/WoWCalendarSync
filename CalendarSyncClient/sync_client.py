import configparser
import importlib
import logging
import os
import threading
import time
from collections.abc import Sequence
from datetime import datetime
from sys import exit
from typing import List

import pytz
from slpp import slpp as lua
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from service_connectors import ServiceConnector, AddonEvent

VERSION = "1.0.0"

logging.basicConfig(format="%(name)s:%(levelname)s: %(message)s", level=logging.WARNING)
CONFIG_PATH = "options.ini"


class SyncClient(object):

    def __init__(self):
        self.logger = logging.getLogger(type(self).__name__)
        self.sync_delay = 5
        self.active_sync_timer = None
        self.sync_in_progress = False

        self.service_connectors: List[ServiceConnector] = []
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_PATH)
        try:
            enabled_services = self.config["Services"]["EnabledServices"]
            enabled_services = enabled_services.strip().split(",")
            if len(enabled_services) < 1 or enabled_services[0] == "":
                raise configparser.NoOptionError("Services", "EnabledServices")

            for service in enabled_services:
                self._load_service_connector(service)

        except (KeyError, configparser.NoSectionError, configparser.NoOptionError) as e:
            self.logger.error("No services enabled. Please set desired services in options.ini. See example_options for help.")
            input()
            exit()

    def _load_service_connector(self, connector_name):
        module = importlib.import_module("."+connector_name, ".service_connectors")
        config = self.config[connector_name]
        connector = getattr(module, "get_connector")(config)
        self.service_connectors.append(connector)

    @property
    def _addon_data_path(self):
        try:
            addon_data_file_path = self.config["AddOn"]["SaveFilePath"]
            if not addon_data_file_path:
                raise configparser.NoOptionError("Addon", "SaveFilePath")
            if not os.path.exists(addon_data_file_path):
                self.logger.error("""Addon save file not found: {0}.
                      Ensure options.ini is correct and you've run the AddOn at least once.""".format(addon_data_file_path))
                input()
                exit()
            return addon_data_file_path
        except (KeyError, configparser.NoSectionError, configparser.NoOptionError) as e:
            self.logger.error("Missing addon path in options.ini. See example_options for help.")
            input()
            exit()

    def run_auto_update(self):
        """Watch the addon data file for changes, scheduling a sync when changes are detected."""
        addon_data_file_path = self._addon_data_path

        addon_data_file_name = os.path.basename(addon_data_file_path)
        addon_data_dir_path = os.path.dirname(addon_data_file_path)

        event_handler = PatternMatchingEventHandler(patterns=["*"+addon_data_file_name], ignore_directories=True)
        event_handler.on_modified = lambda event: self.schedule_sync()

        observer = Observer()
        observer.schedule(event_handler, addon_data_dir_path, recursive=False)
        observer.start()
        print("Watching {0} for changes.".format(addon_data_file_path))
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def schedule_sync(self):
        """Schedule a sync to run after the config sync_delay and any running syncs have completed."""
        if self.active_sync_timer:
            self.active_sync_timer.cancel()
            self.active_sync_timer = None

        if self.sync_in_progress:
            self.active_sync_timer = threading.Timer(self.sync_delay, self.schedule_sync)
        else:
            self.active_sync_timer = threading.Timer(self.sync_delay, self._sync_calendar)
        self.active_sync_timer.start()

    def _sync_calendar(self):
        print("Syncing calendar...")
        self.sync_in_progress = True
        addon_data_file_path = self._addon_data_path

        with open(addon_data_file_path, "r") as data_file:
            combined_lines = str.join("", data_file.readlines())
            # Ensure data is contained in an object.
            if combined_lines[0] != "{":
                combined_lines = "{" + combined_lines + "}"
            addon_data = lua.decode(combined_lines.replace("\\n", "\n"))

        lookahead_days = int(addon_data["CalendarSyncDB"]["profiles"]["Default"]["lookaheadDays"])
        addon_calendars = addon_data["CalendarSyncDB"]["profiles"]["Default"]["calendars"]
        for calendar_name, addon_calendar_data in addon_calendars.items():
            print("Found in-game calendar: {0}".format(calendar_name))
            addon_events = addon_calendar_data["events"]  # type: Sequence[AddonEvent]

            for service in self.service_connectors:
                print("Updating service: {0}".format(service.service_name))
                cal_id = service.get_calender_id_by_name(calendar_name)
                if not cal_id:
                    print("{0} not found, creating it.".format(calendar_name))
                    cal_id = service.create_calendar(calendar_name)

                # Note: We're controlling the sync here to ease service complexity, but it may need to change to
                # a generic service.sync() depending on whether future services can fit in this pattern.

                remote_events = service.get_events(cal_id, lookahead_days)
                # New/updated events.
                for addon_event in addon_events:
                    event_exists = False
                    for remote_event in remote_events:
                        event_comparison = service.compare_events(addon_event, remote_event)
                        if event_comparison is event_comparison.UPDATED:
                            event_exists = True
                            print("\nUpdating event: {0}.".format(service.event_tostring(remote_event)))
                            service.update_event(cal_id, remote_event, addon_event)
                            break

                        elif event_comparison is event_comparison.EQUAL:
                            event_exists = True
                            break

                    if not event_exists:
                        start_datetime = datetime.fromtimestamp(addon_event["startTime"], tz=pytz.utc)
                        end_datetime = datetime.fromtimestamp(addon_event["endTime"], tz=pytz.utc)
                        description = addon_event["description"] if "description" in addon_event else "null"

                        print("\nCreating new event:")
                        print("\t {0} - {1}".format(start_datetime.isoformat(), end_datetime.isoformat()))
                        print("\t" + addon_event["title"])
                        print("\t- " + addon_event["creator"])
                        print("\t" + description)
                        print("\t--")

                        service.create_event(cal_id, addon_event)

                # Removed events.
                for remote_event in remote_events:
                    event_exists = False
                    for addon_event in addon_events:
                        event_comparison = service.compare_events(addon_event, remote_event)
                        if event_comparison is not event_comparison.DIFFERENT:
                            event_exists = True
                            break

                    if not event_exists:
                        print("\n{0}\n\tNo longer exists, removing".format(service.event_tostring(remote_event)))
                        service.remove_event(cal_id, remote_event)

        print("Sync complete")
        self.sync_in_progress = False


if __name__ == "__main__":
    sync_client = SyncClient()
    sync_client.schedule_sync()
    sync_client.run_auto_update()
