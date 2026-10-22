"""Mode-aware controls, HA policy limits and accessory lifecycle."""

from datetime import timedelta

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from modbus_connection.exceptions import IllegalDataAddressError, ServerDeviceBusyError
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.comfoconnect_pro.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .test_home_assistant import entity_id


@pytest.mark.parametrize(
    "mode,profile_available,setpoint_available",
    [(0, True, False), (1, True, False), (2, False, True), (255, False, False)],
)
async def test_temperature_controls_follow_current_mode(
    hass, configured, unit, mode, profile_available, setpoint_available
):
    unit.holding[2] = mode
    await configured.runtime_data.async_refresh()
    for platform, key, available in [
        ("select", "temperature_profile", profile_available),
        ("number", "external_setpoint", setpoint_available),
    ]:
        state = hass.states.get(entity_id(hass, configured, key, platform))
        assert (state.state != "unavailable") == available
    unit.fail_read(0, IllegalDataAddressError(), register_type="holding")
    await configured.runtime_data.async_refresh()
    for platform, key in [
        ("select", "temperature_profile"),
        ("number", "external_setpoint"),
    ]:
        assert (
            hass.states.get(entity_id(hass, configured, key, platform)).state
            == "unavailable"
        )


async def test_setpoint_ui_policy_does_not_clamp_readback(hass, configured, unit):
    unit.holding.update({2: 2, 3: 400})
    await configured.runtime_data.async_refresh()
    eid = entity_id(hass, configured, "external_setpoint", "number")
    state = hass.states.get(eid)
    assert float(state.state) == 40
    assert (
        state.attributes["min"],
        state.attributes["max"],
        state.attributes["step"],
    ) == (5, 35, 0.1)
    for value in (5, 22.5, 35):
        await hass.services.async_call(
            "number", "set_value", {"entity_id": eid, "value": value}, blocking=True
        )
        assert unit.holding[3] == round(value * 10)
    writes = []
    unit.on_write(writes.append)
    for value in (4.9, 35.1, float("nan"), float("inf"), True, None):
        with pytest.raises(ServiceValidationError):
            await configured.runtime_data.async_write("external_setpoint", value)
    assert writes == []


async def test_mode_is_checked_again_at_write_time(hass, configured, unit):
    unit.holding[2] = 2
    await configured.runtime_data.async_refresh()
    unit.holding[2] = 0
    with pytest.raises(ServiceValidationError, match="external"):
        await configured.runtime_data.async_write("external_setpoint", 22)
    assert unit.holding[3] == 210
    assert unit.holding[2] == 0
    unit.holding[2] = 2
    with pytest.raises(ServiceValidationError, match="profile"):
        await configured.runtime_data.async_write("temperature_profile", 1)


async def test_partial_failure_keeps_successful_entities_and_redacted_diagnostics(
    hass, configured, unit
):
    unit.fail_read(
        8, ServerDeviceBusyError(message="gateway.local"), register_type="input"
    )
    await configured.runtime_data.async_refresh()
    assert configured.runtime_data.last_update_success
    assert (
        hass.states.get(
            entity_id(hass, configured, "outdoor_temperature", "sensor")
        ).state
        == "unavailable"
    )
    assert (
        hass.states.get(entity_id(hass, configured, "airflow", "sensor")).state == "350"
    )
    assert (
        hass.states.get(entity_id(hass, configured, "connection_state", "sensor")).state
        == "connected"
    )
    data = await async_get_config_entry_diagnostics(hass, configured)
    assert data["failed_fields"]["outdoor_temperature"] == {
        "error_type": "ServerDeviceBusyError",
        "exception_code": 6,
    }
    assert data["polled_optional_fields"] == ()
    assert 10 not in data["raw_registers"]["input"]
    assert "gateway.local" not in str(data)


async def test_disabled_accessories_are_not_read_at_setup(hass, configured, unit):
    assert configured.runtime_data.data.polled_optional_fields == ()
    assert all(
        not (r.register_type == "input" and r.address in {7, 12, *range(17, 25)})
        for r in unit.read_events
    )
    assert "comfohood" not in configured.runtime_data.data.values
    assert "comfocool" not in configured.runtime_data.data.values


async def test_restored_enabled_accessory_is_read_after_platform_setup(
    hass, entry, unit, mock_connection, enable_custom_integrations
):
    registry = er.async_get(hass)
    saved = registry.async_get_or_create(
        "sensor",
        "comfoconnect_pro",
        f"{entry.entry_id}_room_temperature",
        config_entry=entry,
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(saved.entity_id).state == "21.5"
    assert entry.runtime_data.data.polled_optional_fields == ("room_temperature",)


async def test_accessory_enable_disable_and_reload_preserve_identity(
    hass, configured, unit
):
    registry = er.async_get(hass)
    eid = entity_id(hass, configured, "room_temperature", "sensor")
    before = registry.async_get(eid)
    registry.async_update_entity(eid, disabled_by=None)
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert hass.states.get(eid).state == "21.5"
    assert configured.runtime_data.data.polled_optional_fields == ("room_temperature",)
    assert registry.async_get(eid).unique_id == before.unique_id
    assert registry.async_get(eid).device_id == before.device_id
    registry.async_update_entity(eid, disabled_by=er.RegistryEntryDisabler.USER)
    await hass.async_block_till_done()
    unit.read_events.clear()
    await configured.runtime_data.async_refresh()
    assert configured.runtime_data.data.polled_optional_fields == ()
    assert all(
        not (r.register_type == "input" and r.address == 7) for r in unit.read_events
    )
    assert await hass.config_entries.async_reload(configured.entry_id)
    assert registry.async_get(eid).unique_id == before.unique_id
