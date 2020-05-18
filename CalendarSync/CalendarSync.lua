--
-- Part of the CalendarSync AddOn
-- Author: Aerthok - Defias Brotherhood EU
--

local _, ns = ...

local CalendarSync = LibStub("AceAddon-3.0"):NewAddon("Calendar Sync", "AceConsole-3.0", "AceTimer-3.0", "AceEvent-3.0", "AceHook-3.0")
ns.CalendarSync = CalendarSync

SYNC_DELAY = 5

local dataDefaults = 
{
    profile = 
    {
        debugMode = false,

        lookaheadDays = 30,
        calendars = 
        {
            ---@class AddonEvent
            ---@field eventID number
            ---@field title string
            ---@field description string
            ---@field creator string
            ---@field startTime number  UTC timestamp.
            ---@field endTime number  UTC timestamp.

            -- Guild/Club Name = { events = AddonEvent[] }
        }
    }
}

function CalendarSync:OnInitialize()
        -- Load database
        self.db = LibStub("AceDB-3.0"):New("CalendarSyncDB", dataDefaults, true)
        if self.db.profile.calendars == nil then
            self.db.profile.calendars = {}
        end

        -- Var reset.
        self:StopEventDescriptionRequests()
end

function CalendarSync:OnEnable()
    self:RegisterChatCommand("calendarsync", "CalendarSyncCommand")

    self:RegisterEvent("CALENDAR_UPDATE_EVENT", self.ScheduleCalendarSync, self)
    self:RegisterEvent("CALENDAR_UPDATE_EVENT_LIST", self.ScheduleCalendarSync, self)
    self:RegisterEvent("CALENDAR_UPDATE_GUILD_EVENTS", self.ScheduleCalendarSync, self)
    self:RegisterEvent("CALENDAR_OPEN_EVENT", self.OnEventOpened, self)
    self:RegisterEvent("CALENDAR_ACTION_PENDING", self.OnActionPending, self)

    CalendarFrame:HookScript("OnShow", function(_)
        CalendarSync:PrintDebugMessage("Calendar frame shown.")
        CalendarSync.calendarFrameShown = true
        CalendarSync:CancelSync()
    end)

    CalendarFrame:HookScript("OnHide", function(_)
        CalendarSync:PrintDebugMessage("Calendar frame hidden.")
        CalendarSync.calendarFrameShown = false
        self:ScheduleCalendarSync()
    end)

    self:ScheduleCalendarSync()
end

function CalendarSync:OnDisable()
    self:UnregisterChatCommand("calendarsync")
    self:UnregisterEvent("CALENDAR_UPDATE_EVENT")
    self:UnregisterEvent("CALENDAR_UPDATE_EVENT_LIST")
    self:UnregisterEvent("CALENDAR_UPDATE_GUILD_EVENTS")
    self:UnregisterEvent("CALENDAR_OPEN_EVENT")
    self:UnregisterEvent("CALENDAR_ACTION_PENDING")

    CalendarFrame:UnhookAll()
end

function CalendarSync:CalendarSyncCommand()
    self.UI:Show()
end

function CalendarSync:CanSync()
    return not self.calendarFrameShown
end

function CalendarSync:ScheduleCalendarSync()
    if self.activeSyncTimer ~= nil then
        self:CancelTimer(self.activeSyncTimer)
    end

    self.activeSyncTimer = self:ScheduleTimer(self.SyncCalendar, SYNC_DELAY, self)
end

function CalendarSync:CancelSync()
    if self.activeSyncTimer ~= nil then
        self:CancelTimer(self.activeSyncTimer)
    end
    self:StopEventDescriptionRequests()
end

--region Utils
function CalendarSync:PrintDebugMessage(msg)
    if self.db.profile.debugMode then
        print("[CalendarSync][DEBUG] "..msg)
    end
end

function CalendarSync:PrintAddOnMessage(msg)
    print("[CalendarSync] "..msg)
end

local serverUtcOffset = nil
function CalendarSync:GetServerOffset()
    if serverUtcOffset ~= nil then
        return serverUtcOffset
    end

    local serverDate = C_DateAndTime.GetCurrentCalendarTime()
    serverDate.day = serverDate.monthDay
    serverDate.min = serverDate.minute

    local localDate = date("*t", time())
    -- Get the diff between local and server time. Can't use UTC time for this as time() converts to local time.
    serverLocalOffset = difftime(time(serverDate), time(localDate))
    serverUtcOffset = serverLocalOffset
    -- Round to nearest quarter hour since the above calculation can sometimes be a couple minutes out and 15mins is the smallest timezone interval.
    round_interval = 15 * 60
    local serverOffsetRoundedDown = serverUtcOffset - (serverUtcOffset % round_interval)
    local serverOffsetRoundedUp = serverOffsetRoundedDown + round_interval
    if serverUtcOffset - serverOffsetRoundedDown < serverOffsetRoundedUp - serverUtcOffset then
        serverUtcOffset = serverOffsetRoundedDown
    else
        serverUtcOffset = serverOffsetRoundedUp
    end
    self:PrintDebugMessage("Server offset is " .. serverUtcOffset .. " = " .. (serverUtcOffset / 60 / 60) .. "hrs")
    return serverUtcOffset
end

function CalendarSync:CalendarTimeToUTCTimestamp(calendarTime)
    calendarTime.day = calendarTime.monthDay
    calendarTime.min = calendarTime.minute

    -- Since time converts the date to local time, we can apply the server-local offset to server time which will result in a UTC timestamp.
    return time(calendarTime) - CalendarSync:GetServerOffset()
end

function CalendarSync:GetCalendarTimeBetween(startTime, endTime)
    startTime.day = startTime.monthDay
    startTime.min = startTime.minute
    endTime.day = endTime.monthDay
    endTime.min = endTime.minute
    local timeDiff = difftime(time(endTime), time(startTime))
    local dateDiff = date("*t", timeDiff)

    return
    {
        year = dateDiff.year or 0,
        month = dateDiff.month or 0,
        monthDay = dateDiff.monthDay or 0,
        weekDay = dateDiff.wday or 0,
        hour = dateDiff.hour or 0,
        minute = dateDiff.minute or 0,
    }
end
--endregion

function CalendarSync:SyncCalendar()
    if not self:CanSync() then
        self:PrintAddOnMessage("CanSync() returned false. Skipping calendar sync.")
        return
    end
    self:PrintAddOnMessage("Running calendar sync")
    self:StopEventDescriptionRequests()

    -- TODO: Sync all clubs. Option to disable certain ones in sync app or addon config.
    local guildName = C_Club.GetClubInfo(C_Club.GetGuildClubId()).name
    local currentServerTime = C_DateAndTime.GetCurrentCalendarTime()
    local upcomingEvents = C_Calendar.GetClubCalendarEvents(C_Club.GetGuildClubId(), currentServerTime, C_DateAndTime.AdjustTimeByDays(currentServerTime, self.db.profile.lookaheadDays))

    if self.db.profile.calendars[guildName] == nil then
        self.db.profile.calendars[guildName] = {}
    end
    self.db.profile.calendars[guildName].events = {}

    for _, event in ipairs(upcomingEvents) do
        local startTimestamp = CalendarSync:CalendarTimeToUTCTimestamp(event.startTime)
        local endTimestamp = CalendarSync:CalendarTimeToUTCTimestamp(event.endTime)
        self:PrintDebugMessage(format("Event: %s @ %i:%i - %i:%i", event.title, event.startTime.hour, event.startTime.minute, event.endTime.hour, event.endTime.minute))

        if endTimestamp <= startTimestamp then
            -- Add 30 mins to the end time if there is no set end time
            endTimestamp = startTimestamp + 30 * 60
        end

        local eventData =
        {
            eventID = event.eventID,
            title = event.title,
            description = "",
            creator = event.invitedBy,
            startTime = startTimestamp,
            endTime = endTimestamp
        }
        table.insert(self.db.profile.calendars[guildName].events, eventData)
    end

    -- For whatever reason the description is left out and has to be requested individually, one request at a time.
    self:RequestEventDescriptions(guildName)
end

-- Request Event for getting the description.
-- If index not supplied, will start at 1.
function CalendarSync:RequestEventDescriptions(clubName, index)
    self.currentEventRequestIndex = index or 1
    self.currentEventRequestClubName = clubName

    local event = self.db.profile.calendars[self.currentEventRequestClubName].events[self.currentEventRequestIndex]
    if not event then
        return
    end
    local eventIndexInfo = C_Calendar.GetEventIndexInfo(event.eventID)
    self:PrintDebugMessage("Requesting " .. event.eventID .. " - " .. event.title)

    C_Calendar.OpenEvent(eventIndexInfo.offsetMonths, eventIndexInfo.monthDay, eventIndexInfo.eventIndex)
end

function CalendarSync:StopEventDescriptionRequests()
    self.currentEventRequestIndex = -1
    self.currentEventRequestClubName = nil
end

function CalendarSync:OnEventOpened()
    if self.currentEventRequestIndex < 1 then
        return
    end

    local selectedEvent = C_Calendar.GetEventInfo()
    if selectedEvent ~= nil then
        CalendarSync:PrintDebugMessage("Opened event: " .. selectedEvent.title)
        self.db.profile.calendars[self.currentEventRequestClubName].events[self.currentEventRequestIndex].description = selectedEvent.description
        CalendarSync:PrintDebugMessage("Got description: " .. selectedEvent.description)
    end

    C_Calendar.CloseEvent()
end

function CalendarSync:OnActionPending(_, pending)
    if not pending and not C_Calendar.IsEventOpen() and self.currentEventRequestIndex >= 1 then
        if self.currentEventRequestIndex < #self.db.profile.calendars[self.currentEventRequestClubName].events then
            self:RequestEventDescriptions(self.currentEventRequestClubName, self.currentEventRequestIndex + 1)
        else
            self:StopEventDescriptionRequests()
        end
    end
end