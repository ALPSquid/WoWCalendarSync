# WoW Calendar Sync
A combination AddOn and client that exports calendar events from World of Warcraft and one-way syncs them to an external calendar service, such as Google Calendar.

## Contents
1. [Features](#features)
2. [Requirements](#requirements)
3. [Usage](#usage)
4. [Config](#config)
    * [Google Calendar](#google-calendar)
5. [Creating a ServiceConnector](#creating-a-serviceconnector)

## Features
* One-way sync of all Guild events to an external calendar . (Support for all communities you're in may come in the future).
* Sync to:
    * **Google Calendar** - This will create a new calendar with the name of your guild on your account specifically for Guild events.

## Requirements
**If using a packaged build** (Coming soon):
* Download the latest release from [releases](https://github.com/ALPSquid/WoWCalendarSync/releases) and unzip somewhere.

**If running from source**:
 * Python 3.8+
    * pytz
    * slpp
    * watchdog
    * Google Service Modules:
        * google-api-python-client
        * google-auth-httplib2
        * google-auth-oauthlib

## Usage
1. Copy the **CalendarSync** folder to **World of Warcraft\\\_retail_\Interface\AddOns** and run the game once for the calendar to sync. 
2. In the **CalendarSyncClient** folder, update your **options.ini** file as described in the [Client Config](#client-config) section of this ReadMe.
3. Run the **CalendarSyncClient.exe** (or sync_client.py from within the CalendarSyncClient folder if running from source). It will automatically watch the AddOn data file and sync when changes are detected.

## Client Config

1. First, setup the AddOn and download the Client as defined in [Requirements](#requirements) and [Usage](#usage) sections.
2. In the **CalendarSyncClient** folder, make a copy of **example_options.ini** and rename it **options.ini**
3. Fill out the sections in your new **options.ini** as described in the comments in the file. Namely the path to the AddOn save file. 

Details on how to configure each service can be found below:
* [Google Calendar](#google-calendar)

### Google Calendar
**Warning:** Do not modify the remote calendar. Any new events will be deleted by the client and deleted events that have not also been deleted from the WoW calendar will not be recreated.

Using the Google Calendar Service requires setup of an API Project with the Google Calendar API enabled. To do this:
1. Head to [https://console.developers.google.com/projectcreate](https://console.developers.google.com/projectcreate)
2. Enter a project name. Something like **wow-calendar-sync**.
3. Press **Create** to create the new project.
4. Open the **Navigation Menu** (3 lines in the top left) and click **API & Services**.
5. Click **+ Enable APIs and Services**.
6. Search for **calendar** and select **Google Calendar API**.
7. Click **Enable** to enable the Calendar API in your new project.
8. Once the API has been enabled, go back to **API & Services** from the **Navigation Menu**
9. Click **OAuth Consent Screen** in the left-hand menu.
10. Under ***User Type*** select **External**.
11. Click **Create**.
12. Enter an **Application Name** of your choice. Something like *WoW Calendar Sync*. You can skip the logo.
13. At the bottom, click **Save**.
14. In the left-hand menu, click **Credentials**.
15. At the top, click **+ Create Credentials** then **OAuth client ID**.
16. For ***Applicantion type*** select **Desktop app**. 
17. Give your client a name so you know what you're using these credentials for. Something like *WoW Calendar Sync*.
18. Click **Create** then **OK** on the resulting pop-up.

You're API project is ready to go! Let's download the credentials we just created and update the Calendar Sync Client.

1. In the **Credentials** section of your API project, under **OAuth 2.0 Client IDs**, click the **download arrow** on the right of the credentials you just created.
2. Save the downloaded file and copy the full path to it. Feel free to rename the file to something more meaningful. We'll use **calendarsync_gcal_credentials.json** for this.
  Our file path looks something like **C:\Users\YourName\Documents\Credentials\calendarsync_gcal_credentials.json**
3. Open the CalendarSyncClient **options.ini** file you created at the start of the **Client Config** section.
4. Under **[google_calendar]**, paste the path to your credentials file for the **CredentialsFile** option.
    * Example: **CredentialsFile=C:\Users\YourName\Documents\Credentials\calendarsync_gcal_credentials.json**
5. Under **[Services]** ensure the **EnabledServices** option has **google_calendar** in it.
    * Example: **EnabledServices=google_calendar**

Congratulations! You're all setup and ready to sync to Google Calendar! 

When you first run the client, it will open a browser window asking you to authorise the app. It will warn you that "This app isn't verified" since we just created it and it's for personal use. To bypass this, click **Advanced** then **Go to \<your application name\> (unsafe)**.


## Creating a ServiceConnector
A ServiceConnector is the bridge between the client and an external service. For now, the syncing algorithm is handled within the main client and uses the ServiceConnector for specific interactions with the external service. The external service could be anything from Google Calendar to a text file.

New ServiceConnectors should be added to the **service_connectors** directory where the file name will be the ID used in the config and for importing the module. For example, **google_calendar**. 

Take a look at **example_connector.py** for implementation details. It consists of two things:
1. A class that implements **ServiceConnector**
2. A function that returns a new instance of your connector and passes the service-specific config to your connector.

Once you've created your ServiceConnector, simply add a config entry for it using the file name and append it to the **EnabledServices** option.

If you've made a new connector, please do submit a Pull Request and we'll get it merged in!