"""Behavior of the manufacturer's Modbus map, independent of HA entities."""

import pytest
from modbus_connection.exceptions import IllegalDataAddressError, ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit

from custom_components.comfoconnect_pro.protocol import OPTIONAL_FIELDS, ComfoAirQ600


async def test_decodes_register_spaces_and_signed_temperature(unit: MockModbusUnit):
    device = ComfoAirQ600(unit)
    data = await device.async_update(OPTIONAL_FIELDS)
    assert data.values["connection_state"] == 0
    assert data.values["airflow"] == 350
    assert data.values["outdoor_temperature"] == -5.5
    assert data.values["supply_temperature"] == 18.9
    assert data.values["extract_humidity"] == 46
    assert data.values["ventilation_preset"] == 2
    assert data.values["auto_mode"] is True
    assert data.values["filter_dirty"] is True
    assert data.values["co2_zone_8"] == 607
    assert data.raw["input"][10] == 0xFFC9


async def test_optional_register_rejection_does_not_disable_core(unit: MockModbusUnit):
    unit.fail_read(17, IllegalDataAddressError(), register_type="input")
    data = await ComfoAirQ600(unit).async_update(OPTIONAL_FIELDS)
    assert data.values["co2_zone_1"] is None
    assert data.values["co2_zone_2"] == 601
    assert data.values["airflow"] == 350
    assert "co2_zone_1" in data.unsupported


async def test_timeout_is_not_treated_as_optional_absence(unit: MockModbusUnit):
    unit.fail_read(17, ModbusTimeoutError(), register_type="input")
    data = await ComfoAirQ600(unit).async_update(OPTIONAL_FIELDS)
    assert "co2_zone_1" not in data.unsupported
    assert "co2_zone_1" in data.failed_fields
    assert data.values["airflow"] == 350


async def test_preset_writes_only_the_requested_register(unit: MockModbusUnit):
    writes = []
    unit.on_write(writes.append)
    await ComfoAirQ600(unit).async_write("ventilation_preset", 3)
    assert [(w.function_code, w.address, w.values) for w in writes] == [(6, 0, [3])]
    assert unit.coil[5] is True


@pytest.mark.parametrize(
    "command,address",
    [
        ("reset_errors", 0),
        ("preset_away", 1),
        ("preset_low", 2),
        ("preset_medium", 3),
        ("preset_high", 4),
    ],
)
async def test_command_coils_write_true_once(unit: MockModbusUnit, command, address):
    writes = []
    unit.on_write(writes.append)
    device = ComfoAirQ600(unit)
    await device.async_write(command, True)
    assert [(w.function_code, w.address, w.values) for w in writes] == [
        (5, address, [True])
    ]
    with pytest.raises(ValueError):
        await device.async_write(command, False)


async def test_temperature_dependencies_are_checked_without_changing_mode(
    unit: MockModbusUnit,
):
    device = ComfoAirQ600(unit)
    with pytest.raises(ValueError, match="external"):
        await device.async_write("external_setpoint", 22.5)
    unit.holding[2] = 2
    await device.async_write("external_setpoint", 22.5)
    assert unit.holding[3] == 225
    with pytest.raises(ValueError, match="profile"):
        await device.async_write("temperature_profile", 1)


async def test_every_measurement_and_status_field(unit):
    data = await ComfoAirQ600(unit).async_update(OPTIONAL_FIELDS)
    assert data.values == {
        "connection_state": 0,
        **{
            f"active_error_{i + 1}": code
            for i, code in enumerate((21, 77, 79, 104, 250))
        },
        "airflow": 350,
        "room_temperature": 21.5,
        "extract_temperature": 22.1,
        "exhaust_temperature": 15.5,
        "outdoor_temperature": -5.5,
        "supply_temperature": 18.9,
        **{
            f"{location}_humidity": 45 + i
            for i, location in enumerate(
                ("room", "extract", "exhaust", "outdoor", "supply")
            )
        },
        **{f"co2_zone_{i + 1}": 600 + i for i in range(8)},
        "filter_days_remaining": 180,
        "ventilation_preset": 2,
        "temperature_profile": 0,
        "temperature_profile_mode": 0,
        "external_setpoint": 21.0,
        "boost_duration": 600,
        "auto_mode": True,
        "boost": False,
        "away": False,
        "error": True,
        "standby": False,
        "filter_dirty": True,
        "comfohood": False,
        "comfocool": False,
    }
    assert data.raw["holding"] == {0: 2, 1: 0, 2: 0, 3: 210, 4: 600}
    assert data.raw["discrete"] == {0: True, 1: False, 2: False, 3: True}
    assert data.raw["coil"] == {5: True, 6: False, 7: False, 8: False}


@pytest.mark.parametrize(
    "key,value",
    [
        ("ventilation_preset", -1),
        ("ventilation_preset", 4),
        ("ventilation_preset", True),
        ("temperature_profile_mode", 1.5),
        ("boost_duration", 65536),
        ("boost_duration", float("nan")),
        ("boost_duration", float("inf")),
        ("boost_duration", None),
        ("external_setpoint", 21.15),
        ("auto_mode", 1),
        ("airflow", 100),
    ],
)
async def test_invalid_writes_never_reach_device(unit, key, value):
    unit.holding[2] = 2
    writes = []
    unit.on_write(writes.append)
    with pytest.raises(ValueError):
        await ComfoAirQ600(unit).async_write(key, value)
    assert writes == []


@pytest.mark.parametrize(
    "key,value,address,space",
    [
        ("ventilation_preset", 0, 0, "holding"),
        ("temperature_profile", 1, 1, "holding"),
        ("temperature_profile_mode", 2, 2, "holding"),
        ("external_setpoint", 6553.5, 3, "holding"),
        ("boost_duration", 65535, 4, "holding"),
        ("auto_mode", False, 5, "coil"),
        ("boost", True, 6, "coil"),
        ("away", True, 7, "coil"),
        ("comfocool", True, 8, "coil"),
    ],
)
async def test_all_writable_settings(unit, key, value, address, space):
    unit.holding[2] = 2 if key == "external_setpoint" else 0
    writes = []
    unit.on_write(writes.append)
    await ComfoAirQ600(unit).async_write(key, value)
    assert len(writes) == 1
    assert writes[0].register_type == space
    assert writes[0].address == address
    assert writes[0].values == [65535 if key == "external_setpoint" else value]


@pytest.mark.parametrize("state", [30, 40, 50, 255])
async def test_disconnected_unit_reads_status_only_and_rejects_writes(unit, state):
    unit.input[0] = state
    device = ComfoAirQ600(unit)
    data = await device.async_update()
    assert data.values == {"connection_state": state}
    assert len(unit.read_events) == 1
    with pytest.raises(ValueError, match="unavailable"):
        await device.async_write("boost", True)


async def test_optional_values_are_cleared_and_can_recover(unit):
    device = ComfoAirQ600(unit)
    assert (await device.async_update(OPTIONAL_FIELDS)).values[
        "room_temperature"
    ] == 21.5
    unit.fail_read(7, IllegalDataAddressError(), register_type="input")
    data = await device.async_update(OPTIONAL_FIELDS)
    assert data.values["room_temperature"] is None
    assert 7 not in data.raw["input"]
    unit.fail_read(7, None, register_type="input")
    assert (await device.async_update(OPTIONAL_FIELDS)).values[
        "room_temperature"
    ] == 21.5
