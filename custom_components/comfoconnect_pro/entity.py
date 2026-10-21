"""Shared identity, availability and device association for all entities."""

from typing import override

from homeassistant.core import callback
from homeassistant.helpers.device_registry import ChildDeviceInfo, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import BaseCoordinatorEntity

from .coordinator import ComfoConnectCoordinator
from .protocol import Value


class ComfoConnectEntity[DescriptionT: EntityDescription](
    BaseCoordinatorEntity[ComfoConnectCoordinator]
):
    """One field on the Q600; identifiers survive connection reconfiguration."""

    _attr_has_entity_name: bool = True

    def __init__(
        self, coordinator: ComfoConnectCoordinator, description: DescriptionT
    ) -> None:
        super().__init__(coordinator)
        # Each platform fixes DescriptionT to its own HA description type.
        self.entity_description: DescriptionT = description  # pyright: ignore[reportIncompatibleVariableOverride]
        assert coordinator.config_entry is not None
        self._attr_unique_id: str | None = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )
        self._attr_device_info: DeviceInfo | ChildDeviceInfo | None = (
            coordinator.device_info
        )
        self._update_state()

    @property
    def field_value(self) -> Value:
        return self.coordinator.data.values.get(self.entity_description.key)

    @callback
    def _update_state(self) -> None:
        """Update HA's cache-invalidating attributes from one snapshot."""
        self._attr_available: bool = self.coordinator.last_update_success and (
            self.entity_description.key == "connection_state"
            or (
                self.coordinator.data.values.get("connection_state") == 0
                and self.entity_description.key not in self.coordinator.data.unsupported
            )
        )

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        self._update_state()
        self.async_write_ha_state()

    @override
    async def async_update(self) -> None:
        if self.enabled:
            await self.coordinator.async_request_refresh()
