"""Serve and register the SmartTub Lovelace card."""

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.loader import async_get_integration

from .const import DOMAIN

URL_BASE = "/smarttub_static"
CARD_FILE = "smarttub-card.js"
DATA_REGISTERED = f"{DOMAIN}_card_registered"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and load it in every dashboard (once per run)."""
    if hass.data.get(DATA_REGISTERED):
        return
    hass.data[DATA_REGISTERED] = True

    integration = await async_get_integration(hass, DOMAIN)
    folder = Path(__file__).parent / "frontend"
    url = f"{URL_BASE}/{CARD_FILE}?v={integration.version}"

    async def _register() -> None:
        if hass.http is None:
            return
        await hass.http.async_register_static_paths(
            [StaticPathConfig(URL_BASE, str(folder), cache_headers=False)]
        )
        add_extra_js_url(hass, url)

    if "frontend" in hass.config.components:
        await _register()
        return

    @callback
    def _component_loaded(event: Event) -> None:
        if event.data.get("component") == "frontend":
            remove_listener()
            hass.async_create_task(_register())

    remove_listener = hass.bus.async_listen(EVENT_COMPONENT_LOADED, _component_loaded)
