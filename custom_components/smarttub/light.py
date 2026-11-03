"""Platform for light integration."""

from typing import Any, override

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    EFFECT_COLORLOOP,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from smarttub import SpaLight

from .const import (
    ATTR_LIGHTS,
    DEFAULT_EXTERIOR_LIGHT_EFFECT,
    DEFAULT_LIGHT_BRIGHTNESS,
    DEFAULT_LIGHT_EFFECT,
)

ATTR_ZONE_TYPE = "zone_type"
# exterior zones (corner lights) only support white, as in the SmartTub app
EXTERIOR_LIGHT_EFFECTS = ("white",)
from .controller import SmartTubConfigEntry
from .entity import SmartTubEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartTubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up entities for any lights in the tub."""

    controller = entry.runtime_data

    entities = [
        SmartTubLight(controller.coordinator, light)
        for spa in controller.spas
        for light in controller.coordinator.data[spa.id][ATTR_LIGHTS].values()
    ]

    async_add_entities(entities)


class SmartTubLight(SmartTubEntity, LightEntity):
    """A light on a spa."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], light: SpaLight
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, light.spa, "light")
        self.light_zone = light.zone
        self._attr_unique_id = f"{super().unique_id}-{light.zone}"
        self._attr_translation_key = "light_zone"
        self._attr_translation_placeholders = {"zone": str(light.zone)}

    @property
    def light(self) -> SpaLight:
        """Return the underlying SpaLight object for this entity."""
        return self.coordinator.data[self.spa.id][ATTR_LIGHTS][self.light_zone]

    @property
    def is_exterior(self) -> bool:
        """Return True for an exterior zone (e.g. corner lights).

        Exterior zones only support white; a colour mode such as the default
        purple is accepted by the cloud but ignored by the spa.
        """
        properties = getattr(self.light, "properties", None) or {}
        return (
            properties.get("exterior") is True
            or str(properties.get("zoneType", "")).upper() == "EXTERIOR"
        )

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the zone type."""
        return {ATTR_ZONE_TYPE: "exterior" if self.is_exterior else "interior"}

    @property
    @override
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""

        # SmartTub intensity is 0..100
        return self._optimistic_or(
            "brightness", self._smarttub_to_hass_brightness(self.light.intensity)
        )

    @staticmethod
    def _smarttub_to_hass_brightness(intensity):
        if intensity in (0, 1):
            return 0
        return round(intensity * 255 / 100)

    @staticmethod
    def _hass_to_smarttub_brightness(brightness):
        return round(brightness * 100 / 255)

    @property
    @override
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._optimistic_or("is_on", self.light.mode != SpaLight.LightMode.OFF)

    @property
    @override
    def effect(self) -> str | None:
        """Return the current effect."""
        if "effect" in self._optimistic:
            return self._optimistic["effect"]
        mode = self.light.mode.name.lower()
        if mode in self.effect_list:
            return mode
        return None

    @property
    @override
    def effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        if self.is_exterior:
            return list(EXTERIOR_LIGHT_EFFECTS)
        return [
            effect
            for effect in map(self._light_mode_to_effect, SpaLight.LightMode)
            if effect is not None
        ]

    @staticmethod
    def _light_mode_to_effect(light_mode: SpaLight.LightMode):
        if light_mode == SpaLight.LightMode.OFF:
            return None
        if light_mode == SpaLight.LightMode.HIGH_SPEED_COLOR_WHEEL:
            return EFFECT_COLORLOOP

        return light_mode.name.lower()

    @staticmethod
    def _effect_to_light_mode(effect):
        if effect == EFFECT_COLORLOOP:
            return SpaLight.LightMode.HIGH_SPEED_COLOR_WHEEL

        return SpaLight.LightMode[effect.upper()]

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""

        effect = kwargs.get(ATTR_EFFECT)
        if effect is None and self.is_on and self.effect in self.effect_list:
            # e.g. only the brightness changes: keep the current effect
            effect = self.effect
        if effect is None:
            effect = (
                DEFAULT_EXTERIOR_LIGHT_EFFECT
                if self.is_exterior
                else DEFAULT_LIGHT_EFFECT
            )
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is None:
            brightness = (
                self.brightness
                if self.is_on and self.brightness
                else DEFAULT_LIGHT_BRIGHTNESS
            )
        mode = self._effect_to_light_mode(effect)
        intensity = self._hass_to_smarttub_brightness(brightness)

        confirmed = await self.controller.async_command(
            self.light.set_mode(mode, intensity), f"turn on light {self.light_zone}"
        )
        self._set_optimistic(
            confirmed,
            is_on=True,
            brightness=brightness,
            effect=self._light_mode_to_effect(mode),
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        confirmed = await self.controller.async_command(
            self.light.set_mode(SpaLight.LightMode.OFF, 0),
            f"turn off light {self.light_zone}",
        )
        self._set_optimistic(confirmed, is_on=False, brightness=0, effect=None)
