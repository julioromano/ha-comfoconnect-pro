"""Documented enumerated settings, without invented on/off semantics."""

from dataclasses import dataclass
from typing import cast, final, override

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ComfoConnectConfigEntry
from .entity import ComfoConnectEntity
from .protocol import PRESETS, PROFILE_MODES, TEMPERATURE_PROFILES


@dataclass(frozen=True, kw_only=True)
class ComfoConnectSelectDescription(SelectEntityDescription):
    """The wire values corresponding to translated options."""

    values: dict[int, str]


SELECTS = tuple(
    ComfoConnectSelectDescription(
        key=key, translation_key=key, values=values, options=list(values.values())
    )
    for key, values in (
        ("ventilation_preset", PRESETS),
        ("temperature_profile", TEMPERATURE_PROFILES),
        ("temperature_profile_mode", PROFILE_MODES),
    )
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ComfoConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        ComfoConnectSelect(entry.runtime_data, description) for description in SELECTS
    )


@final
class ComfoConnectSelect(ComfoConnectEntity[SelectEntityDescription], SelectEntity):
    """One enumerated setting; selection writes just its register."""

    @override
    def _update_state(self) -> None:
        super()._update_state()
        description = cast(ComfoConnectSelectDescription, self.entity_description)
        self._attr_current_option = description.values.get(cast(int, self.field_value))

    @override
    async def async_select_option(self, option: str) -> None:
        description = cast(ComfoConnectSelectDescription, self.entity_description)
        value = next(
            key for key, label in description.values.items() if label == option
        )
        await self.coordinator.async_write(self.entity_description.key, value)
