"""SmartTub integration (resilient fork of the built-in integration)."""

from homeassistant.config_entries import ConfigEntries
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .controller import SmartTubConfigEntry, SmartTubController
from .frontend import async_register_card
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Home Assistant 2026.11 expects None from the config entry methods (and an
# exception on failure); earlier releases require a boolean.
ENTRY_METHODS_RETURN_NONE = hasattr(ConfigEntries, "async_unload_platforms_or_raise")

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.LIGHT,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services and the SmartTub card."""
    async_setup_services(hass)
    await async_register_card(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: SmartTubConfigEntry
) -> bool | None:
    """Set up a smarttub config entry."""

    controller = SmartTubController(hass)

    await controller.async_setup_entry(entry)

    entry.runtime_data = controller

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return None if ENTRY_METHODS_RETURN_NONE else True


async def async_unload_entry(
    hass: HomeAssistant, entry: SmartTubConfigEntry
) -> bool | None:
    """Remove a smarttub config entry."""
    if ENTRY_METHODS_RETURN_NONE:
        await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
        return None
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(
    hass: HomeAssistant, entry: SmartTubConfigEntry
) -> None:
    """Reload the entry when the options change."""
    await hass.config_entries.async_reload(entry.entry_id)
