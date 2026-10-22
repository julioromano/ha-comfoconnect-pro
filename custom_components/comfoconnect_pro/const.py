"""Integration constants."""

from homeassistant.const import Platform

DOMAIN = "comfoconnect_pro"
NAME = "Zehnder ComfoConnect PRO Modbus"
MIN_HA_VERSION = "2026.10.2"
MODEL_Q600 = "comfoair_q600"
MODEL_NAME = "ComfoAir Q600"
CONF_UNIT_ID = "unit_id"
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1
SCAN_INTERVAL_SECONDS = 30
# HA control policy, not manufacturer-specified device limits.
EXTERNAL_SETPOINT_MIN = 5
EXTERNAL_SETPOINT_MAX = 35
PLATFORMS = (
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.BUTTON,
)
