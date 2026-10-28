# Supported models and Modbus register reference

Reviewed **2026-10-28**. This independent integration uses the manufacturer's Q/Flex interface through a ComfoConnect PRO configured for Modbus TCP.

## Authoritative sources

| Source | Edition and relevant pages | Establishes |
| --- | --- | --- |
| [Zehnder ComfoConnect PRO product datasheet](https://zehnder.hu/wp-content/uploads/2025/08/Zehnder_CSY_ComfoConnect-PRO_DAS_UK-en.pdf) | `ComfoConnect_PRO_Technical_Specification_2024_V2`, pp. 1 and 3 | Explicit Q350/Q450/Q600 and Flex 250/350 compatibility; page 3 includes preheater, handedness and Q enthalpy variants |
| [Zehnder ComfoConnect PRO installer manual](https://zehnderamerica.com/wp-content/uploads/2026/02/ComfoConnectPro-Installer-Manual.pdf) | `REV00-08-2025`; section 9.3, pp. 21–23, embedded Modbus document revision **137** | One Q/Flex register map, encodings, function codes and address convention; section 9.5, pp. 25–26, gives the published alarm identifiers |
| [Zehnder ComfoCool Q600 installer manual](https://zehnder-systems-si.zendesk.com/hc/en-us/article_attachments/4419064246033) | `849050624-0516`, English p. 22 (PDF page 22) | ComfoCool Q600 is intended for use with ComfoAir Q600 ST only |
| [Zehnder ComfoAir Flex installer/service manual](https://zehnder.hu/wp-content/uploads/2024/10/2-11_10001099246-1123-zw-zw-A4-ComfoAir-Flex-R2-Installer_Service-Zehnder-SI_-EN.pdf) | `10001099246-1123`, section 2.9.4, pp. 19–20 | Flex supports CO₂ sensor assignment to zones 1–8; this does not prove installed sensors or provide a different Modbus map |
| [Zehnder's current ComfoConnect PRO product page](https://www.zehnder.co.uk/en/indoor-ventilation/solutions/controls-sensors-connectivity/zehnder-comfoconnect-pro) | Web page reviewed 2026-10-28 | Names Q/Flex families and associated controls, sensors and accessories |

The register reference is the **2025 installer edition**, not the date in its upload URL. The [2024 installer edition](https://zehnder.lv/wp-content/uploads/2024/12/ComfoConnect-PRO-Installer-manual.pdf) also embeds revision 137, but its later sections have different page numbers. The [manufacturer's installer-manual landing page](https://zehnderamerica.com/resources/comfoconnect-pro-installer-manual/) is another route to the current download.

## Model applicability and verification

| Setup choice | Stored model ID | Shared Q/Flex map | ComfoCool permission | Registered entities / disabled accessories | Verification |
| --- | --- | --- | --- | --- | --- |
| ComfoAir Q350 | `comfoair_q350` | Yes | Omitted | 39 / 11 | Manufacturer specifications and simulated tests |
| ComfoAir Q450 | `comfoair_q450` | Yes | Omitted | 39 / 11 | Manufacturer specifications and simulated tests |
| ComfoAir Q600 | `comfoair_q600` | Yes | Optional; requires compatible Q600 ST installation | 40 / 12 | Physical Q600 with PRO; simulated tests |
| ComfoAir Flex 250 | `comfoair_flex250` | Yes | Omitted | 39 / 11 | Manufacturer specifications and simulated tests |
| ComfoAir Flex 350 | `comfoair_flex350` | Yes | Omitted | 39 / 11 | Manufacturer specifications and simulated tests |

The PRO table explicitly covers **ComfoAir Q/Flex** without separate per-model maps or an applicability column. Its embedded heading still says ComfoAirQ. Applying that family table to the five listed models is the integration's interpretation of the two manufacturer documents together; it is not evidence of physical validation of every model or accessory.

The **ComfoCool exclusion is inferred from the accessory's explicit compatibility restriction**, not from a model flag in the Modbus table. No other exclusions are established by the reviewed sources. Shared-map accessory entries below remain disabled until the user enables them. Their inclusion does not guarantee availability with every accessory, commissioning setup or firmware. Zero readback does not establish presence. Illegal-address responses on enabled accessories are recorded as unsupported and retried; transient errors remain separate.

Setup reads connection status only. Status 0 confirms interface availability, not the exact selected model, serial number or installed accessories. Model selection never changes gateway settings, register addresses or firmware.

### Classic and other families

Section 11, **page 28 of the 2025 PRO manual**, lists ComfoAir 160, 180, 200, 225, 350, 450, 550, SL220, SL330, Standard 300 and Standard 375 conditionally from software release 1.1. The published register interface is nevertheless scoped to Q/Flex, and the current product page names Q/Flex. The reviewed sources do not confirm that the Classic condition is fulfilled or establish a Classic Modbus map. These models are **not selectable in this integration** pending authoritative Modbus applicability documentation. This is a documentation gap, not a claim that Zehnder will never support them. Other product families and rebadged models are not inferred compatible.

## Address and applicability conventions

Manufacturer register numbers below are **one-based hexadecimal**, as printed in section 9.3. PDU addresses are **zero-based decimal**, used by the integration: manufacturer number minus one. Input registers (IR), holding registers (HR), coils (C) and discrete inputs (DI) are separate spaces; the same number in two spaces does not refer to the same value.

`Shared` means all five selectable models under the family map. `Optional` means a shared-map accessory, disabled by default and read only while enabled. `Q600 optional` additionally applies the documented accessory restriction above. Operating-mode dependencies affect availability, not model eligibility.

## Input registers — FC04, read only

The interface transports each entry in one 16-bit register, including fields published as `byte`. `short` is signed 16-bit; `ushort` is unsigned 16-bit. All rows are read only.

| Measurement/status | Manufacturer number | PDU address | Published type / decoding | HA sensor key | Applicability |
| --- | --- | --- | --- | --- | --- |
| Gateway connection status | `0x0001` | 0 | byte; 0 connected, 30 wrong device, 40 incompatible firmware, 50 no unit | `connection_state` | Shared; readable without a connected unit |
| Alarm slot 1 | `0x0002` | 1 | byte; numeric alarm identifier | `active_error_1` | Shared |
| Alarm slot 2 | `0x0003` | 2 | byte; numeric alarm identifier | `active_error_2` | Shared |
| Alarm slot 3 | `0x0004` | 3 | byte; numeric alarm identifier | `active_error_3` | Shared |
| Alarm slot 4 | `0x0005` | 4 | byte; numeric alarm identifier | `active_error_4` | Shared |
| Alarm slot 5 | `0x0006` | 5 | byte; numeric alarm identifier | `active_error_5` | Shared |
| Volume airflow | `0x0007` | 6 | ushort; m³/h | `airflow` | Shared |
| Room temperature | `0x0008` | 7 | short × 0.1 °C | `room_temperature` | Optional |
| Extract temperature | `0x0009` | 8 | short × 0.1 °C | `extract_temperature` | Shared |
| Exhaust temperature | `0x000A` | 9 | short × 0.1 °C | `exhaust_temperature` | Shared |
| Outdoor temperature | `0x000B` | 10 | short × 0.1 °C | `outdoor_temperature` | Shared |
| Supply temperature | `0x000C` | 11 | short × 0.1 °C | `supply_temperature` | Shared |
| Room humidity | `0x000D` | 12 | byte; unscaled % | `room_humidity` | Optional |
| Extract humidity | `0x000E` | 13 | byte; unscaled % | `extract_humidity` | Shared |
| Exhaust humidity | `0x000F` | 14 | byte; unscaled % | `exhaust_humidity` | Shared |
| Outdoor humidity | `0x0010` | 15 | byte; unscaled % | `outdoor_humidity` | Shared |
| Supply humidity | `0x0011` | 16 | byte; unscaled % | `supply_humidity` | Shared |
| CO₂ zone 1 | `0x0012` | 17 | ushort; ppm | `co2_zone_1` | Optional |
| CO₂ zone 2 | `0x0013` | 18 | ushort; ppm | `co2_zone_2` | Optional |
| CO₂ zone 3 | `0x0014` | 19 | ushort; ppm | `co2_zone_3` | Optional |
| CO₂ zone 4 | `0x0015` | 20 | ushort; ppm | `co2_zone_4` | Optional |
| CO₂ zone 5 | `0x0016` | 21 | ushort; ppm | `co2_zone_5` | Optional |
| CO₂ zone 6 | `0x0017` | 22 | ushort; ppm | `co2_zone_6` | Optional |
| CO₂ zone 7 | `0x0018` | 23 | ushort; ppm | `co2_zone_7` | Optional |
| CO₂ zone 8 | `0x0019` | 24 | ushort; ppm | `co2_zone_8` | Optional |
| Indicative filter life | `0x001A` | 25 | ushort; days | `filter_days_remaining` | Shared |

Alarm sensors retain numeric states and add the identifier from section 9.5 when known. The manufacturer labels that alarm list ComfoAirQ; it supplies no separate Flex alarm dictionary. Unknown values remain visible. Humidity outside 0–100% becomes unknown while the raw word remains available in diagnostics; the integration never guesses another scaling factor.

## Holding registers — FC03 read, FC06 write

All five are read/write and shared by all five models. HA controls provide the readback states; separate duplicate holding-register sensors are not created.

| Setting | Manufacturer number | PDU address | Published type / decoding | HA control | Operating constraint |
| --- | --- | --- | --- | --- | --- |
| Ventilation level | `0x0001` | 0 | byte; 0 away, 1 low, 2 medium, 3 high | Select `ventilation_preset` | No automatic change to Auto mode |
| Comfort profile | `0x0002` | 1 | byte; 0 normal, 1 cold, 2 warm | Select `temperature_profile` | Only in profile mode 0 or 1 |
| Profile calculation mode | `0x0003` | 2 | byte; 0 adaptive, 1 fixed, 2 external setpoint | Select `temperature_profile_mode` | Select explicitly before dependent controls |
| External comfort temperature | `0x0004` | 3 | ushort × 0.1 °C | Number `external_setpoint` | Only in profile mode 2 |
| Boost duration/countdown | `0x0005` | 4 | ushort; seconds; 65535 means 24 hours | Number `boost_duration` | Configured length before boost, remaining time during boost |

The map does not publish external-setpoint bounds. The HA control's **5–35 °C**, step **0.1 °C**, is integration UI policy inherited from the previous YAML control. The protocol's encoding range is 0–6553.5 °C. Readback is not clamped. Mode-dependent writes recheck the device mode; invalid or unreadable modes make the dependent controls unavailable. A write acknowledgment is not a guarantee of achieved temperature or airflow.

## Coils — FC01 read, FC05 write

Each coil is a read/write boolean in the published map. Trigger coils are written as true only and are not polled as persistent switches.

| Command/state | Manufacturer number | PDU address | HA entity or protocol action | Applicability / behavior |
| --- | --- | --- | --- | --- |
| Clear errors | `0x0001` | 0 | Button `reset_errors` | Shared; self-resetting trigger, false ignored; does not reset filter life |
| Request away level | `0x0002` | 1 | Protocol action `preset_away` | Shared; true trigger, false ignored; HA uses HR 0 through the preset select |
| Request low level | `0x0003` | 2 | Protocol action `preset_low` | Shared; true trigger, false ignored; HA uses the preset select |
| Request medium level | `0x0004` | 3 | Protocol action `preset_medium` | Shared; true trigger, false ignored; HA uses the preset select |
| Request high level | `0x0005` | 4 | Protocol action `preset_high` | Shared; true trigger, false ignored; HA uses the preset select |
| Automatic ventilation | `0x0006` | 5 | Switch `auto_mode` | Shared; boolean readback |
| Boost session | `0x0007` | 6 | Switch `boost` | Shared; boolean readback; duration in HR 4 |
| Away function | `0x0008` | 7 | Switch `away` | Shared; separate from the away-level command |
| Cooling permission | `0x0009` | 8 | Switch `comfocool` | Q600 optional; permission only, not active compressor status |

The four preset trigger aliases are available to the protocol implementation, not as additional HA entities or custom HA services. HA sends one requested write and reads back the resulting state. Device scheduling, sensor demand and safety controls can override a request.

## Discrete inputs — FC02, read only

All four are read-only booleans.

| Status | Manufacturer number | PDU address | HA binary-sensor key | Applicability |
| --- | --- | --- | --- | --- |
| Unit error | `0x0001` | 0 | `error` | Shared |
| Standby | `0x0002` | 1 | `standby` | Shared; no fan on/off control |
| Hood activity | `0x0003` | 2 | `comfohood` | Optional |
| Filter replacement flag | `0x0004` | 3 | `filter_dirty` | Shared |

This inventory covers **44 distinct register/coil entries**. Four preset trigger aliases share the existing preset-select capability, giving 40 HA entities for Q600 and 39 when ComfoCool is excluded. The manufacturer also lists FC15 and FC16; this integration uses single writes instead.

## Entity lifecycle and model corrections

`models.py` is the central model/capability registry. Model exclusions control entity creation, optional polling and protocol writes. Inapplicable entities are omitted; hiding would leave entities running, as described in [Home Assistant's entity-registry guidance](https://contributors.home-assistant.io/core/entities/registry/). Supported accessories use HA's ordinary disabled-by-default behavior and are enabled only by the user.

Reconfigure can correct the model on an existing installation after a successful read-only probe. Default titles and device metadata follow the model; custom names and common entity IDs, settings and refresh interval remain intact. Once setup refresh succeeds, obsolete integration-owned entities for that entry are removed from the registry. Changing Q600 to another model removes ComfoCool, including an enabled instance, and prevents its reads and writes. Automations referring to that removed entity need attention. Returning to Q600 recreates the entity with the same unique ID; HA's registry restoration rules govern restoration of its previous settings. No recorder-history purge is performed. A failed probe leaves the saved model and existing registry entries intact.

Existing Q600 entries need no configuration migration. Model selection does not create separate HA devices for optional controls or sensors, and compatibility with an accessory is not automatic discovery of that accessory.
