# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Generate the SYNTHETIC pump sensor log used by sensor_log_analysis.py.

The numbers are made up (seeded, so they are reproducible) to look like a
real data-logger export: two pumps, one reading every 10 s for two hours,
with noise, a few dropped readings, and one pump that runs hot.

Run from the repo root:  uv run examples/data/make_pump_sensor_log.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(seed=42)
timestamps = pd.date_range("2026-11-06 08:00", periods=720, freq="10s")

frames = []
for pump_id, base_temp in (("P-101", 55.0), ("P-102", 63.0)):
    n = len(timestamps)
    frames.append(pd.DataFrame({
        "timestamp": timestamps,
        "pump_id": pump_id,
        "flow_l_s": 12 + rng.normal(0, 0.4, n),
        "discharge_kpa": 180 + rng.normal(0, 5, n),
        # A slow upward drift + noise on the bearing temperature.
        "bearing_temp_c": base_temp + np.linspace(0, 8, n) + rng.normal(0, 1.0, n),
    }))
log = pd.concat(frames, ignore_index=True)

# Real loggers drop readings: blank out ~1% of the flow values.
log.loc[rng.random(len(log)) < 0.01, "flow_l_s"] = np.nan

out = Path(__file__).resolve().parent / "pump_sensor_log.csv"
log.round({"flow_l_s": 3, "discharge_kpa": 3, "bearing_temp_c": 3}).to_csv(out, index=False)
print(f"Wrote {len(log)} rows -> {out}")
