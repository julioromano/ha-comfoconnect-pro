# Zehnder ComfoConnect PRO Modbus

A Home Assistant custom integration for a **Zehnder ComfoAir Q600** connected to a **ComfoConnect PRO in Modbus TCP mode**. Requires **Home Assistant 2026.10.2 or newer**.

**Experimental: tested against simulated Modbus devices, not yet validated on physical Q600/PRO hardware.** The hardware acceptance checklist below tracks that remaining validation.

## Authoritative register documentation

The register map comes directly from **Zehnder**, the manufacturer:

- [Official ComfoConnect PRO installer-manual download page](https://zehnderamerica.com/resources/comfoconnect-pro-installer-manual/)
- [Manufacturer-hosted installer manual PDF, register map on page 21](https://zehnderamerica.com/wp-content/uploads/2026/02/ComfoConnectPro-Installer-Manual.pdf#page=21)

The linked manual is marked **REV00-08-2025**; its embedded Modbus interface is **document revision 137**. Section **9.3** contains the ComfoAir Q/Flex registers and coils, **9.4** gives request examples, and **9.5** lists alarm codes. This integration supports the Q600 only; the shared family map does not establish validation of other models.

Addresses in the manual start at one. The integration converts them to zero-based PDU addresses and keeps input registers, holding registers, coils and discrete inputs separate.

## Installation

### Manual

1. Copy `custom_components/comfoconnect_pro` into your HA configuration directory as `config/custom_components/comfoconnect_pro`.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration** and choose **Zehnder ComfoConnect PRO Modbus**.

### HACS custom repository

The repository includes HACS metadata. Once it is hosted on GitHub, add its GitHub URL under **HACS → Custom repositories**, choose **Integration**, download it, restart HA, then add the integration above. It has not been submitted to the HACS default directory.

## Gateway preparation and configuration

Commission the gateway and ventilation unit with Zehnder's tools first. Enable **Modbus TCP** in the gateway's **Protocols & Services** settings and confirm the ComfoNet connection works. The integration does not configure gateway firmware or network settings.

The HA form asks for:

| Setting | Default |
| --- | --- |
| Hostname or IP address | Required |
| TCP port | `502` |
| Modbus unit ID | `1`, configurable from `1` to `247` |
| Ventilation model | ComfoAir Q600 |

Setup performs a read-only connection-status probe. Select the actual model yourself: this register map cannot identify the exact Q-series model or its serial number.

Use **Reconfigure** on the integration to change an address, port or unit ID for the same device. Entity identifiers remain stable. Duplicate normalized host/port/unit combinations are rejected. DNS aliases and an IP address pointing to the same gateway cannot be recognized as the same physical device; use a consistent endpoint spelling across integrations to share the connection.

## Entities

The integration registers 40 entities on one Q600 device. Twelve accessory entities start disabled; enable the relevant ones in the entity settings if those accessories are installed. A successful read of zero does not prove an accessory is installed.

| Entities | Behavior |
| --- | --- |
| Ventilation preset | Away, Low, Medium, High select |
| Temperature profile / profile mode | Normal/Cold/Warm and Adaptive/Fixed/External setpoint selects |
| External temperature setpoint | Number in °C, in 0.1 °C steps |
| Auto mode, boost, away function | Independent switches |
| Boost duration | Number in seconds |
| Reset errors | Button sending a single true command |
| Airflow | Volume flow in m³/h |
| Extract, exhaust, outdoor and supply temperatures/humidity | Measurement sensors |
| Filter days remaining / filter dirty | Remaining-life sensor and problem flag |
| Connection state / error / standby | Diagnostic status and read-only flags |
| Active errors 1–5 | Numeric codes with an alarm-identifier attribute; unknown codes are retained |
| Optional: room temperature/humidity, CO₂ zones 1–8 | Disabled by default |
| Optional: ComfoHood / ComfoCool permission | Disabled status sensor / permission switch |

Away is a ventilation preset, not a shutdown command. Standby is read-only, so this integration does not expose fan on/off actions.

Each command changes only the requested setting. Selecting a preset does not silently disable auto mode. The temperature profile can be changed only in Adaptive or Fixed mode; an external setpoint can be changed only in External setpoint mode. Choose the mode explicitly before changing those values.

The setpoint number exposes the documented unsigned-register encoding range, **0–6553.5 °C**; the manual supplies no narrower operating range. This represents encoding limits, not a recommended comfort-temperature range. Device-rejected settings are reported as errors.

Boost duration accepts **0–65535 seconds**. The special value **65535 means 24 hours**, and the entity exposes `effective_duration_seconds: 86400` for that value. The number is the configured duration, not a remaining-time countdown.

Humidity follows the manufacturer's unscaled percentage definition. Values outside 0–100 become unknown; the original word remains in diagnostics. The integration does not infer a different scale from individual readings.

## Updates, failures and diagnostics

The integration polls every 30 seconds and reads back immediately after a write. Device code uses typed `modbus_connection.model` components. Home Assistant owns the shared TCP connection through `async_get_unit` and temporary setup probes through `async_get_temporary_unit`, following the [modern Modbus integration architecture](https://home-assistant-libs.github.io/modbus-connection/home-assistant/integration/). No YAML hub or separate socket is needed.

Transport failures make entities unavailable; polling recovers when the connection returns. If the gateway is reachable but cannot see the ventilation unit, its connection-status entity remains readable. An unsupported optional address affects only that accessory. Writes are not replayed by the integration after an error.

Download diagnostics from the integration's menu for decoded values, raw registers and unsupported optional fields. The host is redacted, and config-entry/device identifiers are omitted. If reporting a firmware discrepancy, include gateway/unit firmware versions and compare raw values with the Zehnder display.

## Development

Use Python 3.14 and `uv`. HA's Modbus requirements determine compatible backend versions; the integration itself adds no transport dependency pins.

```sh
uv sync --frozen
uv run ruff format --check
uv run ruff check
uv run basedpyright
uv run pytest -m 'not integration'
uv run pytest tests/integration --no-cov
```

Unit tests use fake Modbus units while exercising HA's real setup, entity services and shared-connection ownership. The TCP test uses an independent local server and the actual tmodbus backend. It verifies unit IDs, function codes, addresses, socket sharing, reconnect and final-consumer cleanup.

CI enforces 95% unit-test statement/branch coverage and uploads XML/HTML reports even when tests fail. TCP tests run separately without a coverage threshold. HA's hassfest validates integration metadata. The bundled protocol module has no HA imports and can be extracted into a separate library if additional consumers need it.

The [Daikin EKRHH integration](https://github.com/gerione/daikin-ha-ekrhh-modbus) was a functional reference for UI setup and device-specific entities. This implementation uses the current HA shared Modbus APIs.

## Hardware acceptance checklist

- [ ] Record Q600 and PRO firmware versions; confirm Modbus TCP mode and the configured unit ID.
- [ ] Add the integration and compare airflow, temperatures, humidity, filter life and alarms with Zehnder's display/app.
- [ ] Check negative outdoor temperatures and retain raw diagnostics if humidity differs from the manual.
- [ ] Exercise each preset, auto, boost and away; verify independent writes and subsequent readback.
- [ ] Check profile-mode constraints, a normal room-temperature external setpoint, and boost duration including the 24-hour special value.
- [ ] Enable only installed accessories and verify their values; confirm absent accessories leave core entities working.
- [ ] Test connection loss/recovery, restart, reconfiguration and unload while another integration holds the shared connection.
- [ ] Validate reset-errors on a suitable test condition and confirm it sends one trigger.

Modbus RTU, cloud access, discovery and models other than Q600 are outside v0.1.0.
