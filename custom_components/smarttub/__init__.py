"""SmartTub integration (resilient fork of the built-in integration)."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .controller import SmartTubConfigEntry, SmartTubController

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: SmartTubConfigEntry) -> bool:
    """Set up a smarttub config entry."""

    controller = SmartTubController(hass)

    await controller.async_setup_entry(entry)

    entry.runtime_data = controller

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartTubConfigEntry) -> bool:
    """Remove a smarttub config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(
    hass: HomeAssistant, entry: SmartTubConfigEntry
) -> None:
    """Reload the entry when the options change."""
    await hass.config_entries.async_reload(entry.entry_id)
