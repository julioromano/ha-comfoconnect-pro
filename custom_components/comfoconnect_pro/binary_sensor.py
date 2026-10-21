"""Read-only ventilation status flags."""

from typing import cast, final, override

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ComfoConnectConfigEntry
from .entity import ComfoConnectEntity

BINARY_SENSORS = (
    BinarySensorEntityDescription(
        key="error",
        translation_key="error",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorEntityDescription(key="standby", translation_key="standby"),
    BinarySensorEntityDescription(
        key="filter_dirty",
        translation_key="filter_dirty",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorEntityDescription(
        key="comfohood",
        translation_key="comfohood",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ComfoConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        ComfoConnectBinarySensor(entry.runtime_data, description)
        for description in BINARY_SENSORS
    )


@final
class ComfoConnectBinarySensor(
    ComfoConnectEntity[BinarySensorEntityDescription], BinarySensorEntity
):
    """A discrete input, never exposed as a writable switch."""

    @override
    def _update_state(self) -> None:
        super()._update_state()
        self._attr_is_on = cast(bool | None, self.field_value)
