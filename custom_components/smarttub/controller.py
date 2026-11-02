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
from datetime import datetime, timedelta
import hashlib
import logging
from pathlib import Path
import random
import time
from typing import Any

from aiohttp import ClientError, client_exceptions
from awesomeversion import AwesomeVersion

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, __version__ as HA_VERSION
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
    BUILT_AGAINST_HA,
    CONF_AUX_TIMEOUT,
    CONF_COMMAND_TIMEOUT,
    CONF_FAILURE_THRESHOLD,
    CONF_MAX_BACKOFF,
    CONF_POLL_TIMEOUT,
    CONF_SCAN_INTERVAL,
    DEFAULT_OPTIONS,
    DOMAIN,
    ISSUE_API_UNREACHABLE,
    ISSUE_UPSTREAM_CHANGED,
    REPO_URL,
    UNCONFIRMED_COMMAND_MESSAGE,
    UPSTREAM_BROKEN_POLLING_TIMEOUT,
    UPSTREAM_FIXED_IN_HA,
    UPSTREAM_KNOWN_CONTROLLER_SHA256,
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

        await self._async_check_upstream()

        return True

    # ------------------------------------------------------------------ polling

    async def async_update_data(self) -> dict[str, Any]:
        """Query the API and return the new state."""
        started = time.monotonic()
        self.last_attempt = dt_util.utcnow()
        self.total_polls += 1

        try:
            data = {}
            for spa in self.spas:
                data[spa.id] = await self._get_spa_data(spa)
            self._record_success(started)
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

        fullStatus is leading. reminders/errors are fetched concurrently with
        their own timeout; on failure the last known values are kept.
        """
        previous: dict[str, Any] = {}
        if getattr(self, "coordinator", None) is not None and self.coordinator.data:
            previous = self.coordinator.data.get(spa.id) or {}

        full_status, reminders, errors = await asyncio.gather(
            self._timed(ATTR_STATUS, spa.get_status_full(), self.poll_timeout),
            self._timed(ATTR_REMINDERS, spa.get_reminders(), self.aux_timeout),
            self._timed(ATTR_ERRORS, spa.get_errors(), self.aux_timeout),
            return_exceptions=True,
        )
        if isinstance(full_status, BaseException):
            raise full_status

        if isinstance(reminders, BaseException):
            reminders_map = self._aux_fallback(ATTR_REMINDERS, reminders, previous, {})
        else:
            reminders_map = {reminder.id: reminder for reminder in reminders}

        if isinstance(errors, BaseException):
            errors_list = self._aux_fallback(ATTR_ERRORS, errors, previous, [])
        else:
            errors_list = errors

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

    async def _async_check_upstream(self) -> None:
        """Raise a repair issue when the built-in integration may be fixed."""
        reason = await self._hass.async_add_executor_job(_upstream_change_reason)
        if reason is None:
            ir.async_delete_issue(self._hass, DOMAIN, ISSUE_UPSTREAM_CHANGED)
            return
        ir.async_create_issue(
            self._hass,
            DOMAIN,
            ISSUE_UPSTREAM_CHANGED,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_UPSTREAM_CHANGED,
            translation_placeholders={"reason": reason, "version": HA_VERSION},
            learn_more_url=REPO_URL,
        )

    # -------------------------------------------------------------------- misc

    @callback
    def async_register_devices(self, entry: SmartTubConfigEntry) -> None:
        """Register devices with the device registry for all spas."""
        device_registry = dr.async_get(self._hass)
        for spa in self.spas:
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, spa.id)},
                manufacturer=spa.brand,
                name=get_spa_name(spa),
                model=spa.model,
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
        }


def _describe(err: BaseException) -> str:
    """Return a short, log-friendly description of an exception."""
    text = str(err)
    return f"{type(err).__name__}: {text}" if text else type(err).__name__


def _upstream_change_reason() -> str | None:
    """Check whether the built-in smarttub integration looks fixed.

    Runs in the executor (reads files). Returns a reason or None.
    """
    current = AwesomeVersion(HA_VERSION)
    if UPSTREAM_FIXED_IN_HA and current >= AwesomeVersion(UPSTREAM_FIXED_IN_HA):
        return f"the fix is included since Home Assistant {UPSTREAM_FIXED_IN_HA}"

    try:
        import homeassistant.components as ha_components  # noqa: PLC0415

        builtin = Path(ha_components.__file__).parent / "smarttub"
        const_text = (builtin / "const.py").read_text(encoding="utf-8")
        controller_bytes = (builtin / "controller.py").read_bytes()
    except OSError:
        return None

    for line in const_text.splitlines():
        if line.startswith("POLLING_TIMEOUT"):
            try:
                value = float(line.split("=", 1)[1].strip())
            except ValueError:
                break
            if value > UPSTREAM_BROKEN_POLLING_TIMEOUT:
                return f"the built-in POLLING_TIMEOUT is now {value:g} s"
            break

    if current > AwesomeVersion(BUILT_AGAINST_HA):
        digest = hashlib.sha256(controller_bytes).hexdigest()
        if digest not in UPSTREAM_KNOWN_CONTROLLER_SHA256:
            return "the built-in SmartTub controller has changed"
    return None
