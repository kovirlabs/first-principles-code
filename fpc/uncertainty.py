# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""uncertainty.py - how sure is the answer? Monte Carlo on any calculation.

Every input to a real calculation is uncertain: a pipe's roughness is "about
0.045 mm", a measured flow is "12 L/s +/- 3 %", a modulus varies from batch to
batch. A single answer hides that. **Monte Carlo** simulation shows it by brute
force:

    1. describe each uncertain input by a probability distribution;
    2. draw thousands of random input sets;
    3. run the calculation on each one;
    4. look at the spread of the results (mean, standard deviation,
       percentiles) instead of one number.

It needs no calculus and works on any calculation, however non-linear, which
is why engineers reach for it before the textbook error-propagation formulas.

Example::

    from fpc.uncertainty import monte_carlo, Normal, Uniform

    result = monte_carlo(
        "Fluids.pipe_flow",
        {
            "flow": Normal(mean=0.012, std=0.0004),        # 12 L/s, +/- 3 % (1 sigma)
            "diameter": 0.1023,
            "length": 120,
            "roughness": Uniform(low=0.02e-3, high=0.09e-3),
            "density": 998,
            "viscosity": 1.0e-3,
        },
        output="pressure_drop",
        seed=1,
    )
    result.mean, result.std, result.interval(95)   # Pa
    result.sensitivity                             # which input matters most

Techniques shown: NumPy's random ``Generator`` (``np.random.default_rng``)
and why a *seed* makes a random run repeatable; vectorized evaluation with a
fallback to a plain loop; ``np.percentile``; and a correlation-based
sensitivity measure.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from fpc import registry
from fpc.hints import FloatArray

# --- Input distributions --------------------------------------------------
# Each one is a tiny frozen dataclass with a ``sample`` method. Anything with
# that method works as an input (that is what the ``Distribution`` Protocol
# below says), so you can add your own, e.g. a log-normal.


class Distribution(Protocol):
    """Anything that can draw ``n`` random values with a NumPy ``Generator``."""

    def sample(self, rng: np.random.Generator, n: int) -> FloatArray: ...


@dataclass(frozen=True)
class Normal:
    """Bell curve: most values near ``mean``; about 95 % within 2 ``std``.

    Use it for measurements and manufacturing variation. A datasheet's
    "+/- x" is often 2 or 3 standard deviations, so check before using it as ``std``.

    :param mean: centre value [input unit]
    :param std: standard deviation, one sigma [input unit]
    """

    mean: float
    std: float

    def __post_init__(self) -> None:
        if self.std < 0:
            raise ValueError(f"std must be >= 0, got {self.std}")

    def sample(self, rng: np.random.Generator, n: int) -> FloatArray:
        return rng.normal(self.mean, self.std, n)


@dataclass(frozen=True)
class Uniform:
    """Every value between ``low`` and ``high`` equally likely.

    Use it when you only know the bounds (a tolerance band, a "somewhere
    between" estimate).

    :param low: smallest value [input unit]
    :param high: largest value [input unit]
    """

    low: float
    high: float

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(f"high ({self.high}) must be >= low ({self.low})")

    def sample(self, rng: np.random.Generator, n: int) -> FloatArray:
        return rng.uniform(self.low, self.high, n)


@dataclass(frozen=True)
class Triangular:
    """Bounds plus a most-likely value: a good fit for an expert's estimate.

    :param low: smallest value [input unit]
    :param mode: most likely value [input unit]
    :param high: largest value [input unit]
    """

    low: float
    mode: float
    high: float

    def __post_init__(self) -> None:
        if not self.low <= self.mode <= self.high:
            raise ValueError(f"need low <= mode <= high, got {self.low}, {self.mode}, {self.high}")

    def sample(self, rng: np.random.Generator, n: int) -> FloatArray:
        return rng.triangular(self.low, self.mode, self.high, n)


def parse_distribution(text: str) -> float | Distribution:
    """Read an input from text, as typed on the command line.

    ``"998"`` -> 998.0, ``"normal:2,0.1"`` -> ``Normal(2, 0.1)``,
    ``"uniform:0.9,1.1"`` -> ``Uniform``, ``"triangular:1,2,4"`` -> ``Triangular``.

    :param text: a number, or ``kind:numbers``
    :returns: a float or a distribution
    """
    kind, sep, numbers = text.partition(":")
    if not sep:
        return float(text)
    values = [float(v) for v in numbers.split(",")]
    kinds: dict[str, type] = {"normal": Normal, "uniform": Uniform, "triangular": Triangular}
    if kind.lower() not in kinds:
        raise ValueError(f"unknown distribution {kind!r}; use one of {sorted(kinds)}")
    return kinds[kind.lower()](*values)


# --- Results ----------------------------------------------------------------


@dataclass(frozen=True)
class MonteCarloResult:
    """The spread of a calculation's result.

    :param samples: every simulated result [output unit]
    :param inputs: the sampled value of each uncertain input, by name [input unit]
    """

    samples: FloatArray = field(repr=False)
    inputs: dict[str, FloatArray] = field(repr=False)

    @property
    def mean(self) -> float:
        """Average result [output unit]."""
        return float(np.mean(self.samples))

    @property
    def std(self) -> float:
        """Standard deviation of the result [output unit]."""
        return float(np.std(self.samples, ddof=1))

    def percentile(self, q: float) -> float:
        """Value below which ``q`` percent of the results fall [output unit].

        :param q: percentage, 0 to 100 [-]
        """
        return float(np.percentile(self.samples, q))

    def interval(self, coverage: float = 95) -> tuple[float, float]:
        """Range that holds the central ``coverage`` percent of the results.

        ``interval(95)`` is (2.5th percentile, 97.5th percentile). Unlike
        ``mean +/- 2*std`` it stays right when the result is lopsided.

        :param coverage: percentage of results inside the range [-]
        :returns: (low, high) [output unit]
        """
        tail = (100 - coverage) / 2
        return self.percentile(tail), self.percentile(100 - tail)

    @property
    def sensitivity(self) -> dict[str, float]:
        """Share of the result's variation that comes from each uncertain input.

        Computed as the squared correlation between each input's samples and
        the results, scaled to add up to 1. It is a first look, not a full
        variance decomposition: it assumes the inputs are independent and the
        effect is roughly monotonic (more input, more or less output), which
        holds for most engineering formulas. Biggest first.

        :returns: ``{input name: share}`` [-]
        """
        if not self.inputs or np.ptp(self.samples) == 0:
            return {}
        r2 = {
            name: float(np.corrcoef(values, self.samples)[0, 1] ** 2)
            for name, values in self.inputs.items()
        }
        total = sum(r2.values()) or 1.0
        return dict(sorted(((k, v / total) for k, v in r2.items()), key=lambda kv: -kv[1]))

    def summary(self) -> dict[str, Any]:
        """Plain-number summary, ready for JSON, a table, or a report.

        :returns: mean, std, p5, p50, p95 [output unit], samples [-] and sensitivity [-]
        """
        return {
            "mean": self.mean,
            "std": self.std,
            "p5": self.percentile(5),
            "p50": self.percentile(50),
            "p95": self.percentile(95),
            "samples": len(self.samples),
            "sensitivity": self.sensitivity,
        }


# --- The simulation -----------------------------------------------------------


def monte_carlo(
    calculation: str | Callable[..., Any],
    inputs: Mapping[str, Any],
    *,
    samples: int = 10_000,
    seed: int | None = None,
    output: str | int | None = None,
) -> MonteCarloResult:
    """Run a calculation many times with random inputs.

    :param calculation: a registry key such as ``"Fluids.pipe_flow"``, or any
        function that takes keyword arguments
    :param inputs: every argument the calculation needs; uncertain ones as a
        distribution (:class:`Normal`, :class:`Uniform`, :class:`Triangular`),
        fixed ones as plain values [input units]
    :param samples: how many random runs; error in the mean shrinks like
        1/sqrt(samples), so 10 000 is plenty for engineering work [-]
    :param seed: fix the random numbers so the run can be repeated exactly;
        leave as ``None`` for fresh random numbers each time [-]
    :param output: which part of the result to study when the calculation
        returns several values: a dict key (``"pressure_drop"``) or a tuple
        index (``1``) [-]
    :returns: a :class:`MonteCarloResult`
    :raises ValueError: if ``samples < 2`` or the result is not a number
    """
    if samples < 2:
        raise ValueError(f"samples must be at least 2, got {samples}")
    if isinstance(calculation, str):
        calc = registry.get(calculation)
        function = getattr(calc.cls(), calc.name)
    else:
        function = calculation

    # A Generator with a seed gives the same "random" numbers every run, so
    # a result in a report can be reproduced by whoever checks it.
    rng = np.random.default_rng(seed)
    drawn = {
        name: value.sample(rng, samples)
        for name, value in inputs.items()
        if hasattr(value, "sample")
    }
    fixed = {name: value for name, value in inputs.items() if name not in drawn}

    def pick(result: Any) -> Any:
        if output is None:
            return result
        return result[output]  # works for dicts (key) and tuples (index)

    # Fast path: hand the whole arrays over in one call. Formulas written with
    # plain operators (+, *, **) or NumPy functions work on arrays unchanged.
    # Formulas using ``math.sqrt``, ``if x > ...`` or a root finder do not, and
    # raise TypeError/ValueError, so we fall back to one call per sample.
    values: FloatArray | None = None
    try:
        vectorized = np.asarray(pick(function(**fixed, **drawn)), dtype=float)
        if vectorized.shape == (samples,):
            values = vectorized
    except (TypeError, ValueError, KeyError, IndexError):
        values = None
    if values is None:
        values = np.empty(samples)
        for i in range(samples):
            one = {name: float(array[i]) for name, array in drawn.items()}
            result = pick(function(**fixed, **one))
            if isinstance(result, dict | tuple | list):
                options = list(result) if isinstance(result, dict) else list(range(len(result)))
                raise ValueError(
                    f"the calculation returns several values; choose one with output=..., "
                    f"one of {options}"
                )
            values[i] = float(result)
    return MonteCarloResult(samples=values, inputs=drawn)
