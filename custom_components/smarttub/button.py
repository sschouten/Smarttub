"""Platform for button integration."""

from typing import Any, override

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from smarttub import Spa

from .controller import SmartTubConfigEntry
from .entity import SmartTubDiagnosticEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartTubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the refresh button."""
    controller = entry.runtime_data
    async_add_entities(
        SmartTubRefreshButton(controller.coordinator, spa) for spa in controller.spas
    )


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
