"""Test the SmartTub light platform."""

import pytest
from smarttub import SpaLight

from homeassistant.core import HomeAssistant


# the light in light_zone should have initial state light_state. we will call
# service_name with service_params, and expect the resultant call to
# SpaLight.set_mode to have set_mode_args parameters
@pytest.mark.parametrize(
    ("light_zone", "light_state", "service_name", "service_params", "set_mode_args"),
    [
        (1, "off", "turn_on", {}, (SpaLight.LightMode.PURPLE, 50)),
        (1, "off", "turn_on", {"brightness": 255}, (SpaLight.LightMode.PURPLE, 100)),
        (2, "on", "turn_off", {}, (SpaLight.LightMode.OFF, 0)),
    ],
)
async def test_light(
    spa,
    setup_entry,
    hass: HomeAssistant,
    light_zone,
    light_state,
    service_name,
    service_params,
    set_mode_args,
) -> None:
    """Test light entity."""

    entity_id = f"light.{spa.brand}_{spa.model}_light_{light_zone}"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == light_state

    status = await spa.get_status_full()
    light: SpaLight = next(light for light in status.lights if light.zone == light_zone)

    await hass.services.async_call(
        "light",
        service_name,
        {"entity_id": entity_id, **service_params},
        blocking=True,
    )
    light.set_mode.assert_called_with(*set_mode_args)


async def test_exterior_light_turns_on_white(
    spa, spa_state, config_entry, hass: HomeAssistant
) -> None:
    """Exterior zones default to white; colour modes are ignored by the spa."""
    exterior = next(light for light in spa_state.lights if light.zone == 1)
    exterior.properties = {"zone": 1, "zoneType": "EXTERIOR", "exterior": True}

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = f"light.{spa.brand}_{spa.model}_light_1"
    state = hass.states.get(entity_id)
    assert state.attributes["zone_type"] == "exterior"
    assert state.attributes["effect_list"] == ["white"]

    await hass.services.async_call(
        "light", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    exterior.set_mode.assert_called_with(SpaLight.LightMode.WHITE, 50)


async def test_interior_light_zone_type(spa, setup_entry, hass: HomeAssistant) -> None:
    """Interior zones keep all effects."""
    state = hass.states.get(f"light.{spa.brand}_{spa.model}_light_2")
    assert state.attributes["zone_type"] == "interior"
    assert "purple" in state.attributes["effect_list"]


async def test_brightness_change_keeps_effect(
    spa, setup_entry, hass: HomeAssistant
) -> None:
    """Changing only the brightness of a lit zone keeps its current effect."""
    status = await spa.get_status_full()
    light = next(light for light in status.lights if light.zone == 2)
    light.mode = SpaLight.LightMode.AQUA

    await hass.config_entries.async_reload(
        hass.config_entries.async_entries("smarttub")[0].entry_id
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": f"light.{spa.brand}_{spa.model}_light_2", "brightness": 255},
        blocking=True,
    )
    light.set_mode.assert_called_with(SpaLight.LightMode.AQUA, 100)
