"""UI setup and reconfiguration; probing never changes device settings."""

import ipaddress
import logging
import math
import re
from typing import Any, final, override

import probatio
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PORT
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
    DEFAULT_UNIT_ID,
    DOMAIN,
    MODEL_NAME,
    MODEL_Q600,
)
from .protocol import CONNECTION_STATES, ComfoAirQ600

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
        probatio.Required(CONF_HOST): probatio.All(TextSelector(), normalize_host),
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): probatio.All(
            NumberSelector(
                NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
            ),
            _integer,
        ),
        probatio.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): probatio.All(
            NumberSelector(
                NumberSelectorConfig(min=1, max=247, mode=NumberSelectorMode.BOX)
            ),
            _integer,
        ),
        probatio.Required(CONF_MODEL, default=MODEL_Q600): SelectSelector(
            SelectSelectorConfig(
                options=[MODEL_Q600],
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="model",
            )
        ),
    }
)


@final
class ComfoConnectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure the device rather than a separate YAML Modbus hub."""

    VERSION = 1

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
                    return self.async_update_reload_and_abort(entry, data_updates=data)
                else:
                    return self.async_create_entry(title=MODEL_NAME, data=data)
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
                state = await ComfoAirQ600(unit).async_validate()
        except ModbusError, HomeAssistantError:
            return "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected error validating ComfoConnect PRO")
            return "unknown"
        if state == 0:
            return None
        return CONNECTION_STATES.get(state, "unknown_connection_state")
