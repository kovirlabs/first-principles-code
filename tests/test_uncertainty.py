# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for Monte Carlo uncertainty (fpc.uncertainty).

Every test fixes ``seed`` so its random numbers, and so its result, are the
same on every run. Tolerances are set from the theory: the error in a
Monte Carlo mean is about std/sqrt(samples).
"""

import math

import pytest

from fpc.uncertainty import Normal, Triangular, Uniform, monte_carlo, parse_distribution


def test_sum_of_normals_matches_theory():
    # For y = a + b with independent normal inputs, the theory says
    # mean = mean_a + mean_b and std = sqrt(std_a^2 + std_b^2).
    result = monte_carlo(
        lambda *, a, b: a + b,
        {"a": Normal(mean=10, std=3), "b": Normal(mean=5, std=4)},
        samples=50_000,
        seed=1,
    )
    assert result.mean == pytest.approx(15, abs=0.1)
    assert result.std == pytest.approx(5, rel=0.02)
    low, high = result.interval(95)
    assert low == pytest.approx(15 - 1.96 * 5, abs=0.25)
    assert high == pytest.approx(15 + 1.96 * 5, abs=0.25)
    # b has the bigger spread: 16 of the 25 units of variance.
    assert list(result.sensitivity) == ["b", "a"]
    assert result.sensitivity["b"] == pytest.approx(16 / 25, abs=0.02)


def test_registry_key_with_fixed_and_uncertain_inputs():
    # Re = rho*v*L/mu is linear in v, so std(Re) = rho*L/mu * std(v).
    result = monte_carlo(
        "Fluids.reynolds_number",
        {"density": 998, "velocity": Normal(mean=2, std=0.1), "length": 0.05, "viscosity": 1e-3},
        seed=2,
    )
    assert result.mean == pytest.approx(99_800, rel=0.005)
    assert result.std == pytest.approx(998 * 0.05 / 1e-3 * 0.1, rel=0.03)
    assert list(result.sensitivity) == ["velocity"]


def test_non_vectorizable_calculation_falls_back_to_a_loop_and_picks_an_output():
    # pipe_flow solves Colebrook with a root finder, which cannot take arrays.
    result = monte_carlo(
        "Fluids.pipe_flow",
        {
            "flow": Normal(mean=0.012, std=0.0004),
            "diameter": 0.1023,
            "length": 120,
            "roughness": Uniform(low=0.02e-3, high=0.09e-3),
            "density": 998,
            "viscosity": 1.0e-3,
        },
        output="pressure_drop",
        samples=1_000,
        seed=3,
    )
    assert len(result.samples) == 1_000
    assert result.interval(95)[0] < result.mean < result.interval(95)[1]
    assert set(result.sensitivity) == {"flow", "roughness"}
    assert sum(result.sensitivity.values()) == pytest.approx(1)


def test_tuple_result_needs_an_index():
    inputs = {"stiffness": Normal(mean=4000, std=200), "mass": 2.5}
    with pytest.raises(ValueError, match="output="):
        monte_carlo("Modal.natural_frequency", inputs, samples=10, seed=0)
    hz = monte_carlo("Modal.natural_frequency", inputs, output=1, seed=0)
    assert hz.mean == pytest.approx(math.sqrt(4000 / 2.5) / (2 * math.pi), rel=0.01)


def test_seed_makes_runs_repeatable():
    inputs = {"a": Uniform(low=0, high=1)}
    first = monte_carlo(lambda *, a: a, inputs, samples=100, seed=7)
    again = monte_carlo(lambda *, a: a, inputs, samples=100, seed=7)
    assert (first.samples == again.samples).all()


def test_summary_is_plain_numbers():
    result = monte_carlo(lambda *, a: 2 * a, {"a": Triangular(low=0, mode=1, high=2)}, seed=0)
    summary = result.summary()
    assert set(summary) == {"mean", "std", "p5", "p50", "p95", "samples", "sensitivity"}
    assert summary["p50"] == pytest.approx(2, abs=0.05)


def test_parse_distribution_and_bad_inputs():
    assert parse_distribution("998") == 998.0
    assert parse_distribution("normal:2,0.1") == Normal(2, 0.1)
    assert parse_distribution("Uniform:1,3") == Uniform(1, 3)
    assert parse_distribution("triangular:1,2,4") == Triangular(1, 2, 4)
    with pytest.raises(ValueError, match="unknown distribution"):
        parse_distribution("lognormal:1,2")
    with pytest.raises(ValueError):
        Normal(mean=1, std=-1)
    with pytest.raises(ValueError):
        Uniform(low=2, high=1)
    with pytest.raises(ValueError):
        monte_carlo(lambda *, a: a, {"a": 1.0}, samples=1)
