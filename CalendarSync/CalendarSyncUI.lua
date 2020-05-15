--
-- Part of the CalendarSync AddOn
-- Author: Aerthok - Defias Brotherhood EU
--

local _, ns = ...
local CalendarSync = ns.CalendarSync

local CALENDARSYNC_UI_CONFIG =
{
    name = "Calendar Sync",
    handler = CalendarSync,
    type = "group",
    args =
    {
        settingsPanel =
        {
            type = "group",
            name = "Settings",
            inline = true,
            order = 1,
            args =
            {
                lookaheadDays_Title =
                {
                    type = "description",
                    order = 1.11,
                    fontSize = "medium",
                    name = "Lookahead Days"
                },

                lookaheadDays_Entry =
                {
                    type = "input",
                    name = "How many days in advance to get events for:",
                    width = "full",
                    validate = function(info, val)
                        local numberVal = tonumber(val)
                        if not numberVal then
                            return "Number of days lookahead must be a number."
                        end
                        -- Cap it at something reasonable.
                        if numberVal < 1 or numberVal > 150 then
                            return "Number of days lookahead must be between 1 and 150 inclusive."
                        end
                        return true
                    end,
                    get = function() return tostring(CalendarSync.db.profile.lookaheadDays) end,
                    set = function(info, val)
                        CalendarSync.db.profile.lookaheadDays = tonumber(val)
                    end,
                    order = 1.12
                },

                toggleDebugMode =
                {
                    type = "toggle",
                    name = "Debug Mode",
                    desc = "Enable verbose debug logging.",
                    get = function() return CalendarSync.db.profile.debugMode end,
                    set = function(info, val)
                        CalendarSync.db.profile.debugMode = val
                    end,
                    order = 10.1
                },
            }
        },
    },
}

LibStub("AceConfig-3.0"):RegisterOptionsTable("CalendarSync", CALENDARSYNC_UI_CONFIG)

local CalendarSyncUI = {}
CalendarSyncUI.optionsFrameRoot = LibStub("AceConfigDialog-3.0"):AddToBlizOptions("CalendarSync", "Calendar Sync", nil)
CalendarSync.UI = CalendarSyncUI

function CalendarSyncUI:Show()
    InterfaceOptionsFrame_OpenToCategory(self.optionsFrameRoot)
end