"""Platform for climate integration."""

from typing import Any, override

from homeassistant.components.climate import (
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from smarttub import Spa

from .const import DEFAULT_MAX_TEMP, DEFAULT_MIN_TEMP
from .controller import SmartTubConfigEntry
from .entity import SmartTubEntity

PRESET_DAY = "day"
PRESET_READY = "ready"
PRESET_REST = "rest"

# Home Assistant 2026.11 introduced the native_* temperature API for climate
# entities; the old names are deprecated there. Use whichever this release has.
NATIVE_TEMPERATURE_API = "native_current_temperature" in dir(ClimateEntity)

PRESET_MODES = {
    Spa.HeatMode.AUTO: PRESET_NONE,
    Spa.HeatMode.ECONOMY: PRESET_ECO,
    Spa.HeatMode.DAY: PRESET_DAY,
    Spa.HeatMode.READY: PRESET_READY,
    # known to the library but not mapped upstream, which made the entity
    # crash while the spa was in this mode
    Spa.HeatMode.REST: PRESET_REST,
}

HEAT_MODES = {v: k for k, v in PRESET_MODES.items()}

HVAC_ACTIONS = {
    "OFF": HVACAction.IDLE,
    "ON": HVACAction.HEATING,
}

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartTubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up climate entity for the thermostat in the tub."""

    controller = entry.runtime_data

    entities = [
        SmartTubThermostat(controller.coordinator, spa) for spa in controller.spas
    ]

    async_add_entities(entities)


class SmartTubThermostat(SmartTubEntity, ClimateEntity):
    """The target water temperature for the spa."""

    # SmartTub devices don't seem to have the option of disabling the heater,
    # so this is always HVACMode.HEAT.
    _attr_hvac_mode = HVACMode.HEAT
    _attr_hvac_modes = [HVACMode.HEAT]
    # Only target temperature is supported.
    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TARGET_TEMPERATURE
    )
    _attr_min_temp = DEFAULT_MIN_TEMP
    _attr_max_temp = DEFAULT_MAX_TEMP
    _attr_preset_modes = [PRESET_NONE, PRESET_ECO, PRESET_DAY, PRESET_READY]
    _attr_translation_key = "thermostat"

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], spa: Spa
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, spa, "Thermostat")

    @property
    @override
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation."""
        return HVAC_ACTIONS.get(self.spa_status.heater)

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode.

        As with hvac_mode, we don't really have an option here.
        """
        if hvac_mode == HVACMode.HEAT:
            return
        raise NotImplementedError(hvac_mode)

    @property
    @override
    def preset_mode(self) -> str:
        """Return the current preset mode."""
        return self._optimistic_or(
            "preset_mode", PRESET_MODES.get(self.spa_status.heat_mode)
        )

    @property
    @override
    def preset_modes(self) -> list[str]:
        """Return the presets; "rest" only while the spa is in that mode."""
        modes = list(self._attr_preset_modes)
        if self.preset_mode == PRESET_REST:
            modes.append(PRESET_REST)
        return modes

    def _water_temperature(self) -> float | None:
        return self.spa_status.water.temperature

    def _set_temperature(self) -> float | None:
        return self._optimistic_or(
            "target_temperature", self.spa_status.set_temperature
        )

    if NATIVE_TEMPERATURE_API:
        _attr_native_temperature_unit = UnitOfTemperature.CELSIUS

        @property
        def native_current_temperature(self) -> float | None:
            """Return the current water temperature."""
            return self._water_temperature()

        @property
        def native_target_temperature(self) -> float | None:
            """Return the target water temperature."""
            return self._set_temperature()

    else:
        _attr_temperature_unit = UnitOfTemperature.CELSIUS

        @property
        def current_temperature(self) -> float | None:
            """Return the current water temperature."""
            return self._water_temperature()

        @property
        def target_temperature(self) -> float | None:
            """Return the target water temperature."""
            return self._set_temperature()

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs[ATTR_TEMPERATURE]
        confirmed = await self.controller.async_command(
            self.spa.set_temperature(temperature),
            f"set temperature to {temperature}",
        )
        self._set_optimistic(confirmed, target_temperature=temperature)

    @override
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Activate the specified preset mode."""
        heat_mode = HEAT_MODES[preset_mode]
        confirmed = await self.controller.async_command(
            self.spa.set_heat_mode(heat_mode), f"set preset {preset_mode}"
        )
        self._set_optimistic(confirmed, preset_mode=preset_mode)
