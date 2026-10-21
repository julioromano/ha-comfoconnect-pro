"""Numeric settings using the manufacturer's documented wire ranges."""

from typing import cast, final, override

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ComfoConnectConfigEntry
from .entity import ComfoConnectEntity

NUMBERS = (
    NumberEntityDescription(
        key="external_setpoint",
        translation_key="external_setpoint",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0,
        native_max_value=6553.5,
        native_step=0.1,
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key="boost_duration",
        translation_key="boost_duration",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ComfoConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        ComfoConnectNumber(entry.runtime_data, description) for description in NUMBERS
    )


@final
class ComfoConnectNumber(ComfoConnectEntity[NumberEntityDescription], NumberEntity):
    """Write a numeric setting, refreshing its state afterwards."""

    @override
    def _update_state(self) -> None:
        super()._update_state()
        self._attr_native_value = cast(float | None, self.field_value)
        if self.entity_description.key == "boost_duration":
            self._attr_extra_state_attributes = {
                "effective_duration_seconds": 86400
                if self.field_value == 65535
                else self.field_value
            }

    @override
    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write(self.entity_description.key, value)
