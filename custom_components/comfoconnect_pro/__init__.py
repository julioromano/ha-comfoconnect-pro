"""Zehnder ComfoConnect PRO Modbus TCP integration."""

from awesomeversion import AwesomeVersion
from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PORT, __version__
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams

from .const import CONF_UNIT_ID, DOMAIN, MIN_HA_VERSION, PLATFORMS
from .coordinator import ComfoConnectConfigEntry, ComfoConnectCoordinator
from .models import MODELS


async def async_setup_entry(
    hass: HomeAssistant, entry: ComfoConnectConfigEntry
) -> bool:
    """Create a unit handle; HA owns the socket and releases it on unload."""
    if AwesomeVersion(__version__) < AwesomeVersion(MIN_HA_VERSION):
        raise ConfigEntryError(f"Requires Home Assistant {MIN_HA_VERSION} or newer")
    if entry.data[CONF_MODEL] not in MODELS:
        raise ConfigEntryError(f"Unsupported {DOMAIN} model")
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    coordinator = ComfoConnectCoordinator(hass, entry, unit)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # Reconfiguration has unloaded the old platforms. Remove only this entry's
    # obsolete fields after a successful refresh; keep the common identities.
    obsolete_ids = {
        f"{entry.entry_id}_{key}" for key in coordinator.device.profile.excluded_fields
    }
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.platform == DOMAIN and entity.unique_id in obsolete_ids:
            registry.async_remove(entity.entity_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # The first refresh has no entity contexts. Hydrate any accessories the
    # entity registry restores as enabled now that platform listeners exist.
    await coordinator.async_refresh()
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ComfoConnectConfigEntry
) -> bool:
    """Unload entities; HA releases this entry's shared-connection hold."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
