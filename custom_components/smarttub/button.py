"""Platform for button integration."""

from typing import Any, override

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from smarttub import Spa

from .controller import SmartTubConfigEntry
from .entity import SmartTubDiagnosticEntity, SmartTubEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartTubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the refresh button."""
    controller = entry.runtime_data
    entities: list[ButtonEntity] = []
    for spa in controller.spas:
        entities.append(SmartTubRefreshButton(controller.coordinator, spa))
        entities.append(SmartTubSyncClockButton(controller.coordinator, spa))
    async_add_entities(entities)


class SmartTubRefreshButton(SmartTubDiagnosticEntity, ButtonEntity):
    """Poll the SmartTub API now."""

    _attr_translation_key = "refresh"

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], spa: Spa
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, spa, "refresh")

    @override
    async def async_press(self) -> None:
        """Request an immediate poll."""
        await self.coordinator.async_request_refresh()


class SmartTubSyncClockButton(SmartTubEntity, ButtonEntity):
    """Set the spa clock to Home Assistant's local date and time."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "sync_clock"

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], spa: Spa
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, spa, "sync_clock")

    @override
    async def async_press(self) -> None:
        """Sync the spa clock."""
        await self.controller.async_set_date_time(self.spa)
