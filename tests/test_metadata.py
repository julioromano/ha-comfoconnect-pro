"""Check distribution metadata and complete, synchronized English strings."""

import json
import tomllib
from pathlib import Path

from custom_components.comfoconnect_pro.binary_sensor import BINARY_SENSORS
from custom_components.comfoconnect_pro.button import RESET_ERRORS
from custom_components.comfoconnect_pro.const import MIN_HA_VERSION
from custom_components.comfoconnect_pro.number import NUMBERS
from custom_components.comfoconnect_pro.select import SELECTS
from custom_components.comfoconnect_pro.sensor import SENSORS
from custom_components.comfoconnect_pro.switch import SWITCHES

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/comfoconnect_pro"


def test_metadata_matches_project_and_minimum_version():
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert manifest["version"] == project["project"]["version"]
    assert hacs["homeassistant"] == MIN_HA_VERSION
    assert manifest["dependencies"] == ["modbus"]
    assert manifest["requirements"] == []


def test_english_strings_cover_all_entities():
    strings = json.loads((COMPONENT / "strings.json").read_text())
    assert strings == json.loads((COMPONENT / "translations/en.json").read_text())
    for platform, descriptions in {
        "sensor": SENSORS,
        "binary_sensor": BINARY_SENSORS,
        "select": SELECTS,
        "number": NUMBERS,
        "switch": SWITCHES,
        "button": (RESET_ERRORS,),
    }.items():
        for description in descriptions:
            translation = strings["entity"][platform][description.translation_key]
            assert translation["name"]
            assert translation["name"].format(
                **(description.translation_placeholders or {})
            )
