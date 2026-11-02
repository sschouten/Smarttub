"""Tests for registering the SmartTub card."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.smarttub.frontend import (
    URL_BASE,
    async_register_card,
)
from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.core import HomeAssistant


async def test_card_registered_when_frontend_loads(hass: HomeAssistant) -> None:
    """The card is served and added to the frontend once it is loaded."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    with patch(
        "homeassistant.components.smarttub.frontend.add_extra_js_url"
    ) as add_url:
        await async_register_card(hass)
        add_url.assert_not_called()

        hass.bus.async_fire(EVENT_COMPONENT_LOADED, {"component": "frontend"})
        await hass.async_block_till_done()

        add_url.assert_called_once()
        assert add_url.call_args[0][1].startswith(f"{URL_BASE}/smarttub-card.js?v=")
        hass.http.async_register_static_paths.assert_awaited_once()

        # registering again (e.g. a second config entry) is a no-op
        await async_register_card(hass)
        hass.bus.async_fire(EVENT_COMPONENT_LOADED, {"component": "frontend"})
        await hass.async_block_till_done()
        add_url.assert_called_once()


async def test_card_registered_immediately_when_frontend_loaded(
    hass: HomeAssistant,
) -> None:
    """With the frontend already loaded the card is registered right away."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()
    hass.config.components.add("frontend")

    with patch(
        "homeassistant.components.smarttub.frontend.add_extra_js_url"
    ) as add_url:
        await async_register_card(hass)

    add_url.assert_called_once()
