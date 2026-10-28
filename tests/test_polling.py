"""Independent register failures and explicit optional-field polling."""

from unittest.mock import patch

import pytest
from modbus_connection.exceptions import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusExceptionError,
    ModbusProtocolError,
    ModbusTimeoutError,
    ServerDeviceBusyError,
)

from custom_components.comfoconnect_pro.protocol import ComfoAir


@pytest.mark.parametrize(
    "space,address,fields",
    [
        ("input", 1, {"airflow", *(f"active_error_{i}" for i in range(1, 6))}),
        (
            "input",
            8,
            {f"{x}_temperature" for x in ("extract", "exhaust", "outdoor", "supply")},
        ),
        (
            "input",
            13,
            {f"{x}_humidity" for x in ("extract", "exhaust", "outdoor", "supply")},
        ),
        ("input", 25, {"filter_days_remaining"}),
        (
            "holding",
            0,
            {
                "ventilation_preset",
                "temperature_profile",
                "temperature_profile_mode",
                "external_setpoint",
                "boost_duration",
            },
        ),
        ("coil", 5, {"auto_mode", "boost", "away"}),
        ("discrete", 0, {"error", "standby"}),
        ("discrete", 3, {"filter_dirty"}),
    ],
)
async def test_failed_block_clears_only_its_values_and_recovers(
    unit, space, address, fields
):
    device = ComfoAir(unit)
    before = await device.async_update()
    unit.fail_read(address, IllegalDataAddressError(), register_type=space)
    failed = await device.async_update()
    assert set(failed.failed_fields) == fields
    assert failed.unsupported == ()
    for key, value in before.values.items():
        assert failed.values[key] == (None if key in fields else value)
    for key in fields:
        assert failed.failed_fields[key].error_type == "IllegalDataAddressError"
        assert failed.failed_fields[key].exception_code == 2
    assert address not in failed.raw.get(space, {})
    unit.fail_read(address, None, register_type=space)
    assert await device.async_update() == before


async def test_core_poll_never_reads_optional_addresses(unit):
    data = await ComfoAir(unit).async_update()
    assert data.polled_optional_fields == ()
    assert "room_temperature" not in data.values
    assert [(r.register_type, r.address, r.count) for r in unit.read_events] == [
        ("input", 0, 1),
        ("input", 1, 6),
        ("input", 8, 4),
        ("input", 13, 4),
        ("input", 25, 1),
        ("holding", 0, 5),
        ("coil", 5, 3),
        ("discrete", 0, 2),
        ("discrete", 3, 1),
    ]


async def test_only_requested_accessories_are_polled(unit):
    selected = frozenset(
        {"room_temperature", "room_humidity", "co2_zone_8", "comfohood", "comfocool"}
    )
    data = await ComfoAir(unit).async_update(selected)
    assert data.polled_optional_fields == tuple(sorted(selected))
    assert data.values["co2_zone_8"] == 607
    assert "co2_zone_1" not in data.values
    assert 17 not in data.raw["input"]
    assert data.raw["coil"][8] is False
    assert data.raw["discrete"][2] is False


@pytest.mark.parametrize(
    "error", [ModbusTimeoutError(), ServerDeviceBusyError(), ModbusExceptionError(200)]
)
async def test_accessory_failures_are_transient_and_do_not_hide_core(unit, error):
    unit.fail_read(17, error, register_type="input")
    data = await ComfoAir(unit).async_update(frozenset({"co2_zone_1"}))
    assert data.values["airflow"] == 350
    assert data.values["co2_zone_1"] is None
    assert data.unsupported == ()
    assert data.failed_fields["co2_zone_1"].error_type == type(error).__name__
    assert data.failed_fields["co2_zone_1"].exception_code == getattr(
        error, "exception_code", None
    )
    status_reads = [
        r for r in unit.read_events if r.register_type == "input" and r.address == 0
    ]
    assert len(status_reads) == (2 if isinstance(error, ModbusTimeoutError) else 1)


@pytest.mark.parametrize("error", [ModbusConnectionError(), ModbusProtocolError()])
async def test_transport_failures_abort_the_poll(unit, error):
    unit.fail_read(8, error, register_type="input")
    with pytest.raises(type(error)):
        await ComfoAir(unit).async_update()
    assert unit.read_events[-1].address == 8


async def test_timeout_requires_successful_status_recheck(unit):
    read = unit.read_input_registers
    status_reads = 0

    async def failing_recheck(address, count):
        nonlocal status_reads
        if address == 0:
            status_reads += 1
            if status_reads == 2:
                unit.fail_requests(ModbusTimeoutError())
        return await read(address, count)

    unit.fail_read(8, ModbusTimeoutError(), register_type="input")
    with patch.object(unit, "read_input_registers", side_effect=failing_recheck):
        with pytest.raises(ModbusTimeoutError):
            await ComfoAir(unit).async_update()
    assert status_reads == 2


async def test_timeout_recheck_can_report_disconnected_ventilation_unit(unit):
    read = unit.read_input_registers

    async def disconnect_target(address, count):
        if address == 17:
            unit.input[0] = 50
        return await read(address, count)

    unit.fail_read(17, ModbusTimeoutError(), register_type="input")
    with patch.object(unit, "read_input_registers", side_effect=disconnect_target):
        data = await ComfoAir(unit).async_update(frozenset({"co2_zone_1"}))
    assert data.values == {"connection_state": 50}
    assert data.raw == {"input": {0: 50}}
    with pytest.raises(ValueError, match="unavailable"):
        await ComfoAir(unit).async_write("boost", True)
