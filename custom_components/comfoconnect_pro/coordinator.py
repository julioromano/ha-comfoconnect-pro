"""Poll the model and adapt protocol errors to Home Assistant."""

import logging
import math
from datetime import timedelta
from typing import final, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError, ModbusUnit

from .const import (
    DOMAIN,
    EXTERNAL_SETPOINT_MAX,
    EXTERNAL_SETPOINT_MIN,
    MODEL_NAME,
    SCAN_INTERVAL_SECONDS,
)
from .protocol import OPTIONAL_FIELDS, ComfoAirQ600, Snapshot, Value

_LOGGER = logging.getLogger(__name__)
type ComfoConnectConfigEntry = ConfigEntry[ComfoConnectCoordinator]


@final
class ComfoConnectCoordinator(DataUpdateCoordinator[Snapshot]):
    """Poll one ventilation unit over an HA-owned shared connection."""

    def __init__(
        self, hass: HomeAssistant, entry: ComfoConnectConfigEntry, unit: ModbusUnit
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=MODEL_NAME,
            config_entry=entry,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
            always_update=False,
        )
        self.device = ComfoAirQ600(unit)
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=MODEL_NAME,
            manufacturer="Zehnder",
            model=MODEL_NAME,
        )

    @override
    async def _async_update_data(self) -> Snapshot:
        try:
            optional_fields = frozenset(self.async_contexts()) & OPTIONAL_FIELDS
            return await self.device.async_update(optional_fields)
        except ModbusError as err:
            raise UpdateFailed("Unable to read ComfoConnect PRO") from err

    async def async_write(self, key: str, value: Value) -> None:
        """Write, then read device state instead of assuming the command applied."""
        try:
            if key == "external_setpoint" and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not EXTERNAL_SETPOINT_MIN <= value <= EXTERNAL_SETPOINT_MAX
            ):
                limits = f"{EXTERNAL_SETPOINT_MIN}-{EXTERNAL_SETPOINT_MAX} °C"
                raise ValueError(f"External setpoint must be within {limits}")
            await self.device.async_write(key, value)
        except ValueError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_setting",
                translation_placeholders={"reason": str(err)},
            ) from err
        except ModbusError as err:
            # The next poll recovers normally; never retry a trigger blindly.
            await self.async_refresh()
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
            ) from err
        # A user command needs readback now, even inside the request debouncer's
        # cooldown after another command. The model serializes polls and writes.
        await self.async_refresh()
