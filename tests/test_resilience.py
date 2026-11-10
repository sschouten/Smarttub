"""Tests for the resilience features of the SmartTub fork."""

import asyncio
from datetime import timedelta
from unittest.mock import patch

import pytest
import smarttub
from smarttub import APIError

from homeassistant.components.smarttub.const import (
    CONF_AUX_TIMEOUT,
    CONF_COMMAND_TIMEOUT,
    CONF_FAILURE_THRESHOLD,
    CONF_MAX_BACKOFF,
    CONF_POLL_TIMEOUT,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    ISSUE_API_UNREACHABLE,
    ISSUE_UPSTREAM_CHANGED,
    UNCONFIRMED_COMMAND_MESSAGE,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from tests.common import MockConfigEntry

PREFIX = "mockbrand1_mockmodel1"
CLIMATE = f"climate.{PREFIX}_thermostat"
API_CONNECTION = f"binary_sensor.{PREFIX}_api_connection"
FAILED_POLLS = f"sensor.{PREFIX}_consecutive_failed_polls"
LAST_SUCCESS = f"sensor.{PREFIX}_last_successful_poll"
POLL_DURATION = f"sensor.{PREFIX}_last_poll_duration"
REFRESH = f"button.{PREFIX}_refresh"
JET_P1 = f"switch.{PREFIX}_jet_p1"

# unique_ids produced by the built-in integration (HA 2026.10.4) for the mock
# spa; they must stay identical so existing entities and automations survive
UPSTREAM_UNIQUE_IDS = {
    ("binary_sensor", "mockspa1-Error"),
    ("binary_sensor", "mockspa1-Online"),
    ("binary_sensor", "mockspa1-externalsensor-address1"),
    ("binary_sensor", "mockspa1-reminder-FILTER01"),
    ("climate", "mockspa1-Thermostat"),
    ("light", "mockspa1-light-1"),
    ("light", "mockspa1-light-2"),
    ("sensor", "mockspa1-Blowout Cycle"),
    ("sensor", "mockspa1-Cleanup Cycle"),
    ("sensor", "mockspa1-Flow Switch"),
    ("sensor", "mockspa1-Ozone"),
    ("sensor", "mockspa1-Primary Filtration Cycle"),
    ("sensor", "mockspa1-Secondary Filtration Cycle"),
    ("sensor", "mockspa1-State"),
    ("sensor", "mockspa1-UV"),
    ("switch", "mockspa1-pump-CP"),
    ("switch", "mockspa1-pump-P1"),
    ("switch", "mockspa1-pump-P2"),
}


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


async def test_unique_ids_unchanged(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, config_entry, setup_entry
) -> None:
    """All upstream unique_ids exist unchanged; only diagnostic ones are added."""
    entries = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    unique_ids = {(entry.domain, entry.unique_id) for entry in entries}
    assert unique_ids >= UPSTREAM_UNIQUE_IDS
    assert unique_ids - UPSTREAM_UNIQUE_IDS == {
        ("binary_sensor", "mockspa1-api_connection"),
        ("button", "mockspa1-refresh"),
        ("button", "mockspa1-sync_clock"),
        ("sensor", "mockspa1-clock_offset"),
        ("sensor", "mockspa1-energy_today"),
        ("sensor", "mockspa1-energy_yesterday"),
        ("sensor", "mockspa1-energy_month"),
        ("sensor", "mockspa1-consecutive_failed_polls"),
        ("sensor", "mockspa1-last_poll_duration"),
        ("sensor", "mockspa1-last_successful_poll"),
    }


async def test_diagnostic_entities(hass: HomeAssistant, setup_entry) -> None:
    """Diagnostic entities are enabled and report a healthy poll."""
    assert hass.states.get(API_CONNECTION).state == STATE_ON
    assert hass.states.get(FAILED_POLLS).state == "0"
    assert hass.states.get(LAST_SUCCESS).state not in (None, "unknown")
    assert float(hass.states.get(POLL_DURATION).state) >= 0
    assert "status_duration" in hass.states.get(POLL_DURATION).attributes


async def test_aux_failure_keeps_last_values(
    hass: HomeAssistant, spa, config_entry, setup_entry
) -> None:
    """A failing reminders/errors call does not fail the update."""
    reminder = f"binary_sensor.{PREFIX}_myfilter_reminder"
    assert hass.states.get(reminder).attributes["days"] == 2

    # error details are only fetched while the spa reports an error code
    (await spa.get_status_full()).error_code = 11
    spa.get_reminders.side_effect = TimeoutError
    spa.get_errors.side_effect = APIError("boom")
    await _refresh(hass, config_entry)

    controller = config_entry.runtime_data
    assert controller.consecutive_failures == 0
    assert controller.aux_failures == {"reminders": 1, "errors": 1}
    assert hass.states.get(reminder).attributes["days"] == 2
    assert hass.states.get(CLIMATE).state != STATE_UNAVAILABLE


async def test_errors_only_fetched_with_error_code(
    hass: HomeAssistant, spa, config_entry, setup_entry
) -> None:
    """Without an error code the (slow) errors endpoint is not called."""
    spa.get_errors.reset_mock()
    await _refresh(hass, config_entry)
    spa.get_errors.assert_not_called()

    (await spa.get_status_full()).error_code = 11
    await _refresh(hass, config_entry)
    spa.get_errors.assert_called_once()


async def test_slow_aux_call_is_cut_off(
    hass: HomeAssistant, spa, config_entry, setup_entry
) -> None:
    """A reminders call slower than aux_timeout is cancelled, status still wins."""
    controller = config_entry.runtime_data

    async def slow_reminders():
        await asyncio.sleep(3600)

    spa.get_reminders.side_effect = slow_reminders
    with patch.object(
        type(controller), "aux_timeout", new_callable=lambda: property(lambda s: 0.01)
    ):
        await _refresh(hass, config_entry)

    assert controller.consecutive_failures == 0
    assert controller.aux_failures["reminders"] == 1


async def test_hold_data_until_threshold(
    hass: HomeAssistant, spa, config_entry, setup_entry
) -> None:
    """Entities stay available until failure_threshold polls failed in a row."""
    controller = config_entry.runtime_data
    issue_registry = ir.async_get(hass)
    spa.get_status_full.side_effect = TimeoutError

    for failures in range(1, controller.failure_threshold):
        await _refresh(hass, config_entry)
        assert controller.consecutive_failures == failures
        assert hass.states.get(CLIMATE).state != STATE_UNAVAILABLE
        assert hass.states.get(API_CONNECTION).state == STATE_OFF
        assert hass.states.get(API_CONNECTION).attributes["holding_last_data"]
        assert hass.states.get(FAILED_POLLS).state == str(failures)
        assert issue_registry.async_get_issue(DOMAIN, ISSUE_API_UNREACHABLE) is None

    await _refresh(hass, config_entry)
    assert hass.states.get(CLIMATE).state == STATE_UNAVAILABLE
    # diagnostic entities stay available while polling fails
    assert hass.states.get(FAILED_POLLS).state == str(controller.failure_threshold)
    assert hass.states.get(API_CONNECTION).state == STATE_OFF
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_API_UNREACHABLE) is not None

    spa.get_status_full.side_effect = None
    await _refresh(hass, config_entry)
    assert hass.states.get(CLIMATE).state != STATE_UNAVAILABLE
    assert hass.states.get(API_CONNECTION).state == STATE_ON
    assert hass.states.get(FAILED_POLLS).state == "0"
    assert issue_registry.async_get_issue(DOMAIN, ISSUE_API_UNREACHABLE) is None


async def test_backoff_and_restore(
    hass: HomeAssistant, spa, config_entry, setup_entry
) -> None:
    """The poll interval backs off after the threshold and is restored after."""
    controller = config_entry.runtime_data
    coordinator = controller.coordinator
    normal = timedelta(seconds=controller.scan_interval)
    assert coordinator.update_interval == normal

    spa.get_status_full.side_effect = TimeoutError
    for _ in range(controller.failure_threshold + 3):
        await _refresh(hass, config_entry)

    interval = coordinator.update_interval.total_seconds()
    assert interval > controller.scan_interval
    assert interval <= controller.max_backoff * 1.1 + 1

    spa.get_status_full.side_effect = None
    await _refresh(hass, config_entry)
    assert coordinator.update_interval == normal


async def test_threshold_one_behaves_like_upstream(
    hass: HomeAssistant, spa, account
) -> None:
    """failure_threshold=1 makes entities unavailable at the first failure."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"email": "test-email", "password": "test-password"},
        options={CONF_FAILURE_THRESHOLD: 1},
        unique_id=account.id,
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    spa.get_status_full.side_effect = TimeoutError
    await _refresh(hass, entry)
    assert hass.states.get(CLIMATE).state == STATE_UNAVAILABLE


async def test_new_reminder_added_later(
    hass: HomeAssistant, spa, config_entry, setup_entry
) -> None:
    """Reminders that appear after setup get an entity."""
    new_reminder = smarttub.SpaReminder(
        spa,
        id="REFRESH",
        name="Water",
        remainingDuration=10,
        snoozed=False,
        state="INACTIVE",
    )
    reminders = await spa.get_reminders()
    spa.get_reminders.return_value = [*reminders, new_reminder]
    await _refresh(hass, config_entry)

    assert hass.states.get(f"binary_sensor.{PREFIX}_water_reminder") is not None


async def test_refresh_button(hass: HomeAssistant, spa, setup_entry) -> None:
    """The refresh button polls the API."""
    calls = spa.get_status_full.call_count
    await hass.services.async_call(
        "button", "press", {"entity_id": REFRESH}, blocking=True
    )
    await hass.async_block_till_done()
    assert spa.get_status_full.call_count > calls


async def test_unconfirmed_command_is_optimistic(
    hass: HomeAssistant, spa, setup_entry
) -> None:
    """A command accepted but not confirmed shows the target state."""
    pump = next(
        pump for pump in spa.get_status_full.return_value.pumps if pump.id == "P1"
    )
    pump.toggle.side_effect = RuntimeError(UNCONFIRMED_COMMAND_MESSAGE)
    assert hass.states.get(JET_P1).state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": JET_P1}, blocking=True
    )
    assert hass.states.get(JET_P1).state == STATE_ON


async def test_command_timeout_raises(hass: HomeAssistant, spa, setup_entry) -> None:
    """A command that times out raises a readable error."""
    pump = next(
        pump for pump in spa.get_status_full.return_value.pumps if pump.id == "P1"
    )
    pump.toggle.side_effect = TimeoutError
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": JET_P1}, blocking=True
        )
    assert hass.states.get(JET_P1).state == STATE_OFF


async def test_climate_optimistic_target(hass: HomeAssistant, spa, setup_entry) -> None:
    """Setting a temperature shows the new target right away."""
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": CLIMATE, "temperature": 36.5},
        blocking=True,
    )
    assert hass.states.get(CLIMATE).attributes["temperature"] == 36.5


async def test_options_flow(hass: HomeAssistant, config_entry, setup_entry) -> None:
    """Options can be changed and are validated."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    values = {
        CONF_SCAN_INTERVAL: 120,
        CONF_POLL_TIMEOUT: 40,
        CONF_AUX_TIMEOUT: 25,
        CONF_COMMAND_TIMEOUT: 60,
        CONF_FAILURE_THRESHOLD: 3,
        CONF_MAX_BACKOFF: 60,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], values
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_MAX_BACKOFF: "max_backoff_too_low"}

    values[CONF_MAX_BACKOFF] = 900
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], values
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    controller = config_entry.runtime_data
    assert controller.failure_threshold == 3
    assert controller.coordinator.update_interval == timedelta(seconds=120)


async def test_old_upstream_issue_is_removed(hass: HomeAssistant, config_entry) -> None:
    """The repair issue of versions before 1.5.1 is cleaned up at setup."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_UPSTREAM_CHANGED,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        # the old translation no longer exists; any existing key will do here
        translation_key=ISSUE_API_UNREACHABLE,
        translation_placeholders={"failures": "0", "error": "-", "last_success": "-"},
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_UPSTREAM_CHANGED) is None
