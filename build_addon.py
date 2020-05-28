import os
import shutil
import zipfile


addon_name = "CalendarSync"
addon_root_folder = "CalendarSync"
build_folder = "build/addon"
extra_archive_files = ["CHANGELOG.md"] #, "LICENSE.txt"]


def build():
    """Package the addon to a folder and return the output path."""
    version_num = 0

    with open(os.path.join(addon_root_folder, "CalendarSync.toc"), 'r') as toc_file:
        for line in toc_file:
            if "## Version:" in line:
                version_num = line.split()[2]

    print("Building AddOn version " + version_num)

    base_release_folder = os.path.join(build_folder, version_num)
    release_zip_path = os.path.join(base_release_folder, addon_name + "_" + version_num)
    release_folder_path = os.path.join(base_release_folder, addon_name)

    if os.path.exists(base_release_folder):
        shutil.rmtree(base_release_folder)

    shutil.copytree(addon_root_folder, release_folder_path)
    for extra_file in extra_archive_files:
        shutil.copy(os.path.join(addon_root_folder, extra_file), os.path.join(release_folder_path, extra_file))

    shutil.make_archive(release_zip_path, "zip", os.path.join(release_folder_path, os.pardir), os.path.basename(release_folder_path))

    return base_release_folder


if __name__ == "__main__":
    build()
