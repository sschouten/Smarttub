"""smarttub constants."""

DOMAIN = "smarttub"

EVENT_SMARTTUB = "smarttub"

# --- Polling / resilience options (configurable via the options flow) -------

CONF_SCAN_INTERVAL = "scan_interval"
CONF_POLL_TIMEOUT = "poll_timeout"
CONF_AUX_TIMEOUT = "aux_timeout"
CONF_COMMAND_TIMEOUT = "command_timeout"
CONF_FAILURE_THRESHOLD = "failure_threshold"
CONF_MAX_BACKOFF = "max_backoff"
CONF_AUTO_CLOCK_SYNC = "auto_clock_sync"

# seconds between polls
SCAN_INTERVAL = 60
# seconds allowed for fullStatus (the call that drives almost all entities)
POLLING_TIMEOUT = 30
# seconds allowed for reminders / errors; on failure the last known values are kept
AUX_TIMEOUT = 20
# seconds allowed for a command (pump/light/heater) including the library's
# own wait-for-confirmation loop
COMMAND_TIMEOUT = 45
# consecutive failed polls before entities become unavailable
FAILURE_THRESHOLD = 5
# upper bound (seconds) for the poll interval while the API keeps failing
MAX_BACKOFF = 600
# keep the spa clock in sync with Home Assistant (e.g. after a DST change)
AUTO_CLOCK_SYNC = False
# clock offset (minutes) from which the automatic sync corrects the spa clock
CLOCK_SYNC_THRESHOLD = 3
# minimum time between two automatic clock syncs
CLOCK_SYNC_COOLDOWN = 3600
# random extra delay (fraction of the interval) to spread load on the cloud API
BACKOFF_JITTER = 0.1

DEFAULT_OPTIONS = {
    CONF_SCAN_INTERVAL: SCAN_INTERVAL,
    CONF_POLL_TIMEOUT: POLLING_TIMEOUT,
    CONF_AUX_TIMEOUT: AUX_TIMEOUT,
    CONF_COMMAND_TIMEOUT: COMMAND_TIMEOUT,
    CONF_FAILURE_THRESHOLD: FAILURE_THRESHOLD,
    CONF_MAX_BACKOFF: MAX_BACKOFF,
    CONF_AUTO_CLOCK_SYNC: AUTO_CLOCK_SYNC,
}

# kept for backwards compatibility with code that imports it
API_TIMEOUT = COMMAND_TIMEOUT

DEFAULT_MIN_TEMP = 18.5
DEFAULT_MAX_TEMP = 40

# the device doesn't remember any state for the light, so we have to choose a
# mode (smarttub.SpaLight.LightMode) when turning it on.
DEFAULT_LIGHT_EFFECT = "purple"
# exterior zones (e.g. corner lights) only support white
DEFAULT_EXTERIOR_LIGHT_EFFECT = "white"
# default to 50% brightness
DEFAULT_LIGHT_BRIGHTNESS = 128

ATTR_ERRORS = "errors"
ATTR_LIGHTS = "lights"
ATTR_PUMPS = "pumps"
ATTR_REMINDERS = "reminders"
ATTR_STATUS = "status"
ATTR_SENSORS = "sensors"

# the desired duration, in hours, of the cycle
ATTR_DURATION = "duration"
# the hour of the day at which to start the cycle (0-23)
ATTR_START_HOUR = "start_hour"
# how many days to snooze the reminder for
ATTR_REMINDER_DAYS = "days"
# energy usage service
ATTR_INTERVAL = "interval"
ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"
# date/time service
ATTR_DATE = "date"
ATTR_TIME = "time"

# --- Repairs ----------------------------------------------------------------

ISSUE_API_UNREACHABLE = "api_unreachable"
ISSUE_UPSTREAM_CHANGED = "upstream_changed"

# The built-in integration in Home Assistant 2026.10.x uses a 10 s polling
# timeout for all three calls together. When the built-in constant changes, or
# when HA reaches UPSTREAM_FIXED_IN_HA (set in a later release of this fork
# once the upstream fix has shipped), a repair issue suggests removing the fork.
UPSTREAM_BROKEN_POLLING_TIMEOUT = 10
UPSTREAM_FIXED_IN_HA: str | None = None
# Newest HA release this fork was built against. On newer releases a changed
# built-in controller.py (hash not listed below) is reported as a repair issue.
BUILT_AGAINST_HA = "2026.10.4"
UPSTREAM_KNOWN_CONTROLLER_SHA256 = frozenset(
    {
        # homeassistant/components/smarttub/controller.py @ 2026.10.4
        "0e3ff385c040fb4aa1e861e55ec3f1fd5254e6b394aaf906405f4768b82e9594",
    }
)
REPO_URL = "https://github.com/sschouten/Smarttub"

# library error raised when a command was accepted but the new state was not
# visible within the library's own confirmation window
UNCONFIRMED_COMMAND_MESSAGE = "State change not reflected within timeout period"
