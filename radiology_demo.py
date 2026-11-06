# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""radiology_demo.py - a worked tour of the medical-imaging classes.

Run it with:  uv run radiology_demo.py

It walks through one calculation per modality, then loads a real (sample,
anonymous) CT slice with pydicom, converts it to Hounsfield units, and shows
it in three different windows - the same slice, three very different images.
The figure is saved to radiology.png.
"""

import matplotlib.pyplot as plt
import numpy as np
from pydicom.data import get_testdata_file

from library import CT, MRI, Dicom, Radiation, Radiography, Ultrasound


def radiation_protection():
    """Distance and shielding: the two cheapest ways to cut dose."""
    radiation = Radiation()
    print("Radiation protection")
    print("-" * 48)
    # A loop over distances shows the inverse square law in action.
    for distance_m in (1, 2, 3, 4):
        rate = radiation.inverse_square_law(
            initial_intensity=100.0, initial_distance=1.0, new_distance=distance_m,
        )
        print(f"  {distance_m} m from source : {rate:6.2f} uGy/h")

    # Lead at ~100 keV: mu/rho ~5.55 cm^2/g (NIST XCOM), rho = 11.35 g/cm^3.
    mu_lead = radiation.linear_attenuation_coefficient(
        mass_attenuation_coefficient=5.55, density=11.35,
    )
    hvl_mm = radiation.half_value_layer(attenuation_coefficient=mu_lead) * 10
    print(f"  HVL of lead at 100 keV    : {hvl_mm:.2f} mm\n")


def radiography_technique():
    """Adjust a technique chart for a new SID and a grid."""
    radiography = Radiography()
    mas = radiography.mas(tube_current_ma=200, exposure_time_s=0.05)
    new_mas = radiography.exposure_maintenance_mas(original_mas=mas, original_sid=100,
                                                   new_sid=180)
    gridded = radiography.grid_mas(original_mas=new_mas, original_grid="none", new_grid="12:1")
    print("Radiography technique")
    print("-" * 48)
    print(f"  10 mAs at 100 cm -> {new_mas:.1f} mAs at 180 cm -> {gridded:.0f} mAs with 12:1 grid\n")


def mri_contrast():
    """Why fat is bright on T1 and CSF is bright on T2."""
    mri = MRI()
    # Each sequence is a dict of keyword arguments - unpacked with ** below.
    sequences = {
        "T1 (TR 500/TE 15)": {"repetition_time_ms": 500, "echo_time_ms": 15},
        "T2 (TR 4000/TE 100)": {"repetition_time_ms": 4000, "echo_time_ms": 100},
    }
    print("MRI spin-echo signal (relative)")
    print("-" * 48)
    for name, timing in sequences.items():
        signals = {tissue: mri.spin_echo_signal(**timing, tissue=tissue)
                   for tissue in ("fat", "white_matter", "csf")}
        brightest = max(signals, key=lambda tissue: signals[tissue])
        row = "  ".join(f"{t}={s:.2f}" for t, s in signals.items())
        print(f"  {name:20s} {row}  -> brightest: {brightest}")
    print()


def ultrasound_doppler():
    """Doppler velocity, and why the insonation angle matters."""
    ultrasound = Ultrasound()
    print("Ultrasound Doppler (5 MHz, true flow 0.5 m/s, shift measured at 60 deg)")
    print("-" * 48)
    shift = ultrasound.doppler_shift(transmitted_frequency_mhz=5, velocity=0.5, angle_deg=60)
    # If the operator mis-sets the angle cursor, the velocity estimate is wrong.
    for assumed_angle in (50, 60, 70):
        v = ultrasound.doppler_velocity(transmitted_frequency_mhz=5, doppler_shift_hz=shift,
                                        angle_deg=assumed_angle)
        print(f"  angle cursor at {assumed_angle} deg -> {v:.2f} m/s")
    print()


def ct_windowing():
    """Load a sample CT slice and display it in three windows."""
    dicom, ct = Dicom(), CT()
    dataset = dicom.read(path=get_testdata_file("CT_small.dcm"))
    hu = dicom.pixel_array_in_units(dataset=dataset)

    print("CT slice (pydicom sample - no patient data)")
    print("-" * 48)
    for key, value in dicom.summary(dataset=dataset).items():
        if value is not None:
            print(f"  {key:18s}: {value}")
    print(f"  HU range          : {hu.min():.0f} to {hu.max():.0f}")
    print(f"  centre pixel      : {hu[64, 64]:.0f} HU "
          f"({ct.classify_hounsfield(hounsfield=hu[64, 64])})")

    presets = ["abdomen", "lung", "bone"]
    figure, axes = plt.subplots(1, len(presets) + 1, figsize=(14, 4))

    # Panel 1: narrow-beam attenuation curves for a few materials.
    thickness_cm = np.linspace(0, 10, 200)
    for label, mu in {"soft tissue (0.18/cm)": 0.18, "bone (0.48/cm)": 0.48}.items():
        axes[0].plot(thickness_cm, np.exp(-mu * thickness_cm) * 100, label=label)
    axes[0].set(title="Attenuation at ~60 keV", xlabel="thickness [cm]",
                ylabel="transmitted [%]")
    axes[0].legend()

    # Panels 2-4: the same HU data through different windows.
    for axis, preset in zip(axes[1:], presets):
        width, level = CT.WINDOW_PRESETS[preset]
        axis.imshow(ct.apply_window(hounsfield=hu, preset=preset), cmap="gray",
                    vmin=0, vmax=255)
        axis.set_title(f"{preset} window (W{width} / L{level})")
        axis.axis("off")

    figure.tight_layout()
    figure.savefig("radiology.png", dpi=120)
    print("\n  Saved figure -> radiology.png")


if __name__ == "__main__":
    radiation_protection()
    radiography_technique()
    mri_contrast()
    ultrasound_doppler()
    ct_windowing()
