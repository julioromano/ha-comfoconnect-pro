"""Measurements and diagnostic status from the published Q/Flex interface."""

from typing import cast, final, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfRatio,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .alarms import ALARM_CODES
from .coordinator import ComfoConnectConfigEntry
from .entity import ComfoConnectEntity
from .protocol import CONNECTION_STATES

SENSORS = (
    SensorEntityDescription(
        key="connection_state",
        translation_key="connection_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(CONNECTION_STATES.values()),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="airflow",
        translation_key="airflow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="filter_days_remaining",
        translation_key="filter_days_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
    ),
    *(
        SensorEntityDescription(
            key=f"active_error_{index}",
            translation_key="active_error",
            translation_placeholders={"slot": str(index)},
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        for index in range(1, 6)
    ),
    *(
        SensorEntityDescription(
            key=f"{location}_temperature",
            translation_key=f"{location}_temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
            entity_registry_enabled_default=location != "room",
        )
        for location in ("room", "extract", "exhaust", "outdoor", "supply")
    ),
    *(
        SensorEntityDescription(
            key=f"{location}_humidity",
            translation_key=f"{location}_humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
            entity_registry_enabled_default=location != "room",
        )
        for location in ("room", "extract", "exhaust", "outdoor", "supply")
    ),
    *(
        SensorEntityDescription(
            key=f"co2_zone_{zone}",
            translation_key="co2_zone",
            translation_placeholders={"zone": str(zone)},
            device_class=SensorDeviceClass.CO2,
            native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
        )
        for zone in range(1, 9)
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ComfoConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        ComfoConnectSensor(entry.runtime_data, description) for description in SENSORS
    )


@final
class ComfoConnectSensor(ComfoConnectEntity[SensorEntityDescription], SensorEntity):
    """One numeric measurement or translated connection status."""

    @override
    def _update_state(self) -> None:
        super()._update_state()
        if self.entity_description.key == "connection_state":
            self._attr_native_value = CONNECTION_STATES.get(cast(int, self.field_value))
            self._attr_extra_state_attributes = {"raw_code": self.field_value}
        else:
            self._attr_native_value = self.field_value
        if self.entity_description.key.startswith("active_error_"):
            code = cast(int | None, self.field_value)
            self._attr_extra_state_attributes = {
                "code": ALARM_CODES.get(code, f"unknown_{code}")
                if code is not None
                else None
            }
