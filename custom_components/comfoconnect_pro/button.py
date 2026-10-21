"""Self-resetting maintenance command."""

from typing import final, override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ComfoConnectConfigEntry
from .entity import ComfoConnectEntity

RESET_ERRORS = ButtonEntityDescription(
    key="reset_errors",
    translation_key="reset_errors",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ComfoConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([ComfoConnectButton(entry.runtime_data, RESET_ERRORS)])


@final
class ComfoConnectButton(ComfoConnectEntity[ButtonEntityDescription], ButtonEntity):
    """A command sent once, never followed by a false write."""

    @override
    async def async_press(self) -> None:
        await self.coordinator.async_write(self.entity_description.key, True)
