"""HA-independent ComfoAir Q map from Zehnder installer manual, revision 137.

All addresses below are PDU addresses: manual register number minus one.
The caller owns the Modbus connection; this model consumes only a unit.
"""

import asyncio
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast, final

from modbus_connection import ModbusUnit
from modbus_connection.exceptions import (
    IllegalDataAddressError,
    ModbusExceptionError,
    ModbusTimeoutError,
)
from modbus_connection.model import Component, Raw, coil, discrete_input, gauge, integer

type Value = int | float | bool | None

PRESETS = {0: "away", 1: "low", 2: "medium", 3: "high"}
TEMPERATURE_PROFILES = {0: "normal", 1: "cold", 2: "warm"}
PROFILE_MODES = {0: "adaptive", 1: "fixed", 2: "external_setpoint"}
CONNECTION_STATES = {
    0: "connected",
    30: "wrong_device",
    40: "incompatible_version",
    50: "no_ventilation_unit",
}
OPTIONAL_FIELDS = frozenset(
    {"room_temperature", "room_humidity", "comfohood", "comfocool"}
    | {f"co2_zone_{zone}" for zone in range(1, 9)}
)
_NO_OPTIONAL_FIELDS: frozenset[str] = frozenset()


def _number(
    minimum: float, maximum: float, step: float = 1
) -> Callable[[object], float]:
    """Validate representable values without rounding invalid requests."""

    def validate(value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Expected a number")
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f"Expected a value between {minimum} and {maximum}")
        steps = (value - minimum) / step
        if not math.isclose(steps, round(steps), rel_tol=0, abs_tol=1e-7):
            raise ValueError(f"Expected increments of {step}")
        return value

    return validate


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError("Expected a boolean")
    return value


def _true_only(value: object) -> bool:
    if value is not True:
        raise ValueError("Command coils accept only true")
    return True


@final
class ConnectionStatus(Component):
    """Gateway-to-ventilation-unit status, readable even without a Q600."""

    register_space = "input"
    connection_state = integer(0, signed=False)


@final
class AlarmsAndAirflow(Component):
    """One contiguous block, isolated from temperature and humidity reads."""

    register_space = "input"
    register_ranges = ((1, 6),)
    active_error_1 = integer(1, signed=False)
    active_error_2 = integer(2, signed=False)
    active_error_3 = integer(3, signed=False)
    active_error_4 = integer(4, signed=False)
    active_error_5 = integer(5, signed=False)
    airflow = integer(6, signed=False, unit="m³/h")


@final
class Temperatures(Component):
    """Mandatory signed duct temperatures."""

    register_space = "input"
    register_ranges = ((8, 11),)
    extract_temperature = gauge(8, 0.1, unit="°C")
    exhaust_temperature = gauge(9, 0.1, unit="°C")
    outdoor_temperature = gauge(10, 0.1, unit="°C")
    supply_temperature = gauge(11, 0.1, unit="°C")


@final
class Humidity(Component):
    """Mandatory unscaled duct humidity percentages."""

    register_space = "input"
    register_ranges = ((13, 16),)
    extract_humidity = integer(13, signed=False, unit="%")
    exhaust_humidity = integer(14, signed=False, unit="%")
    outdoor_humidity = integer(15, signed=False, unit="%")
    supply_humidity = integer(16, signed=False, unit="%")


@final
class FilterLife(Component):
    """Indicative filter lifetime, separate from optional CO₂ registers."""

    register_space = "input"
    filter_days_remaining = integer(25, signed=False, unit="d")


@final
class Settings(Component):
    """Writable holding registers; no side effects on other settings."""

    register_ranges = ((0, 4),)
    ventilation_preset = integer(0, signed=False, writable=_number(0, 3))
    temperature_profile = integer(1, signed=False, writable=_number(0, 2))
    temperature_profile_mode = integer(2, signed=False, writable=_number(0, 2))
    # Zehnder specifies uint16 * 0.1, without a narrower functional range.
    external_setpoint = gauge(
        3, 0.1, signed=False, unit="°C", writable=_number(0, 6553.5, 0.1)
    )
    boost_duration = integer(4, signed=False, unit="s", writable=_number(0, 65535))


@final
class OperatingState(Component):
    """Ordinary read/write coils."""

    coil_ranges = ((5, 7),)
    auto_mode = coil(5, writable=_boolean)
    boost = coil(6, writable=_boolean)
    away = coil(7, writable=_boolean)


@final
class Commands(Component):
    """Trigger coils; never write false or poll them as latched switches."""

    reset_errors = coil(0, writable=_true_only)
    preset_away = coil(1, writable=_true_only)
    preset_low = coil(2, writable=_true_only)
    preset_medium = coil(3, writable=_true_only)
    preset_high = coil(4, writable=_true_only)


@final
class StatusFlags(Component):
    """Contiguous error and standby flags."""

    discrete_ranges = ((0, 1),)
    error = discrete_input(0)
    standby = discrete_input(1)


@final
class FilterStatus(Component):
    """Read filter status without including the optional hood address."""

    filter_dirty = discrete_input(3)


@final
class RoomTemperature(Component):
    """Optional room sensor temperature."""

    register_space = "input"
    room_temperature = gauge(7, 0.1, unit="°C")


@final
class RoomHumidity(Component):
    """Optional room sensor humidity."""

    register_space = "input"
    room_humidity = integer(12, signed=False, unit="%")


@final
class CO2Zone(Component):
    """Optional CO₂ register repeated for zones 1-8."""

    register_space = "input"
    concentration = integer(17, stride=1, signed=False, unit="ppm")


@final
class ComfoHood(Component):
    """Optional hood status."""

    comfohood = discrete_input(2)


@final
class ComfoCool(Component):
    """Optional cooling permission (not compressor running status)."""

    comfocool = coil(8, writable=_boolean)


@dataclass(frozen=True)
class ReadFailure:
    """Stable diagnostic details without exception messages or endpoint data."""

    error_type: str
    exception_code: int | None = None


@dataclass(frozen=True)
class Snapshot:
    """One poll; failed or skipped reads never reuse previous values."""

    values: dict[str, Value]
    raw: Raw
    unsupported: tuple[str, ...] = ()
    failed_fields: dict[str, ReadFailure] = field(default_factory=dict)
    polled_optional_fields: tuple[str, ...] = ()


@final
class ComfoAirQ600:
    """A Q600 behind a PRO gateway, independent of HA and the TCP backend."""

    def __init__(self, unit: ModbusUnit) -> None:
        self._lock = asyncio.Lock()
        self.status = ConnectionStatus(unit)
        self.settings = Settings(unit)
        self.operating = OperatingState(unit)
        self.commands = Commands(unit)
        self.cool = ComfoCool(unit)
        self._core = (
            AlarmsAndAirflow(unit),
            Temperatures(unit),
            Humidity(unit),
            FilterLife(unit),
            self.settings,
            self.operating,
            StatusFlags(unit),
            FilterStatus(unit),
        )
        self._optional: list[tuple[Component, dict[str, str]]] = [
            (RoomTemperature(unit), {"room_temperature": "room_temperature"}),
            (RoomHumidity(unit), {"room_humidity": "room_humidity"}),
            (ComfoHood(unit), {"comfohood": "comfohood"}),
            (self.cool, {"comfocool": "comfocool"}),
            *(
                (CO2Zone(unit, index=zone), {"concentration": f"co2_zone_{zone}"})
                for zone in range(1, 9)
            ),
        ]
        self._writers = {
            name: component
            for component in (self.settings, self.operating, self.commands, self.cool)
            for name in component.declared_fields
        }

    async def async_validate(self) -> int:
        """Read only the gateway's connection status during config validation."""
        await self.status.async_update()
        return cast(int, self.status.connection_state)

    async def async_update(
        self, optional_fields: frozenset[str] = _NO_OPTIONAL_FIELDS
    ) -> Snapshot:
        """Isolate rejected blocks and poll only explicitly requested accessories."""
        async with self._lock:
            raw = await self.status.async_read_raw()
            values: dict[str, Value] = {
                "connection_state": self.status.connection_state
            }
            if self.status.connection_state != 0:
                return Snapshot(values, raw)

            unsupported: list[str] = []
            failures: dict[str, ReadFailure] = {}
            polled: set[str] = set()
            timed_out = False

            async def read(
                component: Component, names: dict[str, str], *, optional: bool = False
            ) -> None:
                nonlocal timed_out
                try:
                    component_raw = await component.async_read_raw()
                except (ModbusExceptionError, ModbusTimeoutError) as err:
                    timed_out |= isinstance(err, ModbusTimeoutError)
                    for key in names.values():
                        values[key] = None
                        if optional and isinstance(err, IllegalDataAddressError):
                            unsupported.append(key)
                        else:
                            failures[key] = ReadFailure(
                                type(err).__name__,
                                err.exception_code
                                if isinstance(err, ModbusExceptionError)
                                else None,
                            )
                    return
                for space, registers in component_raw.items():
                    raw.setdefault(space, {}).update(registers)
                for field, key in names.items():
                    value = cast(Value, getattr(component, field))
                    # The official map uses unscaled percentages. Never guess
                    # another firmware's scale from the magnitude of one reading.
                    if (
                        key.endswith("_humidity")
                        and value is not None
                        and not 0 <= value <= 100
                    ):
                        value = None
                    values[key] = value

            for component in self._core:
                await read(
                    component, {name: name for name in component.declared_fields}
                )
            for component, names in self._optional:
                if optional_fields.intersection(names.values()):
                    polled.update(names.values())
                    await read(component, names, optional=True)
            if timed_out:
                # Do not keep the initial "connected" value if the link or
                # ventilation unit disappeared during the remaining requests.
                status_raw = await self.status.async_read_raw()
                if self.status.connection_state != 0:
                    return Snapshot(
                        {"connection_state": self.status.connection_state},
                        status_raw,
                        polled_optional_fields=tuple(sorted(polled)),
                    )
                raw["input"].update(status_raw["input"])
            return Snapshot(
                values,
                raw,
                unsupported=tuple(unsupported),
                failed_fields=failures,
                polled_optional_fields=tuple(sorted(polled)),
            )

    async def async_write(self, key: str, value: Value) -> None:
        """Validate and write exactly one setting or trigger."""
        async with self._lock:
            if key not in self._writers:
                raise ValueError(f"Unknown writable field: {key}")
            if await self.async_validate() != 0:
                raise ValueError("The ventilation unit is unavailable")
            if key in ("temperature_profile", "external_setpoint"):
                await self.settings.async_update()
                mode = self.settings.temperature_profile_mode
                if key == "external_setpoint" and mode != 2:
                    raise ValueError("Select external setpoint mode first")
                if key == "temperature_profile" and mode not in (0, 1):
                    raise ValueError(
                        "Temperature profile requires adaptive or fixed mode"
                    )
            await self._writers[key].write(key, value)
