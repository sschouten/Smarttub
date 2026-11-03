"""Tests for the extra entities and services of the SmartTub fork."""

import datetime as dt
from unittest.mock import AsyncMock

import pytest
import smarttub

from homeassistant.components.lock import LockState
from homeassistant.components.smarttub.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from tests.common import MockConfigEntry

PREFIX = "mockbrand1_mockmodel1"
STATE_LOCKED = LockState.LOCKED
STATE_UNLOCKED = LockState.UNLOCKED


@pytest.fixture
def extra_status(spa, spa_state):
    """Add cellular, Wi-Fi and lock data to the spa status."""
    spa_state.properties["signal"] = {
        "strength": 82,
        "quality": 70,
        "networkName": "KPN Telecom B.V.",
        "country": "NL",
        "updateAt": "2026-11-02T21:10:44.402Z",
    }
    spa_state.properties["lastWifi"] = {
        "ssid": "secret-ssid",
        "lastConnectionTimestamp": "2025-12-13T10:21:13.541001Z",
    }
    locks = {}
    for kind, state in (
        ("temperature", "UNLOCKED"),
        ("spa", "LOCKED"),
        ("access", "UNLOCKED"),
        ("tuning", None),
    ):
        lock = smarttub.SpaLock(spa, kind=kind, state=state)
        lock.lock = AsyncMock()
        lock.unlock = AsyncMock()
        locks[kind] = lock
    spa_state.locks = locks
    return spa_state


async def _setup(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_signal_and_wifi_sensors(
    hass: HomeAssistant, extra_status, config_entry
) -> None:
    """Cellular signal and last Wi-Fi connection are exposed."""
    await _setup(hass, config_entry)

    strength = hass.states.get(f"sensor.{PREFIX}_cellular_signal_strength")
    assert strength.state == "82"
    assert strength.attributes["network"] == "KPN Telecom B.V."
    assert hass.states.get(f"sensor.{PREFIX}_cellular_signal_quality").state == "70"

    wifi = hass.states.get(f"sensor.{PREFIX}_last_wi_fi_connection")
    assert wifi.state.startswith("2025-12-13T10:21:13")
    assert "secret-ssid" not in str(wifi.attributes)


async def test_no_signal_entities_without_data(
    hass: HomeAssistant, config_entry
) -> None:
    """Spas that do not report cellular data get no signal entities."""
    await _setup(hass, config_entry)
    assert hass.states.get(f"sensor.{PREFIX}_cellular_signal_strength") is None


async def test_locks(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    extra_status,
    config_entry,
) -> None:
    """Locks are created per reported kind; extra kinds disabled by default."""
    await _setup(hass, config_entry)

    temperature = f"lock.{PREFIX}_temperature_lock"
    spa_lock = f"lock.{PREFIX}_spa_lock"
    assert hass.states.get(temperature).state == STATE_UNLOCKED
    assert hass.states.get(spa_lock).state == STATE_LOCKED

    access = entity_registry.async_get(f"lock.{PREFIX}_access_lock")
    assert access.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    # a lock without a state (tuning) is not created
    assert entity_registry.async_get(f"lock.{PREFIX}_tuning_lock") is None

    await hass.services.async_call(
        "lock", "lock", {"entity_id": temperature}, blocking=True
    )
    extra_status.locks["temperature"].lock.assert_awaited_once()
    assert hass.states.get(temperature).state == STATE_LOCKED

    await hass.services.async_call(
        "lock", "unlock", {"entity_id": spa_lock}, blocking=True
    )
    extra_status.locks["spa"].unlock.assert_awaited_once()
    assert hass.states.get(spa_lock).state == STATE_UNLOCKED


async def test_get_energy_usage(hass: HomeAssistant, spa, config_entry) -> None:
    """The energy usage service returns the cloud's buckets."""
    spa.get_energy_usage.return_value = [{"date": "2026-11-02", "kwh": 3.2}]
    await _setup(hass, config_entry)

    response = await hass.services.async_call(
        DOMAIN,
        "get_energy_usage",
        {
            "entity_id": f"climate.{PREFIX}_thermostat",
            "interval": "day",
            "start_date": "2026-11-01",
            "end_date": "2026-11-02",
        },
        blocking=True,
        return_response=True,
    )
    result = response[f"climate.{PREFIX}_thermostat"]
    assert result["buckets"] == [{"date": "2026-11-02", "kwh": 3.2}]
    assert result["start_date"] == "2026-11-01"
    spa.get_energy_usage.assert_awaited_with(
        smarttub.Spa.EnergyUsageInterval.DAY,
        dt.date(2026, 11, 1),
        dt.date(2026, 11, 2),
    )
