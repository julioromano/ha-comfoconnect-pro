"""Zehnder PRO-compatible models and documented capability restrictions.

The PRO datasheet (2024 V2) lists these five models. Its installer manual
REV00-08-2025, section 9.3, publishes one Q/Flex map (Modbus revision 137).
The ComfoCool installer manual (849050624-0516), English page 22, restricts
that accessory to Q600 ST. No other model exclusions are established.
"""

from dataclasses import dataclass
from types import MappingProxyType

MODEL_Q600 = "comfoair_q600"


@dataclass(frozen=True)
class ModelProfile:
    """Display name and fields that do not apply to this ventilation model."""

    name: str
    excluded_fields: frozenset[str] = frozenset()

    def supports(self, key: str) -> bool:
        """Apply documented exclusions without guessing accessory presence."""
        return key not in self.excluded_fields


_NO_COMFOCOOL = frozenset({"comfocool"})
MODELS = MappingProxyType(
    {
        "comfoair_q350": ModelProfile("ComfoAir Q350", _NO_COMFOCOOL),
        "comfoair_q450": ModelProfile("ComfoAir Q450", _NO_COMFOCOOL),
        MODEL_Q600: ModelProfile("ComfoAir Q600"),
        "comfoair_flex250": ModelProfile("ComfoAir Flex 250", _NO_COMFOCOOL),
        "comfoair_flex350": ModelProfile("ComfoAir Flex 350", _NO_COMFOCOOL),
    }
)
