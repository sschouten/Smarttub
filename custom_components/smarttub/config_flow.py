"""Config flow to configure the SmartTub integration."""

from collections.abc import Mapping
from typing import Any, override

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from smarttub import LoginFailed

from ._compat import vol
from .const import (
    CONF_AUX_TIMEOUT,
    CONF_COMMAND_TIMEOUT,
    CONF_FAILURE_THRESHOLD,
    CONF_MAX_BACKOFF,
    CONF_POLL_TIMEOUT,
    CONF_SCAN_INTERVAL,
    DEFAULT_OPTIONS,
    DOMAIN,
)
from .controller import SmartTubController

# option -> (min, max, unit)
OPTION_RANGES: dict[str, tuple[int, int, str | None]] = {
    CONF_SCAN_INTERVAL: (15, 900, "s"),
    CONF_POLL_TIMEOUT: (5, 120, "s"),
    CONF_AUX_TIMEOUT: (5, 120, "s"),
    CONF_COMMAND_TIMEOUT: (5, 180, "s"),
    CONF_FAILURE_THRESHOLD: (1, 30, None),
    CONF_MAX_BACKOFF: (60, 3600, "s"),
}

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
)


class SmartTubConfigFlow(ConfigFlow, domain=DOMAIN):
    """SmartTub configuration flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return SmartTubOptionsFlow()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            controller = SmartTubController(self.hass)
            try:
                account = await controller.login(
                    user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )

            except LoginFailed:
                errors["base"] = "invalid_auth"
            else:
                await self.async_set_unique_id(account.id)

                if self.source != SOURCE_REAUTH:
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user_input[CONF_EMAIL], data=user_input
                    )

                # this is a reauth attempt
                self._abort_if_unique_id_mismatch(reason="already_configured")
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Get new credentials if the current ones don't work anymore."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            # same as DATA_SCHEMA but with default email
            data_schema = vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL,
                        default=self._get_reauth_entry().data.get(CONF_EMAIL),
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            )
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=data_schema,
            )
        return await self.async_step_user(user_input)


class SmartTubOptionsFlow(OptionsFlow):
    """Polling and resilience options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            values = {key: int(value) for key, value in user_input.items()}
            if values[CONF_MAX_BACKOFF] < values[CONF_SCAN_INTERVAL]:
                errors[CONF_MAX_BACKOFF] = "max_backoff_too_low"
            else:
                return self.async_create_entry(data=values)

        current = {**DEFAULT_OPTIONS, **self.config_entry.options}
        if user_input is not None:
            current.update(user_input)
        schema = vol.Schema(
            {
                vol.Required(key, default=current[key]): NumberSelector(
                    NumberSelectorConfig(
                        min=low,
                        max=high,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        **({"unit_of_measurement": unit} if unit else {}),
                    )
                )
                for key, (low, high, unit) in OPTION_RANGES.items()
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
