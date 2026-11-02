"""Base classes for SmartTub entities."""

import time
from typing import TYPE_CHECKING, Any, override

from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from smarttub import Spa, SpaSensor, SpaState

from .const import ATTR_SENSORS, DOMAIN
from .helpers import get_spa_name

if TYPE_CHECKING:
    from .controller import SmartTubController

# how long (s) an unconfirmed command keeps its optimistic state when the
# polled state still disagrees
OPTIMISTIC_HOLD = 180


class SmartTubEntity(CoordinatorEntity):
    """Base class for SmartTub entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        spa: Spa,
        entity_name: str,
    ) -> None:
        """Initialize the entity.

        Given a spa id and a short name for the entity, we provide basic device
        info, name, unique id, etc. for all derived entities.
        """

        super().__init__(coordinator)
        self.spa = spa
        self._attr_unique_id = f"{spa.id}-{entity_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, spa.id)},
            manufacturer=spa.brand,
            model=spa.model,
            name=get_spa_name(spa),
        )
        self._optimistic: dict[str, Any] = {}
        self._optimistic_since = 0.0
        self._optimistic_confirmed = False

    @property
    def controller(self) -> SmartTubController:
        """Return the controller this entity belongs to."""
        return self.coordinator.controller

    @property
    def spa_status(self) -> SpaState:
        """Retrieve the result of Spa.get_status()."""

        return self.coordinator.data[self.spa.id].get("status")

    # ------------------------------------------------------- optimistic state

    @callback
    def _set_optimistic(self, confirmed: bool, **values: Any) -> None:
        """Show the commanded state until a later poll reflects it."""
        self._optimistic.update(values)
        self._optimistic_since = time.monotonic()
        self._optimistic_confirmed = confirmed
        self.async_write_ha_state()

    def _optimistic_or(self, key: str, actual: Any) -> Any:
        """Return the optimistic value for key, or the actual value."""
        return self._optimistic.get(key, actual)

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Drop optimistic state once a poll started after the command."""
        if self._optimistic:
            fresh = self.controller.last_success_started > self._optimistic_since
            expired = time.monotonic() - self._optimistic_since > OPTIMISTIC_HOLD
            if fresh and (self._optimistic_confirmed or expired):
                self._optimistic.clear()
        super()._handle_coordinator_update()


class SmartTubOnboardSensorBase(SmartTubEntity):
    """Base class for SmartTub onboard sensors."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        spa: Spa,
        sensor_name: str,
        state_key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, spa, sensor_name)
        self._state_key = state_key

    @property
    def _state(self):
        """Retrieve the underlying state from the spa."""
        return getattr(self.spa_status, self._state_key)


class SmartTubExternalSensorBase(SmartTubEntity):
    """Class for additional BLE wireless sensors sold separately."""

    _attr_translation_key = "external_sensor"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        spa: Spa,
        sensor: SpaSensor,
    ) -> None:
        """Initialize the external sensor entity."""
        super().__init__(coordinator, spa, self._sensor_key(sensor))
        self.sensor_address = sensor.address
        self._attr_unique_id = f"{spa.id}-externalsensor-{sensor.address}"
        self._attr_translation_placeholders = {
            "sensor_name": self._human_readable_name(sensor),
        }

    @staticmethod
    def _sensor_key(sensor: SpaSensor) -> str:
        """Return a key for the sensor suitable for unique_id generation."""
        return sensor.name.strip("{}").replace("-", "_")

    @staticmethod
    def _human_readable_name(sensor: SpaSensor) -> str:
        """Return a human-readable name for the sensor."""
        return " ".join(
            word.capitalize() for word in sensor.name.strip("{}").split("-")
        )

    @property
    def sensor(self) -> SpaSensor:
        """Access the smarttub.SpaSensor instance for this sensor."""
        return self.coordinator.data[self.spa.id][ATTR_SENSORS][self.sensor_address]

    @property
    @override
    def available(self) -> bool:
        """Return False when the sensor disappeared from the status."""
        return (
            super().available
            and self.sensor_address in self.coordinator.data[self.spa.id][ATTR_SENSORS]
        )


class SmartTubDiagnosticEntity(SmartTubEntity):
    """Diagnostic entity that stays available when polling fails."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    @override
    def available(self) -> bool:
        """Diagnostic entities report on failures, so stay available."""
        return True

    @override
    async def async_added_to_hass(self) -> None:
        """Also update on failed polls."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.controller.async_add_listener(self.async_write_ha_state)
        )
