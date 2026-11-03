"""Services for the SmartTub integration."""

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import ATTR_MODE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, service
from homeassistant.helpers.typing import VolDictType
import smarttub

from ._compat import vol
from .const import ATTR_DURATION, ATTR_REMINDER_DAYS, ATTR_START_HOUR, DOMAIN

# probatio offers AtLeastOne; older releases (voluptuous) use the cv helper
_at_least_one = getattr(vol, "AtLeastOne", None) or cv.has_at_least_one_key

RESET_REMINDER_SCHEMA: VolDictType = {
    vol.Required(ATTR_REMINDER_DAYS): vol.All(
        vol.Coerce(int), vol.Range(min=30, max=365)
    )
}
SNOOZE_REMINDER_SCHEMA: VolDictType = {
    vol.Required(ATTR_REMINDER_DAYS): vol.All(
        vol.Coerce(int), vol.Range(min=10, max=120)
    )
}
SET_PRIMARY_FILTRATION_SCHEMA = vol.All(
    _at_least_one(ATTR_DURATION, ATTR_START_HOUR),
    cv.make_entity_service_schema(
        {
            vol.Optional(ATTR_DURATION): vol.All(int, vol.Range(min=1, max=24)),
            vol.Optional(ATTR_START_HOUR): vol.All(int, vol.Range(min=0, max=23)),
        },
    ),
)
SET_SECONDARY_FILTRATION_SCHEMA: VolDictType = {
    vol.Required(ATTR_MODE): vol.In(
        {
            mode.name.lower()
            for mode in smarttub.SpaSecondaryFiltrationCycle.SecondaryFiltrationMode
        }
    ),
}


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the services for the SmartTub integration."""

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "snooze_reminder",
        entity_domain=BINARY_SENSOR_DOMAIN,
        schema=SNOOZE_REMINDER_SCHEMA,
        func="async_snooze",
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "reset_reminder",
        entity_domain=BINARY_SENSOR_DOMAIN,
        schema=RESET_REMINDER_SCHEMA,
        func="async_reset",
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "set_primary_filtration",
        entity_domain=SENSOR_DOMAIN,
        schema=SET_PRIMARY_FILTRATION_SCHEMA,
        func="async_set_primary_filtration",
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "set_secondary_filtration",
        entity_domain=SENSOR_DOMAIN,
        schema=SET_SECONDARY_FILTRATION_SCHEMA,
        func="async_set_secondary_filtration",
    )
