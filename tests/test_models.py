"""Documented model choices, capabilities and model-change lifecycle."""

import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from modbus_connection.exceptions import IllegalDataAddressError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.comfoconnect_pro.const import DOMAIN
from custom_components.comfoconnect_pro.protocol import OPTIONAL_FIELDS, ComfoAir

from .conftest import CONNECTION_DATA

# Independent expected choices from Zehnder's PRO datasheet, 2024 V2, page 3.
MODEL_CASES = (
    ("comfoair_q350", "ComfoAir Q350", False),
    ("comfoair_q450", "ComfoAir Q450", False),
    ("comfoair_q600", "ComfoAir Q600", True),
    ("comfoair_flex250", "ComfoAir Flex 250", False),
    ("comfoair_flex350", "ComfoAir Flex 350", False),
)
pytestmark = pytest.mark.usefixtures("enable_custom_integrations", "mock_connection")


@pytest.mark.parametrize("model,name,cooling", MODEL_CASES)
async def test_model_setup_is_read_only_and_uses_selected_title(
    hass, unit, model, name, cooling
):
    writes = []
    unit.on_write(writes.append)
    with patch(
        "custom_components.comfoconnect_pro.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={**CONNECTION_DATA, "model": model},
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == name
    assert result["data"]["model"] == model
    assert [(r.register_type, r.address, r.count) for r in unit.read_events] == [
        ("input", 0, 1)
    ]
    assert writes == []


def test_all_model_choices_have_english_labels():
    component = (
        Path(__file__).resolve().parents[1] / "custom_components/comfoconnect_pro"
    )
    strings = json.loads((component / "strings.json").read_text())
    assert strings["selector"]["model"]["options"] == {
        model: f"Zehnder {name}" for model, name, _ in MODEL_CASES
    }


@pytest.mark.parametrize("model,name,cooling", MODEL_CASES)
async def test_model_entities_and_accessory_defaults(
    hass, entry, unit, model, name, cooling
):
    hass.config_entries.async_update_entry(entry, data={**entry.data, "model": model})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert len(entities) == (40 if cooling else 39)
    assert sum(item.disabled for item in entities) == (12 if cooling else 11)
    assert len({item.device_id for item in entities}) == 1
    device = dr.async_get(hass).async_get(entities[0].device_id)
    assert device.model == name
    assert device.name == name
    assert (
        bool(
            registry.async_get_entity_id(
                "switch", DOMAIN, f"{entry.entry_id}_comfocool"
            )
        )
        == cooling
    )
    assert entry.runtime_data.data.values["outdoor_temperature"] == -5.5
    assert entry.runtime_data.data.polled_optional_fields == ()
    assert not any(
        r.register_type == "coil" and r.address <= 8 < r.address + r.count
        for r in unit.read_events
    )
    if not cooling:
        unit.read_events.clear()
        with pytest.raises(ServiceValidationError, match="comfocool"):
            await entry.runtime_data.async_write("comfocool", True)
        assert unit.read_events == []


@pytest.mark.parametrize("model,name,cooling", MODEL_CASES)
async def test_shared_protocol_and_model_capabilities(unit, model, name, cooling):
    device = ComfoAir(unit, model=model)
    data = await device.async_update(OPTIONAL_FIELDS)
    assert data.values["airflow"] == 350
    assert data.values["outdoor_temperature"] == -5.5
    assert data.values["room_temperature"] == 21.5
    assert data.values["co2_zone_8"] == 607
    assert ("comfocool" in data.values) == cooling
    assert ("comfocool" in data.polled_optional_fields) == cooling
    assert (8 in data.raw["coil"]) == cooling
    writes = []
    unit.on_write(writes.append)
    unit.read_events.clear()
    if cooling:
        await device.async_write("comfocool", True)
        assert [(w.address, w.values) for w in writes] == [(8, [True])]
    else:
        with pytest.raises(ValueError, match="comfocool"):
            await device.async_write("comfocool", True)
        assert unit.read_events == []
        assert writes == []
    await device.async_write("ventilation_preset", 3)
    assert unit.holding[0] == 3
    with pytest.raises(ValueError, match="external"):
        await device.async_write("external_setpoint", 22.5)
    await device.async_write("temperature_profile_mode", 2)
    await device.async_write("external_setpoint", 22.5)
    assert unit.holding[3] == 225
    with pytest.raises(ValueError, match="profile"):
        await device.async_write("temperature_profile", 1)
    unit.fail_read(8, IllegalDataAddressError(), register_type="input")
    data = await device.async_update(OPTIONAL_FIELDS)
    assert data.values["outdoor_temperature"] is None
    assert data.values["airflow"] == 350
    assert data.values["co2_zone_8"] == 607


@pytest.mark.parametrize("custom_title", [False, True])
async def test_reconfigure_model_round_trip_preserves_common_entities(
    hass, configured, unit, custom_title
):
    entry = configured
    registry = er.async_get(hass)
    hass.config_entries.async_update_entry(
        entry,
        title="Ventilation" if custom_title else entry.title,
        options={"scan_interval": 30},
    )
    cooling_id = registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_comfocool"
    )
    airflow_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_airflow"
    )
    registry.async_update_entity(
        airflow_id, name="My airflow", hidden_by=er.RegistryEntryHider.USER
    )
    room_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_room_temperature"
    )
    registry.async_update_entity(room_id, disabled_by=None)
    registry.async_update_entity(cooling_id, disabled_by=None)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(entry.entry_id)
    before = {
        item.unique_id: (
            item.entity_id,
            item.device_id,
            item.name,
            item.disabled_by,
            item.hidden_by,
        )
        for item in er.async_entries_for_config_entry(registry, entry.entry_id)
        if item.entity_id != cooling_id
    }
    device_id = registry.async_get(airflow_id).device_id
    dr.async_get(hass).async_update_device(device_id, name_by_user="My ventilation")
    # A different config entry must never lose its similarly named entity.
    other = MockConfigEntry(
        domain=DOMAIN, data={**CONNECTION_DATA, "host": "other.local"}
    )
    other.add_to_hass(hass)
    other_cooling = registry.async_get_or_create(
        "switch", DOMAIN, f"{other.entry_id}_comfocool", config_entry=other
    )
    writes = []
    unit.on_write(writes.append)
    # A failed probe must not save the model or remove an existing entity.
    unit.input[0] = 50
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": entry.entry_id},
        data={**CONNECTION_DATA, "model": "comfoair_flex350"},
    )
    assert result["errors"] == {"base": "no_ventilation_unit"}
    assert entry.data["model"] == "comfoair_q600"
    assert registry.async_get(cooling_id) is not None
    unit.input[0] = 0
    for model, name, cooling in (MODEL_CASES[4], MODEL_CASES[2]):
        unit.read_events.clear()
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "reconfigure", "entry_id": entry.entry_id},
            data={**CONNECTION_DATA, "model": model},
        )
        assert result["reason"] == "reconfigure_successful"
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert entry.title == ("Ventilation" if custom_title else name)
        assert entry.options == {"scan_interval": 30}
        assert entry.runtime_data.update_interval == timedelta(seconds=30)
        after = {
            item.unique_id: (
                item.entity_id,
                item.device_id,
                item.name,
                item.disabled_by,
                item.hidden_by,
            )
            for item in er.async_entries_for_config_entry(registry, entry.entry_id)
            if item.entity_id != cooling_id
        }
        assert after == before
        assert bool(registry.async_get(cooling_id)) == cooling
        assert registry.async_get(other_cooling.entity_id) is not None
        device = dr.async_get(hass).async_get(device_id)
        assert device.model == name
        assert device.name_by_user == "My ventilation"
        assert entry.runtime_data.data.values["room_temperature"] == 21.5
        if not cooling:
            assert hass.states.get(cooling_id) is None
            assert not any(
                r.register_type == "coil" and r.address <= 8 < r.address + r.count
                for r in unit.read_events
            )
    assert registry.async_get(cooling_id).unique_id == f"{entry.entry_id}_comfocool"
    assert writes == []
