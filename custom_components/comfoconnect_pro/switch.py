"""Ordinary writable Modbus coils."""

from typing import Any, cast, final, override

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ComfoConnectConfigEntry
from .entity import ComfoConnectEntity

SWITCHES = tuple(
    SwitchEntityDescription(
        key=key, translation_key=key, entity_registry_enabled_default=key != "comfocool"
    )
    for key in ("auto_mode", "boost", "away", "comfocool")
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ComfoConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        ComfoConnectSwitch(entry.runtime_data, description)
        for description in SWITCHES
        if entry.runtime_data.device.profile.supports(description.key)
    )


@final
class ComfoConnectSwitch(ComfoConnectEntity[SwitchEntityDescription], SwitchEntity):
    """A coil that accepts both true and false."""

    @override
    def _update_state(self) -> None:
        super()._update_state()
        self._attr_is_on = cast(bool | None, self.field_value)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self.entity_description.key, True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self.entity_description.key, False)
