# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Generate the GitHub social-preview card (.github/social-preview.png).

Renders a 1280x640 PNG (GitHub's required size for the Open Graph image used on
the repo card, link unfurls, etc.). Re-run with:

    uv run python .github/make_social_preview.py

then upload the resulting ``social-preview.png`` under
GitHub -> Settings -> General -> Social preview.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# --- Palette (kept in one place so it is easy to retheme) -----------------
BG = "#0d1b2a"  # deep navy background
PANEL = "#152538"  # slightly lighter panel for the plot
CYAN = "#4cc9f0"  # primary accent
MAGENTA = "#f72585"  # secondary accent
TEXT = "#e6edf3"  # near-white body text
SUBTLE = "#8b97a7"  # muted captions

# 16in x 8in at 80 dpi -> 1280 x 640 px, exactly what GitHub wants.
fig = plt.figure(figsize=(16, 8), dpi=80)
fig.patch.set_facecolor(BG)

# One full-bleed axis we use as a layout canvas. Coordinates are 0..1.
canvas = fig.add_axes((0, 0, 1, 1))
canvas.set_xlim(0, 1)
canvas.set_ylim(0, 1)
canvas.set_facecolor(BG)
canvas.set_axis_off()

# Accent bar above the title - a small visual anchor.
canvas.add_patch(plt.Rectangle((0.04, 0.905), 0.075, 0.012, color=CYAN, lw=0))

# Title block: project name, one-line value prop, two-line description.
canvas.text(0.04, 0.74, "First Principles Code", fontsize=46, color=TEXT, weight="bold")
canvas.text(
    0.04, 0.65, "Open-source Python for engineers", fontsize=22, color=CYAN, weight="semibold"
)
canvas.text(
    0.04,
    0.51,
    "A teaching template that replaces MATLAB & Maplesoft\n"
    "with NumPy, SciPy, matplotlib, and Pint.",
    fontsize=18,
    color=SUBTLE,
    linespacing=1.4,
)

# Feature ribbon and repo URL near the bottom.
canvas.text(
    0.04,
    0.18,
    "dynamics  ·  statics  ·  vibration  ·  controls"
    "  ·  Pint units  ·  solve_ivp  ·  curve_fit  ·  pytest",
    fontsize=14,
    color=SUBTLE,
)
canvas.text(
    0.04,
    0.10,
    "github.com/evangress/first-principles-code",
    fontsize=14,
    color=CYAN,
    weight="medium",
)

# --- Inset plot: damped free-vibration "simulate -> fit" hero --------------
plot = fig.add_axes((0.60, 0.22, 0.36, 0.58))
plot.set_facecolor(PANEL)

# Same underdamped SDOF parameters as the project's Modal example.
time = np.linspace(0.0, 5.0, 400)
mass, stiffness, damping = 2.0, 800.0, 8.0
omega_n = np.sqrt(stiffness / mass)
zeta = damping / (2 * np.sqrt(stiffness * mass))
omega_d = omega_n * np.sqrt(1 - zeta**2)
displacement_mm = 10.0 * np.exp(-zeta * omega_n * time) * np.cos(omega_d * time)

plot.plot(time, displacement_mm, color=CYAN, lw=2.5, label="simulate")
plot.plot(
    time, displacement_mm, color=MAGENTA, lw=1.4, ls="--", alpha=0.85, label="fit recovers params"
)

plot.set_title("simulate → fit", color=TEXT, loc="left", fontsize=14, pad=10)
plot.set_xlabel("time [s]", color=SUBTLE, fontsize=12)
plot.set_ylabel("displacement [mm]", color=SUBTLE, fontsize=12)
plot.tick_params(colors=SUBTLE)
for spine in plot.spines.values():
    spine.set_color(SUBTLE)
plot.grid(True, color="#2a3a52", alpha=0.5)
plot.legend(loc="upper right", facecolor=PANEL, edgecolor=SUBTLE, labelcolor=TEXT, fontsize=11)

# --- Save -------------------------------------------------------------------
output_path = Path(__file__).resolve().parent / "social-preview.png"
fig.savefig(output_path, dpi=80, facecolor=BG, pad_inches=0)
print(f"wrote {output_path}")
