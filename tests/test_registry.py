# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for fpc.registry, the catalogue behind the CLI, MCP server and llms.txt.

Several tests here are *library-wide quality checks*: they loop over every
calculation, so a new method that forgets a unit tag or a docstring fails CI.
"""

import json
import math
from pathlib import Path

import numpy as np
import pytest

from fpc import Q_, Fluids, registry

ROOT = Path(__file__).resolve().parent.parent


def test_catalogue_covers_the_domains():
    keys = {calc.key for calc in registry.calculations()}
    assert "Fluids.reynolds_number" in keys
    assert "Radiation.half_value_layer" in keys
    # File-handling classes are deliberately left out (see EXCLUDED_CLASSES).
    assert not any(k.startswith(("Utility.", "Dicom.", "Beam.")) for k in keys)
    assert len(keys) > 100


@pytest.mark.parametrize("calc", registry.calculations(), ids=lambda c: c.key)
def test_every_calculation_is_documented_and_json_callable(calc):
    assert calc.summary, f"{calc.key} needs a docstring"
    assert calc.json_callable, f"{calc.key} has a required input JSON cannot carry"
    for p in calc.parameters:
        assert p.description, f"{calc.key}: document parameter {p.name!r} with :param"
    # The schema must survive a JSON round trip: that is what the MCP client sees.
    assert json.loads(json.dumps(calc.input_schema()))["type"] == "object"


def test_every_numeric_parameter_has_a_unit_tag():
    # Dimensionless numbers are tagged [-]; anything else names its unit.
    assert registry.missing_units() == []


def test_docstring_parsing():
    calc = registry.get("Fluids.reynolds_number")
    density = calc.parameters[0]
    assert (density.name, density.unit, density.required) == ("density", "kg/m^3", True)
    assert calc.returns.endswith("[-]")
    assert "laminar" in calc.description


def test_schema_types_follow_type_hints():
    schema = registry.get("Properties.interpolate").input_schema()["properties"]
    assert schema["table"] == {"type": "string", "description": schema["table"]["description"]}
    assert schema["method"]["enum"] == ["linear", "cubic"]
    assert schema["method"]["default"] == "linear"
    assert "anyOf" in schema["x"]  # a number or an array


def test_get_unknown_key_suggests_matches():
    with pytest.raises(KeyError, match="reynolds_number"):
        registry.get("Fluids.reynolds")


def test_search_ranks_name_matches_first():
    assert registry.search("reynolds")[0].key == "Fluids.reynolds_number"
    assert all(c.domain == "Thermo" for c in registry.search("heat", domain="thermo"))


def test_calculate_matches_a_direct_call():
    args = {"density": 998.0, "velocity": 2.0, "length": 0.05, "viscosity": 1e-3}
    assert registry.calculate("Fluids.reynolds_number", args) == Fluids().reynolds_number(**args)


def test_calculate_converts_lists_to_arrays():
    result = registry.calculate(
        "Properties.water_liquid", {"temperature_c": [20, 40], "property": "density_kg_m3"}
    )
    assert result == pytest.approx([998.21, 992.22])


def test_calculate_rejects_bad_arguments():
    with pytest.raises(ValueError, match="unknown argument"):
        registry.calculate("Fluids.dynamic_pressure", {"density": 1.2, "speed": 10})
    with pytest.raises(ValueError, match="missing required"):
        registry.calculate("Fluids.dynamic_pressure", {"density": 1.2})


def test_to_jsonable():
    assert registry.to_jsonable(np.float64(1.5)) == 1.5
    assert registry.to_jsonable((np.array([1.0, 2.0]), 3)) == [[1.0, 2.0], 3]
    assert registry.to_jsonable(math.inf) == "inf"
    assert registry.to_jsonable(Q_(2.0, "m")) == {"magnitude": 2.0, "units": "meter"}


def test_committed_llms_txt_is_up_to_date():
    # llms.txt is generated; regenerate with:  uv run fpc llms-txt > llms.txt
    assert (ROOT / "llms.txt").read_text() == registry.llms_txt()
