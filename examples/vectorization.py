# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""vectorization.py - loops vs NumPy arrays, side by side.

QUESTION
    A shaft has 1,000,000 measured (or simulated) load cases. For each one,
    what is the bending stress, and which cases exceed yield?

LESSON
    Coming from Excel or plain Python, the instinct is to loop over every
    case. NumPy lets you write the formula once and apply it to the whole
    array - "vectorization". It is shorter, closer to the math, and often
    tens of times faster because the loop runs in compiled C, not Python.

    Three ideas to take away:
      1. Vectorized arithmetic:  stress = moment * c / I  works on arrays.
      2. Broadcasting:           a (N,1) column with a (M,) row gives an (N,M)
                                 grid - every combination, no nested loops.
      3. Boolean masking:        stress[stress > yield] picks the failures.

Run it:  uv run examples/vectorization.py
"""

import time

import numpy as np

YIELD_STRENGTH = 250e6              # Pa
DIAMETER = 0.04                     # m, solid round shaft
SECOND_MOMENT = np.pi * DIAMETER**4 / 64
FIBRE_DISTANCE = DIAMETER / 2

rng = np.random.default_rng(seed=0)
moments = rng.normal(loc=1000, scale=300, size=1_000_000)    # N*m, one per case


def with_loop():
    """The plain-Python way: one case at a time."""
    stresses = []
    for moment in moments:
        stresses.append(moment * FIBRE_DISTANCE / SECOND_MOMENT)
    over = 0
    for stress in stresses:
        if stress > YIELD_STRENGTH:
            over += 1
    return over


def vectorized():
    """The NumPy way: the formula, applied to every case at once."""
    stresses = moments * FIBRE_DISTANCE / SECOND_MOMENT
    return int((stresses > YIELD_STRENGTH).sum())   # True counts as 1


def timed(function):
    start = time.perf_counter()
    result = function()
    return result, time.perf_counter() - start


def main():
    loop_count, loop_time = timed(with_loop)
    vec_count, vec_time = timed(vectorized)
    assert loop_count == vec_count               # same answer, different speed
    print(f"Cases above yield: {vec_count} of {len(moments):,}")
    print(f"  Python loop : {loop_time * 1000:8.1f} ms")
    print(f"  NumPy       : {vec_time * 1000:8.1f} ms  ({loop_time / vec_time:.0f}x faster)\n")

    # --- Boolean masking: pull out just the failing cases ----------------
    stresses = moments * FIBRE_DISTANCE / SECOND_MOMENT
    failing = stresses[stresses > YIELD_STRENGTH]
    print(f"Worst stress {failing.max() / 1e6:.0f} MPa; "
          f"mean of the failures {failing.mean() / 1e6:.0f} MPa")

    # --- Broadcasting: a design table over two variables -----------------
    # Column of diameters (shape (5, 1)) against a row of moments (shape (4,)).
    diameters = np.array([0.030, 0.035, 0.040, 0.045, 0.050])[:, np.newaxis]
    design_moments = np.array([500, 1000, 1500, 2000])
    # NumPy stretches both to (5, 4): every diameter x every moment.
    table = design_moments * (diameters / 2) / (np.pi * diameters**4 / 64) / 1e6
    print("\nStress [MPa]  (rows: diameter, columns: moment [N*m])")
    print("   d [mm] " + "".join(f"{m:>8}" for m in design_moments))
    for d, row in zip(diameters.ravel(), table):
        # Mark cells above yield with '*'.
        cells = "".join(f"{s:7.0f}{'*' if s > YIELD_STRENGTH / 1e6 else ' '}" for s in row)
        print(f"   {d * 1000:6.0f} {cells}")
    print("   (* = above yield)")


if __name__ == "__main__":
    main()
