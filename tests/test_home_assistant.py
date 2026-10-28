"""Exercise real config-entry lifecycle, entities and HA service calls."""

import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from modbus_connection.exceptions import IllegalDataAddressError, ModbusTimeoutError
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.comfoconnect_pro.diagnostics import (
    async_get_config_entry_diagnostics,
)


def entity_id(hass, entry, key, platform):
    return er.async_get(hass).async_get_entity_id(
        platform, "comfoconnect_pro", f"{entry.entry_id}_{key}"
    )


async def test_entities_metadata_and_optional_defaults(hass, configured):
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, configured.entry_id)
    assert len(entries) == 40
    assert len({item.device_id for item in entries}) == 1
    device = dr.async_get(hass).async_get(entries[0].device_id)
    assert device.manufacturer == "Zehnder"
    assert device.model == "ComfoAir Q600"
    assert configured.runtime_data.update_interval.total_seconds() == 5
    for item in entries:
        key = item.unique_id.removeprefix(f"{configured.entry_id}_")
        optional = key.startswith("co2_zone_") or key in {
            "room_temperature",
            "room_humidity",
            "comfocool",
            "comfohood",
        }
        assert (item.disabled_by is not None) == optional
        if not optional:
            assert hass.states.get(item.entity_id) is not None
    outdoor = hass.states.get(
        entity_id(hass, configured, "outdoor_temperature", "sensor")
    )
    assert outdoor.state == "-5.5"
    assert outdoor.attributes["unit_of_measurement"] == "°C"
    assert (
        hass.states.get(
            entity_id(hass, configured, "active_error_5", "sensor")
        ).attributes["code"]
        == "unknown_250"
    )


@pytest.mark.parametrize("options,interval", [({}, 5), ({"scan_interval": 30}, 30)])
async def test_scheduled_poll_uses_configured_interval(
    hass,
    entry,
    unit,
    mock_connection,
    enable_custom_integrations,
    freezer,
    options,
    interval,
):
    hass.config_entries.async_update_entry(entry, options=options)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    airflow_id = entity_id(hass, entry, "airflow", "sensor")
    assert entry.runtime_data.update_interval == timedelta(seconds=interval)
    unit.input[6] = 410

    freezer.tick(timedelta(seconds=interval - 2))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(airflow_id).state == "350"

    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(airflow_id).state == "410"


async def test_options_reload_applies_interval_and_preserves_identity(
    hass, configured, unit
):
    registry = er.async_get(hass)
    before = {
        item.unique_id: (item.entity_id, item.device_id)
        for item in er.async_entries_for_config_entry(registry, configured.entry_id)
    }
    previous_coordinator = configured.runtime_data
    writes = []
    unit.on_write(writes.append)
    result = await hass.config_entries.options.async_init(configured.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 30}
    )
    await hass.async_block_till_done()
    assert configured.state is ConfigEntryState.LOADED
    assert configured.runtime_data is not previous_coordinator
    assert configured.runtime_data.update_interval == timedelta(seconds=30)
    assert configured.options == {"scan_interval": 30}
    after = {
        item.unique_id: (item.entity_id, item.device_id)
        for item in er.async_entries_for_config_entry(registry, configured.entry_id)
    }
    assert after == before
    assert writes == []


async def test_controls_write_and_refresh_cached_states(hass, configured, unit):
    async def call(platform, service, key, **data):
        await hass.services.async_call(
            platform,
            service,
            {"entity_id": entity_id(hass, configured, key, platform), **data},
            blocking=True,
        )
        await hass.async_block_till_done()

    await call("select", "select_option", "ventilation_preset", option="high")
    assert unit.holding[0] == 3
    assert (
        hass.states.get(
            entity_id(hass, configured, "ventilation_preset", "select")
        ).state
        == "high"
    )
    for key in ("auto_mode", "boost", "away"):
        await call("switch", "turn_on", key)
        assert hass.states.get(entity_id(hass, configured, key, "switch")).state == "on"
        await call("switch", "turn_off", key)
        assert (
            hass.states.get(entity_id(hass, configured, key, "switch")).state == "off"
        )
    await call("select", "select_option", "temperature_profile", option="warm")
    assert unit.holding[1] == 2
    await call(
        "select",
        "select_option",
        "temperature_profile_mode",
        option="external_setpoint",
    )
    await call("number", "set_value", "external_setpoint", value=22.5)
    assert unit.holding[3] == 225
    await call("number", "set_value", "boost_duration", value=65535)
    state = hass.states.get(entity_id(hass, configured, "boost_duration", "number"))
    assert float(state.state) == 65535
    assert state.attributes["effective_duration_seconds"] == 86400
    writes = []
    unit.on_write(writes.append)
    await call("button", "press", "reset_errors")
    assert [(w.address, w.values) for w in writes] == [(0, [True])]


async def test_boost_duration_reports_configured_length_then_remaining_time(
    hass, configured, unit
):
    duration_id = entity_id(hass, configured, "boost_duration", "number")
    boost_id = entity_id(hass, configured, "boost", "switch")
    writes = []
    unit.on_write(writes.append)

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": duration_id, "value": 300},
        blocking=True,
    )
    assert float(hass.states.get(duration_id).state) == 300
    assert hass.states.get(boost_id).state == "off"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": boost_id}, blocking=True
    )
    assert hass.states.get(boost_id).state == "on"
    assert float(hass.states.get(duration_id).state) == 300

    for remaining in (285, 270, 1, 0):
        unit.holding[4] = remaining
        await configured.runtime_data.async_refresh()
        state = hass.states.get(duration_id)
        assert float(state.state) == remaining
        assert state.attributes["effective_duration_seconds"] == remaining

    assert [(w.address, w.values) for w in writes] == [(4, [300]), (6, [True])]


async def test_disconnected_unit_keeps_status_and_recovers(hass, configured, unit):
    unit.input[0] = 50
    await configured.runtime_data.async_refresh()
    assert (
        hass.states.get(entity_id(hass, configured, "connection_state", "sensor")).state
        == "no_ventilation_unit"
    )
    assert (
        hass.states.get(entity_id(hass, configured, "airflow", "sensor")).state
        == "unavailable"
    )
    unit.input[0] = 0
    unit.input[6] = 400
    await configured.runtime_data.async_refresh()
    assert (
        hass.states.get(entity_id(hass, configured, "airflow", "sensor")).state == "400"
    )


async def test_timeout_unavailability_and_recovery(hass, configured, unit):
    unit.fail_requests(ModbusTimeoutError())
    await configured.runtime_data.async_refresh()
    assert not configured.runtime_data.last_update_success
    assert (
        hass.states.get(entity_id(hass, configured, "connection_state", "sensor")).state
        == "unavailable"
    )
    unit.fail_requests(None)
    await configured.runtime_data.async_refresh()
    assert (
        hass.states.get(entity_id(hass, configured, "connection_state", "sensor")).state
        == "connected"
    )


async def test_unknown_values_remain_available_in_diagnostics(hass, configured, unit):
    unit.input[13] = 4550
    unit.holding[0] = 255
    unit.fail_read(17, IllegalDataAddressError(), register_type="input")
    await configured.runtime_data.async_refresh()
    assert (
        hass.states.get(entity_id(hass, configured, "extract_humidity", "sensor")).state
        == "unknown"
    )
    assert (
        hass.states.get(
            entity_id(hass, configured, "ventilation_preset", "select")
        ).state
        == "unknown"
    )
    data = await async_get_config_entry_diagnostics(hass, configured)
    assert data["raw_registers"]["input"][13] == 4550
    assert "gateway.local" not in json.dumps(data)
    assert configured.entry_id not in json.dumps(data)


async def test_service_errors(hass, configured, unit):
    with pytest.raises(ServiceValidationError, match="external"):
        await configured.runtime_data.async_write("external_setpoint", 22)
    unit.fail_write(4, ModbusTimeoutError())
    with pytest.raises(HomeAssistantError, match="write"):
        await configured.runtime_data.async_write("boost_duration", 300)


async def test_unload_releases_connection(hass, configured, connection):
    assert connection.connected
    assert await hass.config_entries.async_unload(configured.entry_id)
    assert configured.state is ConfigEntryState.NOT_LOADED
    assert not connection.connected


async def test_loaded_reconfigure_keeps_entity_and_device_identity(hass, configured):
    hass.config_entries.async_update_entry(configured, options={"scan_interval": 30})
    registry = er.async_get(hass)
    before = {
        item.unique_id: (item.entity_id, item.device_id)
        for item in er.async_entries_for_config_entry(registry, configured.entry_id)
    }
    result = await hass.config_entries.flow.async_init(
        "comfoconnect_pro",
        context={"source": "reconfigure", "entry_id": configured.entry_id},
        data={**configured.data, "host": "new-gateway.local"},
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    after = {
        item.unique_id: (item.entity_id, item.device_id)
        for item in er.async_entries_for_config_entry(registry, configured.entry_id)
    }
    assert before == after
    assert configured.data["host"] == "new-gateway.local"
    assert configured.state is ConfigEntryState.LOADED
    assert configured.options == {"scan_interval": 30}
    assert configured.runtime_data.update_interval == timedelta(seconds=30)


async def test_unknown_connection_status_is_preserved(hass, configured, unit):
    unit.input[0] = 255
    await configured.runtime_data.async_refresh()
    state = hass.states.get(entity_id(hass, configured, "connection_state", "sensor"))
    assert state.state == "unknown"
    assert state.attributes["raw_code"] == 255


async def test_manual_update_uses_the_coordinator(hass, configured, unit):
    assert await async_setup_component(hass, "homeassistant", {})
    unit.input[6] = 410
    await hass.services.async_call(
        "homeassistant",
        "update_entity",
        {"entity_id": entity_id(hass, configured, "airflow", "sensor")},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id(hass, configured, "airflow", "sensor")).state == "410"
    )


async def test_startup_retries_after_timeout(
    hass, entry, unit, mock_connection, enable_custom_integrations
):
    unit.fail_requests(ModbusTimeoutError())
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize(
    "version,model", [("2026.9.0", "comfoair_q600"), ("2026.10.2", "unsupported")]
)
async def test_unsupported_versions_and_models(
    hass, entry, mock_connection, enable_custom_integrations, version, model
):
    hass.config_entries.async_update_entry(entry, data={**entry.data, "model": model})
    with patch("custom_components.comfoconnect_pro.__version__", version):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR
