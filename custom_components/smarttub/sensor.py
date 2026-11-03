"""Platform for sensor integration."""

from datetime import datetime
from enum import Enum
from typing import Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import ATTR_MODE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import smarttub

from .const import ATTR_DURATION, ATTR_START_HOUR
from .controller import SmartTubConfigEntry
from .entity import SmartTubDiagnosticEntity, SmartTubOnboardSensorBase

ATTR_CYCLE_LAST_UPDATED = "cycle_last_updated"

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartTubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensor entities for the sensors in the tub."""

    controller = entry.runtime_data

    entities = []
    for spa in controller.spas:
        entities.extend(
            [
                SmartTubBuiltinSensor(controller.coordinator, spa, "State", "state"),
                SmartTubBuiltinSensor(
                    controller.coordinator, spa, "Flow Switch", "flow_switch"
                ),
                SmartTubBuiltinSensor(controller.coordinator, spa, "Ozone", "ozone"),
                SmartTubBuiltinSensor(controller.coordinator, spa, "UV", "uv"),
                SmartTubBuiltinSensor(
                    controller.coordinator, spa, "Blowout Cycle", "blowout_cycle"
                ),
                SmartTubBuiltinSensor(
                    controller.coordinator, spa, "Cleanup Cycle", "cleanup_cycle"
                ),
                SmartTubPrimaryFiltrationCycle(controller.coordinator, spa),
                SmartTubSecondaryFiltrationCycle(controller.coordinator, spa),
                SmartTubLastSuccessfulPoll(controller.coordinator, spa),
                SmartTubLastPollDuration(controller.coordinator, spa),
                SmartTubConsecutiveFailedPolls(controller.coordinator, spa),
            ]
        )

    async_add_entities(entities)


class SmartTubBuiltinSensor(SmartTubOnboardSensorBase, SensorEntity):
    """Generic class for SmartTub status sensors."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        spa: smarttub.Spa,
        sensor_name: str,
        state_key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, spa, sensor_name, state_key)
        self._attr_translation_key = state_key

    @property
    @override
    def native_value(self) -> str | None:
        """Return the current state of the sensor."""
        if self._state is None:
            return None

        if isinstance(self._state, Enum):
            return self._state.name.lower()

        return self._state.lower()


class SmartTubPrimaryFiltrationCycle(SmartTubBuiltinSensor):
    """The primary filtration cycle."""

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], spa: smarttub.Spa
    ) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, spa, "Primary Filtration Cycle", "primary_filtration"
        )
        self._attr_translation_key = "primary_filtration_cycle"

    @property
    def cycle(self) -> smarttub.SpaPrimaryFiltrationCycle:
        """Return the underlying smarttub.SpaPrimaryFiltrationCycle object."""
        return self._state

    @property
    @override
    def native_value(self) -> str:
        """Return the current state of the sensor."""
        return self.cycle.status.name.lower()

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            ATTR_DURATION: self.cycle.duration,
            ATTR_CYCLE_LAST_UPDATED: self.cycle.last_updated.isoformat(),
            ATTR_MODE: self.cycle.mode.name.lower(),
            ATTR_START_HOUR: self.cycle.start_hour,
        }

    async def async_set_primary_filtration(self, **kwargs):
        """Update primary filtration settings."""
        await self.controller.async_command(
            self.cycle.set(
                duration=kwargs.get(ATTR_DURATION),
                start_hour=kwargs.get(ATTR_START_HOUR),
            ),
            "set primary filtration",
        )


class SmartTubSecondaryFiltrationCycle(SmartTubBuiltinSensor):
    """The secondary filtration cycle."""

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], spa: smarttub.Spa
    ) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, spa, "Secondary Filtration Cycle", "secondary_filtration"
        )
        self._attr_translation_key = "secondary_filtration_cycle"

    @property
    def cycle(self) -> smarttub.SpaSecondaryFiltrationCycle:
        """Return the underlying smarttub.SpaSecondaryFiltrationCycle object."""
        return self._state

    @property
    @override
    def native_value(self) -> str:
        """Return the current state of the sensor."""
        return self.cycle.status.name.lower()

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            ATTR_CYCLE_LAST_UPDATED: self.cycle.last_updated.isoformat(),
            ATTR_MODE: self.cycle.mode.name.lower(),
        }

    async def async_set_secondary_filtration(self, **kwargs):
        """Update primary filtration settings."""
        mode = smarttub.SpaSecondaryFiltrationCycle.SecondaryFiltrationMode[
            kwargs[ATTR_MODE].upper()
        ]
        await self.controller.async_command(
            self.cycle.set_mode(mode), "set secondary filtration"
        )


class SmartTubLastSuccessfulPoll(SmartTubDiagnosticEntity, SensorEntity):
    """Timestamp of the last successful poll of the SmartTub API."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_successful_poll"

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], spa: smarttub.Spa
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, spa, "last_successful_poll")

    @property
    @override
    def native_value(self) -> datetime | None:
        """Return the time of the last successful poll."""
        return self.controller.last_success


class SmartTubLastPollDuration(SmartTubDiagnosticEntity, SensorEntity):
    """Duration of the last poll attempt (successful or not)."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_translation_key = "last_poll_duration"

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], spa: smarttub.Spa
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, spa, "last_poll_duration")

    @property
    @override
    def native_value(self) -> float | None:
        """Return the duration of the last poll in seconds."""
        return self.controller.last_poll_duration

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the duration of each API call."""
        return {
            f"{name}_duration": value
            for name, value in self.controller.last_call_durations.items()
        }


class SmartTubConsecutiveFailedPolls(SmartTubDiagnosticEntity, SensorEntity):
    """Number of consecutive failed polls."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "consecutive_failed_polls"

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], spa: smarttub.Spa
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, spa, "consecutive_failed_polls")

    @property
    @override
    def native_value(self) -> int:
        """Return the number of consecutive failed polls."""
        return self.controller.consecutive_failures

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return failure statistics."""
        controller = self.controller
        return {
            "failure_threshold": controller.failure_threshold,
            "total_polls": controller.total_polls,
            "total_failures": controller.total_failures,
            "reminders_failures": controller.aux_failures["reminders"],
            "errors_failures": controller.aux_failures["errors"],
            "last_error": controller.last_error,
        }
