# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""Tests for the radiology / medical-imaging classes.

Each expected value is a textbook answer a radiology student could check by
hand, so these tests double as worked examples.
"""

import math

import numpy as np
import pytest
from pydicom.data import get_testdata_file

from library import CT, MRI, Dicom, Radiation, Radiography, Ultrasound

radiation = Radiation()
radiography = Radiography()
ct = CT()
mri = MRI()
ultrasound = Ultrasound()
dicom = Dicom()


# --- Radiation ---------------------------------------------------------------

def test_inverse_square_doubling_distance_quarters_intensity():
    assert radiation.inverse_square_law(
        initial_intensity=100.0, initial_distance=1.0, new_distance=2.0,
    ) == pytest.approx(25.0)


def test_one_hvl_halves_the_beam():
    mu = 0.2  # 1/cm
    hvl = radiation.half_value_layer(attenuation_coefficient=mu)
    assert hvl == pytest.approx(math.log(2) / mu)
    assert radiation.transmitted_intensity(
        initial_intensity=1.0, attenuation_coefficient=mu, thickness=hvl,
    ) == pytest.approx(0.5)


def test_tvl_is_about_3_32_hvls():
    tvl = radiation.tenth_value_layer(attenuation_coefficient=1.0)
    hvl = radiation.half_value_layer(attenuation_coefficient=1.0)
    assert tvl / hvl == pytest.approx(3.3219, rel=1e-4)


def test_shielding_thickness_inverts_attenuation():
    x = radiation.shielding_thickness(attenuation_coefficient=0.5, transmission=0.01)
    assert radiation.transmitted_intensity(
        initial_intensity=1.0, attenuation_coefficient=0.5, thickness=x,
    ) == pytest.approx(0.01)


def test_duane_hunt_minimum_wavelength_at_100_kvp():
    assert radiation.photon_wavelength(energy_kev=100) == pytest.approx(0.0124, rel=1e-3)


def test_tc99m_after_two_half_lives():
    """Tc-99m (6.01 h): after 12.02 h a quarter of the activity remains."""
    assert radiation.remaining_activity(
        initial_activity=800.0, half_life=6.01, elapsed_time=12.02,
    ) == pytest.approx(200.0)


def test_effective_half_life_is_shorter_than_both():
    te = radiation.effective_half_life(physical_half_life=6.0, biological_half_life=24.0)
    assert te == pytest.approx(4.8)


@pytest.mark.parametrize("radiation_type, expected_sv", [
    ("photon", 2.0), ("electron", 2.0), ("proton", 4.0), ("alpha", 40.0),
])
def test_equivalent_dose(radiation_type, expected_sv):
    assert radiation.equivalent_dose(
        absorbed_dose=2.0, radiation_type=radiation_type,
    ) == pytest.approx(expected_sv)


def test_unknown_radiation_type_raises():
    with pytest.raises(ValueError):
        radiation.equivalent_dose(absorbed_dose=1.0, radiation_type="gamma-ish")


def test_neutron_weighting_peaks_near_20_at_1_mev():
    assert radiation.neutron_weighting_factor(energy_mev=1.0) == pytest.approx(20.7, abs=0.1)


def test_tissue_weighting_factors_sum_to_one():
    assert sum(Radiation.TISSUE_WEIGHTING_FACTORS.values()) == pytest.approx(1.0)


def test_uniform_whole_body_dose_equals_effective_dose():
    """If every organ gets 1 mSv, effective dose must also be 1 mSv."""
    uniform = {organ: 1.0 for organ in Radiation.TISSUE_WEIGHTING_FACTORS}
    assert radiation.effective_dose(organ_equivalent_doses=uniform) == pytest.approx(1.0)


def test_partial_body_effective_dose():
    assert radiation.effective_dose(
        organ_equivalent_doses={"thyroid": 10.0},
    ) == pytest.approx(0.4)


# --- Radiography -------------------------------------------------------------

def test_mas_reciprocity():
    assert radiography.mas(tube_current_ma=200, exposure_time_s=0.1) == pytest.approx(
        radiography.mas(tube_current_ma=400, exposure_time_s=0.05)
    )


def test_fifteen_percent_rule_round_trip():
    kvp, mas = radiography.fifteen_percent_rule(kvp=70, mas=20, steps=1)
    assert (kvp, mas) == (pytest.approx(80.5), pytest.approx(10.0))
    back = radiography.fifteen_percent_rule(kvp=kvp, mas=mas, steps=-1)
    assert back == (pytest.approx(70), pytest.approx(20))


def test_exposure_maintenance_100_to_180_cm():
    assert radiography.exposure_maintenance_mas(
        original_mas=10, original_sid=100, new_sid=180,
    ) == pytest.approx(32.4)


def test_grid_mas_adding_12_to_1_grid():
    assert radiography.grid_mas(original_mas=5, original_grid="none", new_grid="12:1") == 25


def test_heat_units_high_frequency():
    assert radiography.heat_units(
        kvp=80, tube_current_ma=200, exposure_time_s=0.1, generator="high_frequency",
    ) == pytest.approx(2320.0)


def test_magnification_and_true_size():
    assert radiography.magnification_factor(sid=100, sod=80) == pytest.approx(1.25)
    assert radiography.object_size(image_size=50, sid=100, sod=80) == pytest.approx(40)


def test_geometric_unsharpness():
    assert radiography.geometric_unsharpness(
        focal_spot_size=1.0, sid=100, oid=20,
    ) == pytest.approx(0.25)


def test_nyquist_limit_for_100_um_detector():
    assert radiography.nyquist_limit(pixel_pitch_mm=0.1) == pytest.approx(5.0)


def test_deviation_index_doubling_is_plus_three():
    assert radiography.exposure_index_deviation(
        exposure_index=800, target_exposure_index=400,
    ) == pytest.approx(3.01, abs=0.01)


# --- CT ----------------------------------------------------------------------

def test_hounsfield_reference_points():
    hu = ct.hounsfield_units(attenuation_coefficient=[0.0, 0.19, 0.38], water_attenuation=0.19)
    np.testing.assert_allclose(hu, [-1000.0, 0.0, 1000.0])


def test_rescale_to_hounsfield():
    np.testing.assert_allclose(ct.rescale_to_hounsfield(stored_values=[0, 1024]), [-1024, 0])


def test_window_bounds_preset():
    assert ct.window_bounds(preset="brain") == (0.0, 80.0)
    assert ct.window_bounds(preset="lung") == (-1350.0, 150.0)


def test_apply_window_maps_ends_to_black_and_white():
    grey = ct.apply_window(hounsfield=[-500, 0, 40, 80, 1000], preset="brain")
    assert grey.dtype == np.uint8
    assert list(grey) == [0, 0, 128, 255, 255]


def test_window_requires_width_and_level():
    with pytest.raises(ValueError):
        ct.window_bounds(window_width=400)


@pytest.mark.parametrize("hu, label", [
    (-1000, "air"), (-700, "lung / aerated tissue"), (-100, "fat"),
    (0, "water / simple fluid"), (45, "soft tissue / blood"),
    (1000, "bone / calcification / metal"),
])
def test_classify_hounsfield(hu, label):
    assert ct.classify_hounsfield(hounsfield=hu) == label


def test_head_ct_effective_dose():
    dlp = ct.dose_length_product(ctdi_vol_mgy=60, scan_length_cm=16)
    assert dlp == pytest.approx(960)
    assert ct.effective_dose_from_dlp(dlp_mgy_cm=dlp, region="head") == pytest.approx(2.016)


# --- MRI ---------------------------------------------------------------------

def test_larmor_frequency_at_1_5_t():
    assert mri.larmor_frequency(field_strength_t=1.5) == pytest.approx(63.87, abs=0.01)


def test_relaxation_after_one_time_constant():
    assert mri.t1_recovery(time_ms=500, t1_ms=500) == pytest.approx(1 - math.exp(-1))
    assert mri.t2_decay(time_ms=80, t2_ms=80) == pytest.approx(math.exp(-1))


def test_fat_brighter_than_csf_on_t1():
    tr, te = 500, 15
    fat = mri.spin_echo_signal(repetition_time_ms=tr, echo_time_ms=te, tissue="fat")
    csf = mri.spin_echo_signal(repetition_time_ms=tr, echo_time_ms=te, tissue="csf")
    assert fat > csf


def test_csf_brighter_than_white_matter_on_t2():
    tr, te = 4000, 100
    csf = mri.spin_echo_signal(repetition_time_ms=tr, echo_time_ms=te, tissue="csf")
    wm = mri.spin_echo_signal(repetition_time_ms=tr, echo_time_ms=te, tissue="white_matter")
    assert csf > wm


@pytest.mark.parametrize("tr, te, weighting", [
    (500, 15, "T1-weighted"), (4000, 100, "T2-weighted"),
    (3000, 15, "PD-weighted"), (1500, 50, "mixed"),
])
def test_sequence_weighting(tr, te, weighting):
    assert mri.sequence_weighting(repetition_time_ms=tr, echo_time_ms=te) == weighting


# --- Ultrasound --------------------------------------------------------------

def test_wavelength_5_mhz_soft_tissue():
    assert ultrasound.wavelength(frequency_mhz=5) == pytest.approx(0.308)


def test_13_microseconds_per_cm_rule():
    assert ultrasound.echo_depth(round_trip_time_us=13) == pytest.approx(1.0, rel=0.01)


def test_tissue_air_reflects_almost_everything():
    assert ultrasound.reflection_between(medium_1="soft_tissue", medium_2="air") > 0.99
    assert ultrasound.reflection_between(medium_1="soft_tissue", medium_2="fat") < 0.01


def test_attenuation_round_trip():
    # 3 MHz, 10 cm deep -> 20 cm path -> 30 dB
    assert ultrasound.attenuation_db(frequency_mhz=3, path_length_cm=20) == pytest.approx(30)


def test_maximum_depth_for_prf():
    assert ultrasound.maximum_depth(pulse_repetition_frequency_hz=5000) == pytest.approx(15.4)


def test_doppler_shift_and_inverse_agree():
    shift = ultrasound.doppler_shift(transmitted_frequency_mhz=5, velocity=0.5, angle_deg=60)
    assert shift == pytest.approx(1623.4, rel=1e-3)
    velocity = ultrasound.doppler_velocity(
        transmitted_frequency_mhz=5, doppler_shift_hz=shift, angle_deg=60,
    )
    assert velocity == pytest.approx(0.5)


def test_doppler_at_90_degrees_raises():
    with pytest.raises(ValueError):
        ultrasound.doppler_velocity(transmitted_frequency_mhz=5, doppler_shift_hz=100,
                                    angle_deg=90)


# --- DICOM (uses pydicom's bundled sample CT - no patient data) --------------

@pytest.fixture
def ct_dataset():
    return dicom.read(path=get_testdata_file("CT_small.dcm"))


def test_dicom_summary_has_modality(ct_dataset):
    summary = dicom.summary(dataset=ct_dataset)
    assert summary["Modality"] == "CT"
    assert "PatientName" not in summary


def test_dicom_pixels_are_converted_to_hu(ct_dataset):
    raw = ct_dataset.pixel_array.astype(float)
    hu = dicom.pixel_array_in_units(dataset=ct_dataset)
    np.testing.assert_allclose(hu, raw * float(ct_dataset.RescaleSlope)
                               + float(ct_dataset.RescaleIntercept))


def test_dicom_anonymize_copies_and_strips_phi(ct_dataset, tmp_path):
    original_name = str(ct_dataset.PatientName)
    clean = dicom.anonymize(dataset=ct_dataset)
    assert str(clean.PatientName) == "ANONYMIZED"
    assert str(ct_dataset.PatientName) == original_name  # original untouched

    out = tmp_path / "anon.dcm"
    dicom.save(dataset=clean, path=out)
    assert str(dicom.read(path=out).PatientName) == "ANONYMIZED"


def test_windowed_slice_exports_to_png(ct_dataset, tmp_path):
    hu = dicom.pixel_array_in_units(dataset=ct_dataset)
    image = ct.apply_window(hounsfield=hu, preset="abdomen")
    out = tmp_path / "slice.png"
    dicom.to_png(image=image, path=out)
    assert out.stat().st_size > 0
