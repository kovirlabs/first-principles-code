# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""pid_tuning.py - tune a PI controller by brute-force search.

QUESTION
    A heater behaves like a first-order plant (time constant 4 s, gain 2).
    Which PI gains reach the setpoint fastest with no more than 5% overshoot?

APPROACH
    1. Simulate the closed loop for every (kp, ki) pair on a grid - computers
       are cheap, so try them all.
    2. Measure each response with NumPy: overshoot and 2% settling time.
    3. Keep the candidates that meet the overshoot limit; pick the fastest.
    4. Plot the best response against a too-aggressive one.

This "simulate many, score, pick" loop is the same pattern behind design
studies and optimization, just with an exhaustive search instead of a solver.

Run it:  uv run examples/pid_tuning.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from fpc import Controls

controls = Controls()

PLANT = {"time_constant": 4.0, "gain": 2.0}
SETPOINT = 1.0
MAX_OVERSHOOT = 0.05
DURATION = 20.0


def score(*, time, output):
    """Return (overshoot fraction, 2% settling time [s]) for a step response."""
    overshoot = max(output.max() - SETPOINT, 0.0) / SETPOINT
    # Boolean mask: True wherever the output is OUTSIDE the 2% band.
    outside = np.abs(output - SETPOINT) > 0.02 * SETPOINT
    if outside[-1]:
        return overshoot, np.inf            # never settled within the run
    # Settling time = just after the last moment the output was outside.
    last_outside = np.nonzero(outside)[0].max()
    return overshoot, time[last_outside + 1]


def main():
    kp_grid = np.linspace(0.5, 6.0, 12)
    ki_grid = np.linspace(0.1, 3.0, 12)
    results = []
    for kp in kp_grid:
        for ki in ki_grid:
            time, output = controls.simulate_pid_first_order(
                setpoint=SETPOINT, kp=kp, ki=ki, duration=DURATION, **PLANT,
            )
            overshoot, settling = score(time=time, output=output)
            results.append({"kp": kp, "ki": ki, "overshoot": overshoot, "settling": settling})

    # A list comprehension with a condition filters the candidates.
    acceptable = [r for r in results if r["overshoot"] <= MAX_OVERSHOOT]
    best = min(acceptable, key=lambda r: r["settling"])
    worst = max(results, key=lambda r: r["overshoot"])

    print(f"Tried {len(results)} gain pairs; {len(acceptable)} meet "
          f"<= {MAX_OVERSHOOT:.0%} overshoot.")
    print(f"Best:  kp = {best['kp']:.2f}, ki = {best['ki']:.2f} -> "
          f"settles in {best['settling']:.2f} s, overshoot {best['overshoot']:.1%}")
    # A best result on the edge of the search grid means the true optimum may
    # lie outside it. (Here: more kp is always faster for a first-order plant,
    # until actuator limits - which this simple model leaves out - bite.)
    if best["kp"] in (kp_grid[0], kp_grid[-1]) or best["ki"] in (ki_grid[0], ki_grid[-1]):
        print("  Note: best gains are on the edge of the grid - widen it, or add "
              "the actuator limit that really caps kp.")
    print(f"Most aggressive: kp = {worst['kp']:.2f}, ki = {worst['ki']:.2f} -> "
          f"overshoot {worst['overshoot']:.1%}")

    figure, axis = plt.subplots(figsize=(7, 4))
    for label, gains in (("best", best), ("most overshoot", worst)):
        time, output = controls.simulate_pid_first_order(
            setpoint=SETPOINT, kp=gains["kp"], ki=gains["ki"], duration=DURATION, **PLANT,
        )
        axis.plot(time, output, label=f"{label}: kp={gains['kp']:.1f}, ki={gains['ki']:.1f}")
    axis.axhline(SETPOINT * (1 + MAX_OVERSHOOT), color="gray", linestyle=":",
                 label="overshoot limit")
    axis.set_xlabel("Time [s]")
    axis.set_ylabel("Output")
    axis.grid(True, alpha=0.3)
    axis.legend()
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(exist_ok=True)
    figure.savefig(output_dir / "pid_tuning.png", dpi=120)
    print(f"Saved plot -> {output_dir / 'pid_tuning.png'}")


if __name__ == "__main__":
    main()
