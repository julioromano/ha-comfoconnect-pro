"""UI setup and reconfiguration; probing never changes device settings."""

import ipaddress
import logging
import math
import re
from datetime import timedelta
from typing import Any, final, override

import probatio
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,  # pyright: ignore[reportUnknownVariableType]
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,  # pyright: ignore[reportUnknownVariableType]
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,  # pyright: ignore[reportUnknownVariableType]
)
from modbus_connection import ModbusError, ModbusTcpParams

from .const import (
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DEFAULT_UNIT_ID,
    DOMAIN,
    MIN_SCAN_INTERVAL_SECONDS,
)
from .models import MODEL_Q600, MODELS
from .protocol import CONNECTION_STATES, ComfoAir

_LOGGER = logging.getLogger(__name__)


def normalize_host(value: str) -> str:
    """Normalize DNS names and IPv4/IPv6 literals, without resolving aliases."""
    host = value.strip().lower().removesuffix(".")
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        if len(host) > 253 or not all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in host.split(".")
        ):
            raise probatio.Invalid("Enter a hostname or IP address") from None
        return host


def _integer(value: float) -> int:
    if isinstance(value, bool) or not math.isfinite(value) or int(value) != value:
        raise probatio.Invalid("Expected an integer")
    return int(value)


DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): TextSelector(),
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): NumberSelector(
            NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
        ),
        probatio.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): NumberSelector(
            NumberSelectorConfig(min=1, max=247, mode=NumberSelectorMode.BOX)
        ),
        probatio.Required(CONF_MODEL, default=MODEL_Q600): SelectSelector(
            SelectSelectorConfig(
                options=list(MODELS),
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="model",
            )
        ),
    }
)

OPTIONS_SCHEMA = probatio.Schema(
    {
        probatio.Required(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_SECONDS
        ): NumberSelector(
            NumberSelectorConfig(
                min=MIN_SCAN_INTERVAL_SECONDS,
                step=1,
                unit_of_measurement="s",
                mode=NumberSelectorMode.BOX,
            )
        ),
    }
)


@final
class ComfoConnectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure the device rather than a separate YAML Modbus hub."""

    VERSION = 1

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> ComfoConnectOptionsFlow:
        """Expose polling preferences separately from the device connection."""
        return ComfoConnectOptionsFlow()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_step_connection("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_step_connection("reconfigure", user_input)

    async def _async_step_connection(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry() if step_id == "reconfigure" else None
        if user_input is not None:
            try:
                data: dict[str, Any] = DATA_SCHEMA(user_input)
                # The form schema is serialized for the frontend. Keep custom
                # validation here because Python callables cannot be rendered.
                data[CONF_HOST] = normalize_host(data[CONF_HOST])
                data[CONF_PORT] = _integer(data[CONF_PORT])
                data[CONF_UNIT_ID] = _integer(data[CONF_UNIT_ID])
            except probatio.Invalid:
                errors["base"] = "invalid_input"
            else:
                self._async_abort_entries_match(
                    {
                        CONF_HOST: data[CONF_HOST],
                        CONF_PORT: data[CONF_PORT],
                        CONF_UNIT_ID: data[CONF_UNIT_ID],
                    }
                )
                error = await self._async_validate(data)
                if error:
                    errors["base"] = error
                elif entry is not None:
                    # Preserve custom entry titles when correcting the model.
                    title = (
                        MODELS[data[CONF_MODEL]].name
                        if entry.title == MODELS[entry.data[CONF_MODEL]].name
                        else entry.title
                    )
                    return self.async_update_reload_and_abort(
                        entry, title=title, data_updates=data
                    )
                else:
                    return self.async_create_entry(
                        title=MODELS[data[CONF_MODEL]].name, data=data
                    )
        schema = (
            self.add_suggested_values_to_schema(DATA_SCHEMA, entry.data)
            if entry
            else DATA_SCHEMA
        )
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)

    async def _async_validate(self, data: dict[str, Any]) -> str | None:
        try:
            async with async_get_temporary_unit(
                self.hass,
                ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT]),
                data[CONF_UNIT_ID],
            ) as unit:
                state = await ComfoAir(unit, data[CONF_MODEL]).async_validate()
        except ModbusError, HomeAssistantError:
            return "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected error validating ComfoConnect PRO")
            return "unknown"
        if state == 0:
            return None
        return CONNECTION_STATES.get(state, "unknown_connection_state")


@final
class ComfoConnectOptionsFlow(OptionsFlowWithReload):
    """Save polling preferences and reload the entry when they change."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                options: dict[str, Any] = OPTIONS_SCHEMA(user_input)
                options[CONF_SCAN_INTERVAL] = _integer(options[CONF_SCAN_INTERVAL])
                # Reject intervals the coordinator cannot represent before saving.
                _ = timedelta(seconds=options[CONF_SCAN_INTERVAL])
            except probatio.Invalid, OverflowError:
                errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
            else:
                return self.async_create_entry(
                    title="", data={**self.config_entry.options, **options}
                )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
            errors=errors,
        )
