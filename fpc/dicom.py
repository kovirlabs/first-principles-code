# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""dicom.py - reading and handling DICOM medical images with pydicom.

DICOM is the file format (and network protocol) used by every CT, MR, x-ray,
and ultrasound system. A DICOM file holds two things:

* a header of tagged metadata - modality, pixel spacing, rescale values, and
  patient identifiers (Protected Health Information, PHI);
* the pixel data, which pydicom hands back as a NumPy array.

This class wraps the handful of pydicom calls a student needs: load a file,
get the image in real units (HU for CT), summarize the header, and strip PHI
before sharing an image. pydicom ships sample files, so you can practise
without any patient data::

    from pydicom.data import get_testdata_file
    path = get_testdata_file("CT_small.dcm")
"""

import copy
import os
from typing import Any

import numpy as np
import pydicom

from fpc.hints import ArrayLike, FloatArray

# A file location may be a plain string or any path-like object such as
# ``pathlib.Path``; ``os.PathLike[str]`` is the type that covers the latter.
# A plain assignment (not a ``type`` statement) keeps the alias transparent
# to ``typing.get_type_hints``.
FilePath = str | os.PathLike[str]


class Dicom:
    """Load, inspect, convert, and de-identify DICOM images."""

    # Header keywords copied into :meth:`summary`. Only technical fields - no
    # patient identifiers - so the summary is safe to print or log.
    SUMMARY_KEYWORDS = (
        "Modality",
        "BodyPartExamined",
        "Manufacturer",
        "Rows",
        "Columns",
        "PixelSpacing",
        "SliceThickness",
        "KVP",
        "XRayTubeCurrent",
        "ExposureTime",
        "RescaleSlope",
        "RescaleIntercept",
        "WindowCenter",
        "WindowWidth",
    )

    # Direct identifiers to blank when de-identifying. This is a teaching
    # subset: full de-identification follows DICOM PS3.15 Annex E and also
    # needs dates, UIDs, private tags, and text burned into the pixels handled.
    PHI_KEYWORDS = (
        "PatientName",
        "PatientID",
        "PatientBirthDate",
        "PatientAddress",
        "PatientTelephoneNumbers",
        "OtherPatientIDs",
        "ReferringPhysicianName",
        "InstitutionName",
        "InstitutionAddress",
        "AccessionNumber",
    )

    def read(self, *, path: FilePath) -> pydicom.Dataset:
        """Read a DICOM file from disk.

        :param path: file path (str or pathlib.Path)
        :returns: a ``pydicom.Dataset`` - access tags as attributes,
            e.g. ``ds.Modality``, and pixels as ``ds.pixel_array``
        """
        return pydicom.dcmread(path)

    def summary(self, *, dataset: pydicom.Dataset) -> dict[str, Any]:
        """Collect the key technical header fields into a plain dict.

        Uses ``dataset.get(keyword)`` rather than ``dataset.keyword`` so a
        missing tag returns None instead of raising - many tags are optional
        and vary by modality.

        :param dataset: a pydicom Dataset
        :returns: dict {keyword: value or None}
        """
        # A dict comprehension: build the whole dictionary in one expression.
        return {keyword: dataset.get(keyword) for keyword in self.SUMMARY_KEYWORDS}

    def pixel_array_in_units(self, *, dataset: pydicom.Dataset) -> FloatArray:
        """Pixel data converted to real-world values (HU for CT).

        Applies  value * RescaleSlope + RescaleIntercept. If the tags are
        absent (common for plain radiographs) the stored values are returned
        unchanged as floats.

        :param dataset: a pydicom Dataset containing pixel data
        :returns: float numpy array [HU for CT, else stored units]
        """
        slope = float(dataset.get("RescaleSlope", 1.0))
        intercept = float(dataset.get("RescaleIntercept", 0.0))
        return dataset.pixel_array.astype(float) * slope + intercept

    def pixel_spacing_mm(self, *, dataset: pydicom.Dataset) -> tuple[float, float] | None:
        """Physical size of one pixel as (row spacing, column spacing) in mm.

        Needed for any real measurement: a length in pixels times the spacing
        gives millimetres.

        :param dataset: a pydicom Dataset
        :returns: tuple (row_mm, col_mm), or None if the tag is missing [mm]
        """
        spacing = dataset.get("PixelSpacing")
        if spacing is None:
            return None
        return float(spacing[0]), float(spacing[1])

    def anonymize(
        self, *, dataset: pydicom.Dataset, replacement: str = "ANONYMIZED"
    ) -> pydicom.Dataset:
        """Blank the direct patient identifiers and drop private tags.

        Works on a DEEP copy so the original dataset is left untouched -
        mutating a caller's object behind their back is a common source of
        bugs. (``dataset.copy()`` is only a shallow copy: the data elements are
        shared, so editing one would silently edit the original too.)

        :param dataset: a pydicom Dataset
        :param replacement: text placed in each blanked field
        :returns: a new, de-identified Dataset
        """
        cleaned = copy.deepcopy(dataset)
        for keyword in self.PHI_KEYWORDS:
            if keyword in cleaned:
                # Dates must stay valid DICOM dates, so blank them instead.
                is_date = cleaned[keyword].VR == "DA"
                setattr(cleaned, keyword, "" if is_date else replacement)
        # Vendors hide all sorts of things (sometimes PHI) in private tags.
        cleaned.remove_private_tags()
        return cleaned

    def save(self, *, dataset: pydicom.Dataset, path: FilePath) -> None:
        """Write a Dataset back to disk as a DICOM file.

        :param dataset: a pydicom Dataset
        :param path: output file path
        """
        dataset.save_as(path)

    def to_png(self, *, image: ArrayLike, path: FilePath) -> None:
        """Save a 2-D greyscale array (e.g. a windowed CT slice) as a PNG.

        Uses matplotlib's ``imsave`` so no extra imaging library is needed.

        :param image: 2-D numpy array
        :param path: output .png path
        """
        import matplotlib.pyplot as plt  # imported here: only needed for export

        image = np.asarray(image)
        # For 8-bit display data, pin the grey scale to 0..255 so matplotlib
        # does not re-stretch the contrast you chose with your window.
        limits = {"vmin": 0, "vmax": 255} if image.dtype == np.uint8 else {}
        plt.imsave(path, image, cmap="gray", **limits)
