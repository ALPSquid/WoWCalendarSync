import os
import re
import shutil

from cx_Freeze import setup, Executable

with open("CalendarSyncClient/sync_client.py", 'r') as client_file:
    for line in client_file:
        stripped_line = line.replace(" ", "")
        if "VERSION=" in stripped_line:
            version_num = re.sub("[\"'\\n]", "", stripped_line.split("=")[1])
            break

if not version_num:
    raise Exception("Couldn't find VERSION in sync_client.py")

build_path_win = "build/{0}/win32".format(version_num)
if os.path.exists(build_path_win):
    shutil.rmtree(build_path_win)

# Note: Google API Client doesn't play ball with building.
# See: https://stackoverflow.com/questions/56766092/cx-freeze-importerror-cannot-import-name-vision/56787860#56787860
build_exe_options = {
    "build_exe": build_path_win,
    "packages": [
        "CalendarSyncClient\\service_connectors",
        "google",
        "googleapiclient",
        "httplib2"
    ],
    "includes": [
        "sys",
    ],
    "excludes": [
        "distutils",
        "lib2to3",
        "pydoc_data"
        "test",
        "tkinter",
        "unittest",
    ],
    "include_files": ["CalendarSyncClient\\example_options.ini"],
    "optimize": 2
}

setup(name="WoW Calendar Sync Client",
      description="Client for syncing WoW calendar events to an external service. Requires the CalendarSync AddOn.",
      version=version_num,
      author="Andy Palmer",
      url="https://github.com/ALPSquid/WoWCalendarSync",
      options={"build_exe": build_exe_options},
      executables=[Executable(
          "CalendarSyncClient\\sync_client.py",
          base=None,
          targetName="WoW CalendarSync Client"
      )])

# Hacky move to correct the package imports as this setup runs from a directory higher than the actual script.
shutil.move(os.path.join(build_path_win, "lib\\CalendarSyncClient\\service_connectors"), os.path.join(build_path_win, "lib\\service_connectors"))
os.rmdir(os.path.join(build_path_win, "lib\\CalendarSyncClient"))