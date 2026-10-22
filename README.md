# Zehnder ComfoConnect PRO Modbus

<img src="custom_components/comfoconnect_pro/brand/logo.png" alt="Zehnder" width="206">

A Home Assistant custom integration for a **Zehnder ComfoAir Q600** connected to a **ComfoConnect PRO in Modbus TCP mode**. Requires **Home Assistant 2026.10.2 or newer**.

**Unofficial, independent project.** This repository and its code are not affiliated with, developed by, sponsored by, endorsed by, or supported by Zehnder Group or any of its subsidiaries. Zehnder, ComfoAir and ComfoConnect names, trademarks and logos belong to their respective owners and are used solely to identify compatible equipment.

**Experimental: tested against simulated Modbus devices, not yet validated on physical Q600/PRO hardware.** The hardware acceptance checklist below tracks that remaining validation.

## Authoritative register documentation

The register map comes directly from **Zehnder**, the manufacturer:

- [Official ComfoConnect PRO installer-manual download page](https://zehnderamerica.com/resources/comfoconnect-pro-installer-manual/)
- [Manufacturer-hosted installer manual PDF, register map on page 21](https://zehnderamerica.com/wp-content/uploads/2026/02/ComfoConnectPro-Installer-Manual.pdf#page=21)

The linked manual is marked **REV00-08-2025**; its embedded Modbus interface is **document revision 137**. Section **9.3** contains the ComfoAir Q/Flex registers and coils, **9.4** gives request examples, and **9.5** lists alarm codes. This integration supports the Q600 only; the shared family map does not establish validation of other models.

Addresses in the manual start at one. The integration converts them to zero-based PDU addresses and keeps input registers, holding registers, coils and discrete inputs separate.

### Unit manuals and technical specifications

These official download URLs were used for the documentation review on **2026-10-22**. The Q-series manuals cover Q350/Q450/Q600; the specifications below are specific to Q600.

| Document | Revision / edition | Download |
| --- | --- | --- |
| ComfoAir Q user manual | `ZGNL_Manual_40014856`, V0218, English UK; 36 pages | [Zehnder support PDF](https://zehnder-systems-si.zendesk.com/hc/en-us/article_attachments/4417585040401) |
| ComfoAir Q installer manual | `ZGNL_Manual_40015975`, V0118, English; 20 pages | [Zehnder support PDF](https://zehnder-systems-si.zendesk.com/hc/en-us/article_attachments/4417585038993) |
| ComfoAir Q service manual | `Manual_10001004868`, V0218, English UK; 44 pages | [Zehnder support PDF](https://zehnder-systems-si.zendesk.com/hc/en-us/article_attachments/4417564641297) |
| Q600 technical specification | `ComfoAirQ600_Technical_Specification_2018_V3`; 16 pages | [Zehnder Estonia PDF](https://www.zehnder.ee/wp-content/uploads/2024/05/ComfoAir-Q600.pdf) |
| Q600 product datasheet | *ComfoAir Q 600 2024*, PDF created 2024-07-22; 8 pages | [Zehnder Lithuania PDF](https://zehnder.lt/wp-content/uploads/2024/10/Zehnder_CSY_ComfoAir-Q-600_ST_DAS_UK-en.pdf) |
| ComfoConnect PRO installer manual | REV00-09-2024; 30 pages | [Zehnder Latvia PDF](https://zehnder.lv/wp-content/uploads/2024/12/ComfoConnect-PRO-Installer-manual.pdf) |

The newer **REV00-08-2025** PRO manual linked above remains the authoritative register reference. Both PRO editions embed **Modbus document revision 137**. Upload-path dates do not establish document revisions. Downloaded PDFs and source records are kept locally under the ignored `.cache/reference-docs/zehnder/` directory and are not distributed with the integration.

The unit manuals explain operating behavior; they do not expose additional Modbus registers. Zehnder's [temperature-profile explanation](https://zehnder-systems-si.zendesk.com/hc/en-us/articles/4411130150417-CAQ-temperature-profile) and the older user manual differ numerically on adaptive temperature targets. The integration lets the unit calculate those targets. The related [ComfoConnect KNX C manual](https://zehnderamerica.com/wp-content/uploads/2024/08/ComfoConnect-KNX-C-Manual.pdf) provides additional terminology, but its units, command arbitration and timing are not assumed to apply to PRO Modbus.

## Installation

### Manual

1. Enable SSH access to Home Assistant. From this repository's root, copy the entire integration directory, including translations and the `brand` folder:

   ```sh
   ssh USER@HA_HOST 'mkdir -p /config/custom_components'
   scp -r custom_components/comfoconnect_pro USER@HA_HOST:/config/custom_components/
   ```

   Replace `USER` and `HA_HOST` with your HA SSH login and address. The resulting file must be `/config/custom_components/comfoconnect_pro/manifest.json`. For HA Container, replace `/config` with the host directory mounted as `/config`.
2. Restart Home Assistant. With the HA OS Terminal & SSH app, you can run `ssh USER@HA_HOST 'ha core restart'`.
3. Open **Settings → Devices & services → Add integration** and choose **Zehnder ComfoConnect PRO Modbus**.
4. Enter the **gateway's** hostname/IP, TCP port (default `502`), unit ID (default `1`) and model **ComfoAir Q600**.

For a custom SSH port, add `-p PORT` to `ssh` and `-P PORT` to `scp`. If SCP reports an unavailable SFTP subsystem, add `-O` to `scp`.

### HACS custom repository

The repository includes HACS metadata. Once it is hosted on GitHub, add its GitHub URL under **HACS → Custom repositories**, choose **Integration**, download it, restart HA, then add the integration above. It has not been submitted to the HACS default directory.

The integration bundles Zehnder icons and logos at standard and high resolution in its `brand` folder, following [Home Assistant's local branding convention](https://contributors.home-assistant.io/core/integrations/brands/). The unmodified images come from the [Home Assistant ComfoConnect brand assets](https://github.com/home-assistant/brands/tree/master/core_integrations/comfoconnect).

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

The integration registers 40 entities on one Q600 device. Twelve accessory entities start disabled and are not polled until enabled; enable the relevant ones in the entity settings if those accessories are installed. Home Assistant may reload the entry after an entity is enabled. Enabled accessories are populated after platform setup and on subsequent polls. A successful read of zero does not prove an accessory is installed.

| Entities | Behavior |
| --- | --- |
| Ventilation preset | Away, Low, Medium, High select |
| Temperature profile / profile mode | Normal/Cold/Warm and Adaptive/Fixed/External setpoint selects |
| External temperature setpoint | Number in °C, in 0.1 °C steps |
| Auto mode, boost, away function | Separate command switches; resulting states are read from the unit |
| Boost duration | Configured session length in seconds; remaining time while boost is active |
| Reset errors | Button sending a single true command |
| Airflow | Volume flow in m³/h |
| Extract, exhaust, outdoor and supply temperatures/humidity | Measurement sensors |
| Filter days remaining / filter dirty | Indicative remaining-life sensor and replacement flag |
| Connection state / error / standby | Diagnostic status and read-only flags |
| Active errors 1–5 | Numeric codes with an alarm-identifier attribute; unknown codes are retained |
| Optional: room temperature/humidity, CO₂ zones 1–8 | Disabled by default |
| Optional: ComfoHood / ComfoCool permission | Disabled status sensor / permission switch |

Preset airflows are configured during commissioning: Low, Medium and High do not imply fixed percentages or specific m³/h values. Schedules, demand controls and safety controls may override the requested airflow. The integration displays actual readback and does not repeatedly reapply commands to counter those controls. The temporary-override timing described for the unit's display is not a guarantee for Modbus commands.

Away selects minimum ventilation. The Away preset and Away-function switch expose separate documented commands whose effects can be related by the device. The integration sends only the requested command and reads back the resulting settings; exact PRO coupling remains part of hardware validation. Standby is read-only, so this integration does not expose fan on/off actions.

Selecting a preset does not silently disable Auto mode. Change Auto explicitly when needed, because it affects scheduling and sensor controls. The temperature-profile control is unavailable outside Adaptive or Fixed mode; the external-setpoint control is unavailable outside External setpoint mode. Unknown or unreadable modes make both dependent controls unavailable. Choose the mode explicitly before changing those values; each write validates the current device mode again.

The HA external-setpoint control accepts **5–35 °C**, in **0.1 °C** steps. This is an **integration UI policy matching the previous YAML control**, not a manufacturer-defined device limit. The reviewed manuals supply no external-setpoint minimum or maximum. Fixed-profile defaults such as 18/20/24 °C and the unit's air/storage/installation temperature ranges are not setpoint bounds. The HA-independent protocol retains the unsigned-register encoding range of 0–6553.5 °C. Existing device readback outside the HA control range remains visible without clamping; HA commands outside 5–35 °C are rejected. Acknowledging a Modbus write does not guarantee the unit can achieve that comfort temperature.

Boost duration accepts **0–65535 seconds**. The special value **65535 means 24 hours**, and the entity exposes `effective_duration_seconds: 86400` for that value. Set the configured session length before activating boost. Once boost is enabled, the device updates the same register with the **remaining time**, so the number also acts as a countdown, refreshed on each 15-second poll. The displayed value therefore reflects remaining time during boost rather than retaining the original session length. Changing it while boost is active does not promise to restart or extend the current timer; that behavior requires PRO hardware validation.

ComfoCool permission allows the unit to decide whether cooling may run. It does not report compressor activity or force cooling to start. Scheduling, season, Away, fan state, bypass state, temperatures and faults can prevent cooling even when permission is enabled.

Filter days remaining is indicative and depends on operation and airflow. Complete the unit's filter-replacement wizard when replacing filters; that procedure resets the filter counter. Reset-errors sends a single trigger to clear errors. It does not replace the filter wizard, reset filter life or repair the underlying fault; unresolved errors may return.

Humidity follows the manufacturer's unscaled percentage definition. Values outside 0–100 become unknown; the original word remains in diagnostics. The integration does not infer a different scale from individual readings.

## Updates, failures and diagnostics

The integration polls every 15 seconds and reads back immediately after a write. Device code uses typed `modbus_connection.model` components. Home Assistant owns the shared TCP connection through `async_get_unit` and temporary setup probes through `async_get_temporary_unit`, following the [modern Modbus integration architecture](https://home-assistant-libs.github.io/modbus-connection/home-assistant/integration/). No YAML hub or separate socket is needed.

Core reads use separate contiguous blocks for alarms/airflow, duct temperatures, duct humidity, filter life, settings, operating coils, error/standby flags and filter status. A device-rejected block or isolated request timeout makes only that block's entities unavailable. Other successfully read groups remain usable, including connection status. Failed fields and their raw words are cleared for that cycle and retried on subsequent polls. An illegal address on an enabled accessory is recorded as unsupported, separately from transient failures, and is also retried.

After any isolated timeout, the integration rechecks connection status once before accepting a partial snapshot. Connection/protocol failures or a failed status probe make the whole update unavailable; normal polling recovers when communication returns. If the gateway reports a disconnected or incompatible ventilation unit, only its connection-status entity remains readable and ventilation commands are blocked. Writes are not replayed by the integration after an error. The shared backend's timeout default is retained; the PRO manual's minimum 2000 ms statement appears in its RTU section and does not establish a TCP timeout or polling interval.

Download diagnostics from the integration's menu for decoded values, raw registers, unsupported optional fields, transient failed fields with error types/codes, and the optional fields polled. Exception messages are excluded to avoid exposing endpoint details. The host is redacted, and config-entry/device identifiers are omitted. If reporting a firmware discrepancy, include gateway/unit firmware versions and compare raw values with the Zehnder display.

## Migrating from YAML Modbus

Back up your YAML and record existing entity references before migration. Add the integration, enable only installed accessories, then update dashboards, scripts and automations to use its entities. Remove or disable the old hub and template controls before returning automations to normal operation. YAML hubs use a separate connection and their entities are not automatically adopted by this integration. History is not automatically transferred. Existing entries of this custom integration keep their entity and device identities when upgraded or reconfigured.

Actual entity IDs can differ because of custom names or suffixes. Find them on the integration's device page. The usual new prefix is `comfoair_q600`; the earlier YAML used `comfoair_q`. Replace direct YAML `modbus.write_register`/`modbus.write_coil` calls with the corresponding `select.select_option`, `number.set_value`, `switch.turn_on`/`switch.turn_off`, or `button.press` action.

The five holding-register sensors are replaced by the states of their controls:

| Previous YAML sensor | Integration control key | State |
| --- | --- | --- |
| `sensor.comfoair_q_ventilation_preset` | Select `ventilation_preset` | `away`, `low`, `medium`, `high` |
| `sensor.comfoair_q_temperature_profile` | Select `temperature_profile` | `normal`, `cold`, `warm` |
| `sensor.comfoair_q_temperature_profile_mode` | Select `temperature_profile_mode` | `adaptive`, `fixed`, `external_setpoint` |
| `sensor.comfoair_q_external_setpoint` | Number `external_setpoint` | °C |
| `sensor.comfoair_q_boost_time` | Number `boost_duration` | Configured seconds, then remaining time while boost is active; `65535` means 24 hours |

Update comparisons and selected options from title-case YAML strings (`Away`, `Low`, `Normal`, `External setpoint`) to lowercase keys (`away`, `low`, `normal`, `external_setpoint`). The frontend still displays translated labels. Replace numeric preset/profile comparisons with those keys. For connection state, replace `0` with `connected`, `30` with `wrong_device`, `40` with `incompatible_version`, and `50` with `no_ventilation_unit`; the numeric value remains in `raw_code`. Alarm sensors retain their numeric states and add symbolic code attributes. Account for mode-dependent control availability and use actual readback after commands.

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
- [ ] Check preset arbitration in Auto/Manual, scheduled changes and sensor/safety overrides; do not assume the display's temporary-override timing applies to Modbus.
- [ ] Verify Away preset/switch coupling and resulting ComfoCool permission without additional client-side writes.
- [ ] Check all temperature modes, unavailable controls, a normal comfort setpoint within the HA 5–35 °C range, and unchanged readback when another controller sets a value outside that range.
- [ ] Test boost duration before activation and remaining-time readback while active, changes while active, early cancellation and the `65535` 24-hour value; record actual timer behavior.
- [ ] Enable only installed accessories and verify their values; confirm enabling/disabling changes polling and absent accessories leave core entities working.
- [ ] Confirm ComfoCool permission is not mistaken for active cooling and compare indicative filter life with the unit's display.
- [ ] Confirm a failed register group affects only its entities and values recover without reloading when reads succeed again.
- [ ] Test connection loss/recovery, restart, reconfiguration and unload while another integration holds the shared connection.
- [ ] Validate reset-errors on a suitable test condition, confirm it sends one trigger, and distinguish it from the unit's filter-replacement wizard.

Modbus RTU, cloud access, discovery and models other than Q600 are outside v0.1.0.

## License

This project is licensed under the [MIT License](LICENSE).
