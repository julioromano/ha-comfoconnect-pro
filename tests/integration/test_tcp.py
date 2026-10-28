"""Verify MBAP framing, shared socket lifetime and reconnect using tmodbus."""

import asyncio
import struct
from contextlib import asynccontextmanager

import pytest
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PORT
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.comfoconnect_pro.const import DOMAIN
from custom_components.comfoconnect_pro.models import MODEL_Q600

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("socket_enabled")]


class Gateway:
    """A small independent FC01-06 TCP server implementing the published map."""

    def __init__(self):
        self.inputs = [0] * 26
        self.inputs[6] = 350
        self.inputs[10] = 0xFFC9
        self.holdings = [2, 0, 0, 210, 600]
        self.coils = [False] * 9
        self.discrete = [False, False, False, True]
        self.requests = []
        self.reject = set()
        self.clients = set()
        self.connection_count = 0
        self.empty = asyncio.Event()
        self.empty.set()

    async def handle(self, reader, writer):
        self.connection_count += 1
        self.clients.add(writer)
        self.empty.clear()
        try:
            while True:
                transaction, protocol, length, unit = struct.unpack(
                    ">HHHB", await reader.readexactly(7)
                )
                assert protocol == 0
                pdu = await reader.readexactly(length - 1)
                fc = pdu[0]
                address, count = struct.unpack(">HH", pdu[1:])
                self.requests.append((unit, fc, address, count))
                if (fc, address) in self.reject:
                    response = bytes([fc | 0x80, 2])
                elif fc in (3, 4):
                    values = (self.holdings if fc == 3 else self.inputs)[
                        address : address + count
                    ]
                    response = bytes([fc, count * 2]) + struct.pack(
                        f">{count}H", *values
                    )
                elif fc in (1, 2):
                    values = (self.coils if fc == 1 else self.discrete)[
                        address : address + count
                    ]
                    bits = sum(int(value) << i for i, value in enumerate(values))
                    width = (count + 7) // 8
                    response = bytes([fc, width]) + bits.to_bytes(width, "little")
                elif fc == 5:
                    assert count in (0, 0xFF00)
                    self.coils[address] = count == 0xFF00
                    response = pdu
                elif fc == 6:
                    self.holdings[address] = count
                    response = pdu
                else:
                    response = bytes([fc | 0x80, 1])
                writer.write(
                    struct.pack(">HHHB", transaction, 0, len(response) + 1, unit)
                    + response
                )
                await writer.drain()
        except asyncio.IncompleteReadError, ConnectionError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            self.clients.remove(writer)
            if not self.clients:
                self.empty.set()

    async def disconnect(self):
        for writer in tuple(self.clients):
            writer.close()
        await asyncio.wait_for(self.empty.wait(), 2)


@asynccontextmanager
async def gateway_server():
    gateway = Gateway()
    server = await asyncio.start_server(gateway.handle, "127.0.0.1", 0)
    try:
        yield gateway, server.sockets[0].getsockname()[1]
    finally:
        server.close()
        await server.wait_closed()
        await gateway.disconnect()


@pytest.mark.parametrize("model", [MODEL_Q600, "comfoair_flex350"])
async def test_tcp_setup_commands_sharing_and_reconnect(
    hass, enable_custom_integrations, model
):
    async with gateway_server() as (gateway, port):
        data = {
            CONF_HOST: "127.0.0.1",
            CONF_PORT: port,
            "unit_id": 7,
            CONF_MODEL: model,
        }
        first = MockConfigEntry(domain=DOMAIN, title="Ventilation", data=data)
        first.add_to_hass(hass)
        second = MockConfigEntry(
            domain=DOMAIN, title="Another unit", data={**data, "unit_id": 8}
        )
        try:
            assert await hass.config_entries.async_setup(first.entry_id)
            assert first.runtime_data.data.values["outdoor_temperature"] == -5.5
            assert first.runtime_data.data.values["filter_dirty"] is True
            assert gateway.requests[0] == (7, 4, 0, 1)
            assert (7, 4, 1, 6) in gateway.requests
            assert (7, 4, 8, 4) in gateway.requests
            assert not any(
                fc == 4 and address in {7, 12, *range(17, 25)}
                for _, fc, address, _ in gateway.requests
            )
            second.add_to_hass(hass)
            assert await hass.config_entries.async_setup(second.entry_id)
            assert gateway.connection_count == 1
            async with async_get_temporary_unit(
                hass, ModbusTcpParams(host="127.0.0.1", port=port), 7
            ) as unit:
                assert await unit.read_input_registers(6, 1) == [350]
            assert gateway.connection_count == 1
            await first.runtime_data.async_write("ventilation_preset", 3)
            await first.runtime_data.async_write("reset_errors", True)
            assert (7, 6, 0, 3) in gateway.requests
            assert gateway.requests.count((7, 5, 0, 0xFF00)) == 1
            assert gateway.holdings[0] == 3
            registry = er.async_get(hass)
            assert bool(
                registry.async_get_entity_id(
                    "switch", DOMAIN, f"{first.entry_id}_comfocool"
                )
            ) == (model == MODEL_Q600)
            assert not any(
                fc == 1 and address <= 8 < address + count
                for _, fc, address, count in gateway.requests
            )
            co2_id = registry.async_get_entity_id(
                "sensor", DOMAIN, f"{first.entry_id}_co2_zone_1"
            )
            registry.async_update_entity(co2_id, disabled_by=None)
            await hass.async_block_till_done()
            assert await hass.config_entries.async_reload(first.entry_id)
            assert first.runtime_data.data.polled_optional_fields == ("co2_zone_1",)
            assert (7, 4, 17, 1) in gateway.requests
            assert not any(
                fc == 4 and address == 18 for _, fc, address, _ in gateway.requests
            )
            gateway.reject.add((4, 17))
            await first.runtime_data.async_refresh()
            assert first.runtime_data.data.unsupported == ("co2_zone_1",)
            assert first.runtime_data.data.values["airflow"] == 350
            gateway.reject.add((4, 8))
            await first.runtime_data.async_refresh()
            assert first.runtime_data.last_update_success
            assert first.runtime_data.data.values["outdoor_temperature"] is None
            assert first.runtime_data.data.values["airflow"] == 350
            assert first.runtime_data.data.values["connection_state"] == 0
            assert (
                first.runtime_data.data.failed_fields[
                    "outdoor_temperature"
                ].exception_code
                == 2
            )
            gateway.reject.remove((4, 8))
            await first.runtime_data.async_refresh()
            assert first.runtime_data.data.values["outdoor_temperature"] == -5.5
            async with async_get_temporary_unit(
                hass, ModbusTcpParams(host="127.0.0.1", port=port), 7
            ) as unit:
                # Server-side close does not mean the client has received EOF.
                # Wait for the real backend notification before testing recovery.
                lost = asyncio.Event()
                unsubscribe = unit.on_connection_lost(lost.set)
                try:
                    await gateway.disconnect()
                    await asyncio.wait_for(lost.wait(), 2)
                finally:
                    unsubscribe()
            await second.runtime_data.async_refresh()
            assert second.runtime_data.last_update_success
            assert gateway.connection_count == 2
            assert await hass.config_entries.async_unload(first.entry_id)
            await second.runtime_data.async_refresh()
            assert second.runtime_data.last_update_success
            assert len(gateway.clients) == 1
            assert await hass.config_entries.async_unload(second.entry_id)
            await asyncio.wait_for(gateway.empty.wait(), 2)
        finally:
            for entry in (first, second):
                if entry.state.value == "loaded":
                    await hass.config_entries.async_unload(entry.entry_id)
