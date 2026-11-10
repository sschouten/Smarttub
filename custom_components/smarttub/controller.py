"""Interface to the SmartTub API.

Resilient fork of the built-in Home Assistant SmartTub controller:

* fullStatus is leading and gets its own (longer) timeout;
* reminders and errors get their own timeout and fall back to the last known
  values instead of failing the whole update;
* the last good data is kept for a configurable number of consecutive failed
  polls before entities become unavailable;
* the poll interval backs off (with jitter) while the API keeps failing;
* poll statistics are exposed for diagnostic entities and diagnostics.
"""

import asyncio
from collections.abc import Callable, Coroutine
from datetime import date, datetime, time as dt_time, timedelta
import logging
import random
import time
from typing import Any

from aiohttp import ClientError, client_exceptions

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from smarttub import APIError, LoginFailed, SmartTub, Spa
from smarttub.api import Account

from .const import (
    ATTR_ERRORS,
    ATTR_LIGHTS,
    ATTR_PUMPS,
    ATTR_REMINDERS,
    ATTR_SENSORS,
    ATTR_STATUS,
    BACKOFF_JITTER,
    CLOCK_SYNC_COOLDOWN,
    CLOCK_SYNC_THRESHOLD,
    CONF_AUTO_CLOCK_SYNC,
    CONF_AUX_TIMEOUT,
    CONF_COMMAND_TIMEOUT,
    CONF_FAILURE_THRESHOLD,
    CONF_MAX_BACKOFF,
    CONF_POLL_TIMEOUT,
    CONF_SCAN_INTERVAL,
    DEFAULT_OPTIONS,
    DOMAIN,
    ENERGY_KWH_FACTOR,
    ENERGY_UPDATE_INTERVAL,
    ISSUE_API_UNREACHABLE,
    ISSUE_UPSTREAM_CHANGED,
    REPO_URL,
    UNCONFIRMED_COMMAND_MESSAGE,
)
from .helpers import get_spa_name

_LOGGER = logging.getLogger(__name__)

type SmartTubConfigEntry = ConfigEntry[SmartTubController]

# errors that make a poll fail (but are expected with a flaky cloud API)
POLL_ERRORS = (
    APIError,
    TimeoutError,
    ClientError,
    RuntimeError,
    KeyError,
    ValueError,
)


class SmartTubCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that knows its controller (used by entities)."""

    controller: SmartTubController


class SmartTubController:
    """Interface between Home Assistant and the SmartTub API."""

    coordinator: SmartTubCoordinator
    spas: list[Spa]
    _account: Account

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize an interface to SmartTub."""
        self._hass = hass
        self._entry: SmartTubConfigEntry | None = None
        self._listeners: list[CALLBACK_TYPE] = []

        # poll statistics
        self.last_success: datetime | None = None
        self.last_success_started: float = 0.0
        self.last_attempt: datetime | None = None
        self.last_poll_duration: float | None = None
        self.last_call_durations: dict[str, float] = {}
        self.consecutive_failures = 0
        self.total_polls = 0
        self.total_failures = 0
        self.aux_failures: dict[str, int] = {ATTR_REMINDERS: 0, ATTR_ERRORS: 0}
        self.last_error: str | None = None
        self.holding_stale_data = False
        self.last_clock_sync: dict[str, float] = {}
        # energy usage per spa: {"today": kWh, "yesterday": kWh, "month": kWh}
        self.energy: dict[str, dict[str, Any]] = {}
        self._energy_fetched: float | None = None
        self._energy_task: asyncio.Task | None = None
        # index of the date/time payload shape the cloud accepted
        self._date_time_body: int | None = None

    # ------------------------------------------------------------------ options

    @property
    def options(self) -> dict[str, Any]:
        """Return the effective options (defaults merged with entry options)."""
        options = dict(DEFAULT_OPTIONS)
        if self._entry is not None:
            options.update(self._entry.options)
        return options

    @property
    def scan_interval(self) -> int:
        """Return the normal poll interval in seconds."""
        return int(self.options[CONF_SCAN_INTERVAL])

    @property
    def poll_timeout(self) -> float:
        """Return the fullStatus timeout in seconds."""
        return float(self.options[CONF_POLL_TIMEOUT])

    @property
    def aux_timeout(self) -> float:
        """Return the reminders/errors timeout in seconds."""
        return float(self.options[CONF_AUX_TIMEOUT])

    @property
    def command_timeout(self) -> float:
        """Return the command timeout in seconds."""
        return float(self.options[CONF_COMMAND_TIMEOUT])

    @property
    def failure_threshold(self) -> int:
        """Return the number of consecutive failures before going unavailable."""
        return int(self.options[CONF_FAILURE_THRESHOLD])

    @property
    def auto_clock_sync(self) -> bool:
        """Return True if the spa clock is kept in sync automatically."""
        return bool(self.options[CONF_AUTO_CLOCK_SYNC])

    @property
    def max_backoff(self) -> int:
        """Return the maximum poll interval while failing, in seconds."""
        return max(int(self.options[CONF_MAX_BACKOFF]), self.scan_interval)

    # -------------------------------------------------------------------- setup

    async def async_setup_entry(self, entry: SmartTubConfigEntry) -> bool:
        """Perform initial setup.

        Authenticate, query static state, set up polling, and otherwise make
        ready for normal operations .
        """
        self._entry = entry

        try:
            async with asyncio.timeout(self.poll_timeout):
                self._account = await self.login(
                    entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD]
                )
        except LoginFailed as ex:
            # credentials were changed or invalidated, we need new ones
            raise ConfigEntryAuthFailed from ex
        except (
            TimeoutError,
            client_exceptions.ClientOSError,
            client_exceptions.ServerDisconnectedError,
            client_exceptions.ContentTypeError,
            ClientError,
            APIError,
        ) as err:
            raise ConfigEntryNotReady from err

        try:
            async with asyncio.timeout(self.poll_timeout):
                self.spas = await self._account.get_spas()
        except (TimeoutError, ClientError, APIError) as err:
            raise ConfigEntryNotReady from err

        self.coordinator = SmartTubCoordinator(
            self._hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self.scan_interval),
        )
        self.coordinator.controller = self

        # upstream uses async_refresh() here, which leaves coordinator.data
        # empty when the first poll fails and makes platform setup crash;
        # this raises ConfigEntryNotReady instead so HA retries the setup.
        await self.coordinator.async_config_entry_first_refresh()

        self.async_register_devices(entry)

        # the comparison with the built-in integration was removed in 1.5.1;
        # drop the repair issue an earlier version may have left behind
        ir.async_delete_issue(self._hass, DOMAIN, ISSUE_UPSTREAM_CHANGED)

        return True

    # ------------------------------------------------------------------ polling

    async def async_update_data(self) -> dict[str, Any]:
        """Query the API and return the new state."""
        started = time.monotonic()
        self.last_attempt = dt_util.utcnow()
        self.total_polls += 1

        try:
            # poll all spas concurrently (as upstream does since 2026.11)
            results = await asyncio.gather(
                *(self._get_spa_data(spa) for spa in self.spas),
                return_exceptions=True,
            )
            data = {}
            for spa, result in zip(self.spas, results, strict=True):
                if isinstance(result, BaseException):
                    raise result
                data[spa.id] = result
            self._record_success(started)
            self._schedule_energy_update()
            if self.auto_clock_sync:
                self._hass.async_create_task(self._async_auto_clock_sync(data))
        except LoginFailed as err:
            self._record_failure(err)
            raise ConfigEntryAuthFailed from err
        except POLL_ERRORS as err:
            self._record_failure(err)
            previous = getattr(self, "coordinator", None) and self.coordinator.data
            if previous and self.consecutive_failures < self.failure_threshold:
                self.holding_stale_data = True
                _LOGGER.info(
                    "SmartTub poll failed (%s/%s), keeping last known data: %s",
                    self.consecutive_failures,
                    self.failure_threshold,
                    self.last_error,
                )
                return previous

            self.holding_stale_data = False
            self._apply_backoff()
            if previous is not None:
                self._create_unreachable_issue()
            raise UpdateFailed(
                f"{self.consecutive_failures} consecutive failed polls, "
                f"last error: {self.last_error}"
            ) from err
        finally:
            self.last_poll_duration = round(time.monotonic() - started, 2)
            self._notify_listeners()

        return data

    async def _get_spa_data(self, spa: Spa) -> dict[str, Any]:
        """Fetch the data for one spa.

        fullStatus is leading. reminders are fetched concurrently with their
        own timeout; on failure the last known values are kept. The error
        details are only fetched while the spa reports an error code (as
        upstream does since 2026.11): it is often the slowest call.
        """
        previous: dict[str, Any] = {}
        if getattr(self, "coordinator", None) is not None and self.coordinator.data:
            previous = self.coordinator.data.get(spa.id) or {}

        full_status, reminders = await asyncio.gather(
            self._timed(ATTR_STATUS, spa.get_status_full(), self.poll_timeout),
            self._timed(ATTR_REMINDERS, spa.get_reminders(), self.aux_timeout),
            return_exceptions=True,
        )
        if isinstance(full_status, BaseException):
            raise full_status

        if isinstance(reminders, BaseException):
            reminders_map = self._aux_fallback(ATTR_REMINDERS, reminders, previous, {})
        else:
            reminders_map = {reminder.id: reminder for reminder in reminders}

        errors_list: list[Any] = []
        if getattr(full_status, "error_code", None):
            try:
                errors_list = await self._timed(
                    ATTR_ERRORS, spa.get_errors(), self.aux_timeout
                )
            except POLL_ERRORS as err:
                errors_list = self._aux_fallback(ATTR_ERRORS, err, previous, [])
        else:
            self.last_call_durations.pop(ATTR_ERRORS, None)

        return {
            ATTR_STATUS: full_status,
            ATTR_PUMPS: {pump.id: pump for pump in full_status.pumps},
            ATTR_LIGHTS: {light.zone: light for light in full_status.lights},
            ATTR_REMINDERS: reminders_map,
            ATTR_ERRORS: errors_list,
            ATTR_SENSORS: {sensor.address: sensor for sensor in full_status.sensors},
        }

    def _aux_fallback(
        self, key: str, err: BaseException, previous: dict[str, Any], empty: Any
    ) -> Any:
        """Return the last known value for an auxiliary call that failed."""
        if isinstance(err, LoginFailed | asyncio.CancelledError):
            raise err
        if not isinstance(err, POLL_ERRORS):
            raise err
        self.aux_failures[key] += 1
        _LOGGER.debug(
            "SmartTub %s call failed, keeping last known value: %s",
            key,
            _describe(err),
        )
        return previous.get(key, empty)

    async def _timed(
        self, name: str, coro: Coroutine[Any, Any, Any], timeout: float
    ) -> Any:
        """Await a coroutine with a timeout and record its duration."""
        start = time.monotonic()
        try:
            async with asyncio.timeout(timeout):
                return await coro
        finally:
            self.last_call_durations[name] = round(time.monotonic() - start, 2)

    def _record_success(self, started: float) -> None:
        self.consecutive_failures = 0
        self.holding_stale_data = False
        self.last_success = dt_util.utcnow()
        self.last_success_started = started
        if self.coordinator.update_interval != timedelta(seconds=self.scan_interval):
            _LOGGER.info("SmartTub API reachable again, restoring poll interval")
            self.coordinator.update_interval = timedelta(seconds=self.scan_interval)
        ir.async_delete_issue(self._hass, DOMAIN, ISSUE_API_UNREACHABLE)

    def _record_failure(self, err: BaseException) -> None:
        self.consecutive_failures += 1
        self.total_failures += 1
        self.last_error = _describe(err)

    def _apply_backoff(self) -> None:
        """Increase the poll interval exponentially (with jitter) while failing."""
        if getattr(self, "coordinator", None) is None:
            return
        over = max(self.consecutive_failures - self.failure_threshold, 0)
        interval = min(self.scan_interval * (2**over), self.max_backoff)
        interval *= 1 + random.uniform(0, BACKOFF_JITTER)
        self.coordinator.update_interval = timedelta(seconds=round(interval))

    @property
    def poll_interval(self) -> float | None:
        """Return the current poll interval in seconds."""
        if getattr(self, "coordinator", None) is None:
            return None
        if self.coordinator.update_interval is None:
            return None
        return self.coordinator.update_interval.total_seconds()

    @property
    def api_connected(self) -> bool:
        """Return True if the last poll succeeded."""
        return self.last_success is not None and self.consecutive_failures == 0

    # ---------------------------------------------------------------- commands

    async def async_command(
        self, coro: Coroutine[Any, Any, Any], description: str
    ) -> bool:
        """Run a command against the API.

        Returns True when the library confirmed the new state, False when the
        command was accepted but the new state was not (yet) visible.
        Raises HomeAssistantError when the command failed or timed out.
        """
        try:
            async with asyncio.timeout(self.command_timeout):
                await coro
        except RuntimeError as err:
            if str(err) != UNCONFIRMED_COMMAND_MESSAGE:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="command_failed",
                    translation_placeholders={
                        "command": description,
                        "error": _describe(err),
                    },
                ) from err
            _LOGGER.info(
                "SmartTub accepted %s but has not confirmed it yet", description
            )
            return False
        except TimeoutError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_timeout",
                translation_placeholders={
                    "command": description,
                    "timeout": str(int(self.command_timeout)),
                },
            ) from err
        except (APIError, ClientError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={
                    "command": description,
                    "error": _describe(err),
                },
            ) from err
        finally:
            if getattr(self, "coordinator", None) is not None:
                await self.coordinator.async_request_refresh()
        return True

    # ------------------------------------------------------------------ energy

    @callback
    def _schedule_energy_update(self) -> None:
        """Fetch the energy usage in the background, every 30 minutes."""
        if self._energy_task is not None and not self._energy_task.done():
            return
        now = time.monotonic()
        if (
            self._energy_fetched is not None
            and now - self._energy_fetched < ENERGY_UPDATE_INTERVAL
        ):
            return
        self._energy_fetched = now
        self._energy_task = self._hass.async_create_background_task(
            self._async_update_energy(), f"{DOMAIN}_energy_usage"
        )

    async def _async_update_energy(self) -> None:
        """Fetch today's, yesterday's and this month's energy usage."""
        today = dt_util.utcnow().date()  # the cloud uses UTC days
        yesterday = today - timedelta(days=1)
        for spa in self.spas:
            try:
                async with asyncio.timeout(self.aux_timeout):
                    days = await spa.get_energy_usage(
                        Spa.EnergyUsageInterval.DAY, yesterday, today
                    )
                async with asyncio.timeout(self.aux_timeout):
                    months = await spa.get_energy_usage(
                        Spa.EnergyUsageInterval.MONTH, today.replace(day=1), today
                    )
            except POLL_ERRORS as err:
                _LOGGER.debug("SmartTub energy usage not available: %s", _describe(err))
                # retry at the next poll instead of in 30 minutes
                self._energy_fetched = None
                continue
            by_day = {b.get("key"): b.get("value") for b in days or []}
            by_month = {b.get("key"): b.get("value") for b in months or []}
            self.energy[spa.id] = {
                "today": energy_kwh(by_day.get(today.isoformat(), 0)),
                "yesterday": energy_kwh(by_day.get(yesterday.isoformat(), 0)),
                "month": energy_kwh(by_month.get(today.strftime("%Y-%m"), 0)),
                "day": today.isoformat(),
                "updated": dt_util.utcnow().isoformat(),
            }
        self.coordinator.async_update_listeners()

    # ------------------------------------------------------------------- clock

    def spa_clock(
        self, spa_id: str, data: dict[str, Any] | None = None
    ) -> datetime | None:
        """Return the spa's clock (local time) as of the last poll."""
        if data is None:
            data = self.coordinator.data
        data = (data or {}).get(spa_id) or {}
        status = data.get(ATTR_STATUS)
        spa_date = getattr(status, "date", None)
        spa_time = getattr(status, "time", None)
        if spa_date is None or spa_time is None:
            return None
        naive = datetime.combine(
            spa_date.date() if isinstance(spa_date, datetime) else spa_date,
            spa_time.replace(microsecond=0),
        )
        return naive.replace(tzinfo=dt_util.get_default_time_zone())

    def clock_offset(
        self, spa_id: str, data: dict[str, Any] | None = None
    ) -> int | None:
        """Return how many minutes the spa clock is ahead (+) or behind (-).

        Measured against the time of the last successful poll, when the spa
        reported its clock.
        """
        spa_clock = self.spa_clock(spa_id, data)
        if spa_clock is None or self.last_success is None:
            return None
        return round((spa_clock - self.last_success).total_seconds() / 60)

    async def async_set_date_time(
        self,
        spa: Spa,
        date_value: date | None = None,
        time_value: dt_time | None = None,
    ) -> None:
        """Set the spa clock; without arguments sync it with Home Assistant."""
        if date_value is None and time_value is None:
            now = dt_util.now()
            date_value, time_value = now.date(), now.time().replace(microsecond=0)
        await self.async_command(
            self._async_patch_date_time(spa, date_value, time_value),
            "set date and time",
        )
        self.last_clock_sync[spa.id] = time.monotonic()

    async def _async_patch_date_time(
        self, spa: Spa, date_value: date | None, time_value: dt_time | None
    ) -> None:
        """Send the date/time to the spa.

        python-smarttub's set_date_time() uses POST /config, which the cloud
        rejects with 405; other config changes (temperature, heat mode) use
        PATCH /config. The payload shape is undocumented, so the known shapes
        are tried in order and the one that is accepted is remembered.
        """
        config: dict[str, str] = {}
        if date_value is not None:
            config["date"] = date_value.isoformat()
        if time_value is not None:
            config["time"] = time_value.isoformat("minutes")
        bodies = [{"dateTimeConfig": config}, config]
        if self._date_time_body is not None:
            bodies.insert(0, bodies.pop(self._date_time_body))
        last_error: APIError | None = None
        for body in bodies:
            try:
                await spa.request("PATCH", "config", body)
            except APIError as err:
                status = getattr(err.args[0] if err.args else None, "status", None)
                if status not in (400, 405, 422):
                    raise
                _LOGGER.debug("SmartTub rejected date/time body %s: %s", body, err)
                last_error = err
                continue
            self._date_time_body = 0 if "dateTimeConfig" in body else 1
            _LOGGER.debug("SmartTub accepted date/time body %s", body)
            return
        assert last_error is not None
        raise last_error

    async def _async_auto_clock_sync(self, data: dict[str, Any]) -> None:
        """Correct spa clocks that are off (e.g. after a DST change)."""
        for spa in self.spas:
            offset = self.clock_offset(spa.id, data)
            if offset is None or abs(offset) < CLOCK_SYNC_THRESHOLD:
                continue
            last = self.last_clock_sync.get(spa.id)
            if last is not None and time.monotonic() - last < CLOCK_SYNC_COOLDOWN:
                continue
            _LOGGER.info("SmartTub clock of %s is %s min off, syncing", spa.id, offset)
            try:
                await self.async_set_date_time(spa)
            except HomeAssistantError as err:
                _LOGGER.warning("Could not sync the SmartTub clock: %s", err)

    # --------------------------------------------------------------- listeners

    @callback
    def async_add_listener(self, update_callback: CALLBACK_TYPE) -> Callable[[], None]:
        """Listen for poll attempts (successful or not)."""
        self._listeners.append(update_callback)

        @callback
        def remove_listener() -> None:
            self._listeners.remove(update_callback)

        return remove_listener

    @callback
    def _notify_listeners(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()

    # ------------------------------------------------------------------ repairs

    @callback
    def _create_unreachable_issue(self) -> None:
        ir.async_create_issue(
            self._hass,
            DOMAIN,
            ISSUE_API_UNREACHABLE,
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_API_UNREACHABLE,
            translation_placeholders={
                "failures": str(self.consecutive_failures),
                "error": self.last_error or "-",
                "last_success": (
                    dt_util.as_local(self.last_success).isoformat(timespec="seconds")
                    if self.last_success
                    else "-"
                ),
            },
            learn_more_url=REPO_URL,
        )

    # -------------------------------------------------------------------- misc

    @callback
    def async_register_devices(self, entry: SmartTubConfigEntry) -> None:
        """Register devices with the device registry for all spas."""
        device_registry = dr.async_get(self._hass)
        for spa in self.spas:
            status = (self.coordinator.data or {}).get(spa.id, {}).get(ATTR_STATUS)
            versions = getattr(status, "versions", None) or {}
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, spa.id)},
                manufacturer=spa.brand,
                name=get_spa_name(spa),
                model=spa.model,
                sw_version=versions.get("controller"),
                hw_version=versions.get("jacuzziLink"),
            )

    async def login(self, email: str, password: str) -> Account:
        """Retrieve the account corresponding to the specified email and password."""

        api = SmartTub(async_get_clientsession(self._hass))

        await api.login(email, password)
        return await api.get_account()

    def as_diagnostics(self) -> dict[str, Any]:
        """Return poll statistics for diagnostics."""
        return {
            "options": self.options,
            "poll_interval": self.poll_interval,
            "last_success": self.last_success.isoformat()
            if self.last_success
            else None,
            "last_attempt": self.last_attempt.isoformat()
            if self.last_attempt
            else None,
            "last_poll_duration": self.last_poll_duration,
            "last_call_durations": self.last_call_durations,
            "consecutive_failures": self.consecutive_failures,
            "total_polls": self.total_polls,
            "total_failures": self.total_failures,
            "aux_failures": self.aux_failures,
            "last_error": self.last_error,
            "holding_stale_data": self.holding_stale_data,
            "energy": self.energy,
        }


def energy_kwh(value: Any) -> float | None:
    """Convert a SmartTub energy bucket value to kWh."""
    if not isinstance(value, int | float):
        return None
    return round(value * ENERGY_KWH_FACTOR, 3)


def _describe(err: BaseException) -> str:
    """Return a short, log-friendly description of an exception."""
    text = str(err)
    return f"{type(err).__name__}: {text}" if text else type(err).__name__
