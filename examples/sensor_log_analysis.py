# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""sensor_log_analysis.py - from a raw data-logger CSV to a summary report.

QUESTION
    We have two hours of logged data from two pumps (examples/data/
    pump_sensor_log.csv - synthetic). What are the average operating points,
    when did either bearing exceed its 68 degC alarm, and can we hand the
    results to someone who lives in Excel?

APPROACH (the everyday pandas workflow)
    1. Read the CSV; parse the timestamp column as real dates.
    2. Clean: count and drop missing readings.
    3. Group by pump and summarize (mean / max).
    4. Resample to 10-minute averages to see trends without the noise.
    5. Filter with a boolean mask to find alarm events.
    6. Export a CSV and a multi-sheet Excel workbook, and plot the trend.

Run it:  uv run examples/sensor_log_analysis.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from fpc import Utility

HERE = Path(__file__).resolve().parent
LOG_FILE = HERE / "data" / "pump_sensor_log.csv"
OUTPUT_DIR = HERE / "output"
BEARING_ALARM_C = 68.0


def main():
    # --- 1. Read ----------------------------------------------------------
    log = Utility().read_table(file_path=LOG_FILE)
    # CSV has no date type; convert the text column so we can resample by time.
    log["timestamp"] = pd.to_datetime(log["timestamp"])
    print(f"Loaded {len(log)} rows, columns: {list(log.columns)}\n")

    # --- 2. Clean ---------------------------------------------------------
    missing = log.isna().sum()
    print("Missing values per column:")
    print(missing[missing > 0].to_string(), "\n")
    log = log.dropna()

    # --- 3. Group and summarize ------------------------------------------
    summary = (
        log.groupby("pump_id")
        .agg(
            mean_flow_l_s=("flow_l_s", "mean"),
            mean_discharge_kpa=("discharge_kpa", "mean"),
            max_bearing_temp_c=("bearing_temp_c", "max"),
        )
        .round(2)
    )
    print("Per-pump summary:")
    print(summary.to_string(), "\n")

    # --- 4. Resample: 10-minute averages per pump -------------------------
    trend = (
        log.set_index("timestamp")
        .groupby("pump_id")["bearing_temp_c"]
        .resample("10min")
        .mean()
        .unstack(level="pump_id")  # one column per pump
    )

    # --- 5. Boolean mask: alarm events -----------------------------------
    alarms = log[log["bearing_temp_c"] > BEARING_ALARM_C]
    first_alarm = alarms.groupby("pump_id")["timestamp"].min()
    print(f"Readings above {BEARING_ALARM_C} degC: {len(alarms)}")
    for pump_id, when in first_alarm.items():
        print(f"  {pump_id} first alarm at {when:%H:%M:%S}")

    # --- 6. Export and plot ----------------------------------------------
    OUTPUT_DIR.mkdir(exist_ok=True)
    summary.to_csv(OUTPUT_DIR / "pump_summary.csv")
    # ExcelWriter puts several tables in one workbook, one per sheet.
    with pd.ExcelWriter(OUTPUT_DIR / "pump_report.xlsx") as workbook:
        summary.to_excel(workbook, sheet_name="summary")
        trend.to_excel(workbook, sheet_name="bearing_trend_10min")
        alarms.to_excel(workbook, sheet_name="alarms", index=False)

    axis = trend.plot(figsize=(7, 4), marker="o", ylabel="Bearing temperature [degC]")
    axis.axhline(BEARING_ALARM_C, color="red", linestyle="--", label="alarm")
    axis.legend()
    axis.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "bearing_trend.png", dpi=120)
    print(f"\nWrote pump_summary.csv, pump_report.xlsx, bearing_trend.png to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
