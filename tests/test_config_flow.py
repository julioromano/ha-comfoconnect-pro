"""UI validation, error reporting, duplicate detection and reconfiguration."""

from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from modbus_connection.exceptions import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.comfoconnect_pro.config_flow import DATA_SCHEMA, normalize_host
from custom_components.comfoconnect_pro.const import DOMAIN

from .conftest import CONNECTION_DATA

pytestmark = pytest.mark.usefixtures("enable_custom_integrations", "mock_connection")


async def test_form_and_read_only_validation(hass, unit, connection):
    writes = []
    unit.on_write(writes.append)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    with patch(
        "custom_components.comfoconnect_pro.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": " GATEWAY.local. "}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == CONNECTION_DATA
    assert writes == []
    assert [
        (event.register_type, event.address, event.count) for event in unit.read_events
    ] == [("input", 0, 1)]
    assert not connection.connected


@pytest.mark.parametrize(
    "state,error",
    [
        (30, "wrong_device"),
        (40, "incompatible_version"),
        (50, "no_ventilation_unit"),
        (99, "unknown_connection_state"),
    ],
)
async def test_connection_status_errors(hass, unit, state, error):
    unit.input[0] = state
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=CONNECTION_DATA
    )
    assert result["errors"] == {"base": error}


@pytest.mark.parametrize(
    "exception",
    [ModbusTimeoutError(), HomeAssistantError("conflict"), OSError("unexpected")],
)
async def test_validation_exceptions(hass, unit, exception):
    unit.fail_requests(exception)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=CONNECTION_DATA
    )
    assert result["errors"] == {
        "base": "unknown" if type(exception) is OSError else "cannot_connect"
    }


async def test_duplicates_are_rejected_before_probe(hass, entry, unit):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={**CONNECTION_DATA, "host": "GATEWAY.local."},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert unit.read_events == []


@pytest.mark.parametrize(
    "updates",
    [
        {"host": "http://gateway.local"},
        {"port": 0},
        {"port": 502.5},
        {"port": float("nan")},
        {"unit_id": 248},
        {"model": "q350"},
    ],
)
async def test_invalid_input(hass, updates):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={**CONNECTION_DATA, **updates}
    )
    assert result["errors"] == {"base": "invalid_input"}


async def test_reconfigure_preserves_entry_and_validates_before_change(
    hass, entry, unit
):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    assert result["step_id"] == "reconfigure"
    unit.input[0] = 50
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**CONNECTION_DATA, "host": "new.local"}
    )
    assert result["errors"] == {"base": "no_ventilation_unit"}
    assert entry.data["host"] == "gateway.local"
    unit.input[0] = 0
    with patch(
        "custom_components.comfoconnect_pro.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**CONNECTION_DATA, "host": "NEW.local."}
        )
        await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["host"] == "new.local"


async def test_reconfigure_cannot_take_another_entry_endpoint(hass, entry):
    MockConfigEntry(
        domain=DOMAIN, data={**CONNECTION_DATA, "host": "other.local"}
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": entry.entry_id},
        data={**CONNECTION_DATA, "host": "other.local"},
    )
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "host,expected",
    [
        ("  GATEWAY.local. ", "gateway.local"),
        ("192.168.1.5", "192.168.1.5"),
        ("[2001:0DB8::1]", "2001:db8::1"),
    ],
)
def test_normalize_hosts(host, expected):
    assert normalize_host(host) == expected


def test_schema_defaults():
    assert DATA_SCHEMA({"host": "gateway.local"}) == CONNECTION_DATA
