"""Reusable device data and Home Assistant fixtures."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.comfoconnect_pro.const import DOMAIN, MODEL_Q600

CONNECTION_DATA = {
    "host": "gateway.local",
    "port": 502,
    "unit_id": 1,
    "model": MODEL_Q600,
}


@pytest.fixture
def connection() -> MockModbusConnection:
    return MockModbusConnection()


@pytest.fixture
def unit(connection: MockModbusConnection) -> MockModbusUnit:
    """A simulated Q600 with recognizable values in every register."""
    result = connection.for_unit(1)
    result.input.update(dict.fromkeys(range(26), 0))
    result.input.update(
        {
            1: 21,
            2: 77,
            3: 79,
            4: 104,
            5: 250,
            6: 350,
            7: 215,
            8: 221,
            9: 155,
            10: 0xFFC9,
            11: 189,
            12: 45,
            13: 46,
            14: 47,
            15: 48,
            16: 49,
            **{17 + zone: 600 + zone for zone in range(8)},
            25: 180,
        }
    )
    result.holding.update({0: 2, 1: 0, 2: 0, 3: 210, 4: 600})
    result.coil.update(dict.fromkeys(range(9), False))
    result.coil[5] = True
    result.discrete.update({0: True, 1: False, 2: False, 3: True})
    return result


@pytest.fixture
def mock_connection(connection: MockModbusConnection):
    """Keep HA's real connection ownership while replacing only TCP I/O."""
    # Each acquire normally constructs a fresh backend after the last hold
    # closes. Reuse the simulated device stores across config-flow retries.
    with (
        patch.object(
            connection,
            "close",
            new=AsyncMock(side_effect=connection.simulate_connection_lost),
        ),
        patch(
            "homeassistant.components.modbus.connection.ModbusConnection",
            return_value=connection,
        ) as factory,
    ):
        yield factory


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    result = MockConfigEntry(domain=DOMAIN, title="ComfoAir Q600", data=CONNECTION_DATA)
    result.add_to_hass(hass)
    return result


@pytest.fixture
async def configured(hass, entry, mock_connection, unit, enable_custom_integrations):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
