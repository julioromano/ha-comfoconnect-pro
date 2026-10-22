"""Diagnostics without connection addresses or persistent identifiers."""

from dataclasses import asdict
from typing import Any

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import ComfoConnectConfigEntry


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: ComfoConnectConfigEntry
) -> dict[str, Any]:
    """Include raw register values to investigate firmware differences."""
    data = entry.runtime_data.data
    return {
        "configuration": {**entry.data, CONF_HOST: "**REDACTED**"},
        "last_update_success": entry.runtime_data.last_update_success,
        "values": data.values,
        "raw_registers": data.raw,
        "unsupported": data.unsupported,
        "failed_fields": {
            key: asdict(failure) for key, failure in data.failed_fields.items()
        },
        "polled_optional_fields": data.polled_optional_fields,
    }
