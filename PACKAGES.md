<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Evan Gress -->

# Python packages for engineers

A curated list of Python packages, grouped by engineering field. Each row says
**when** to reach for the package, not just what it is.

- Add a package to this project with `uv add <pypi-name>`; it updates
  `pyproject.toml` and the lockfile.
- Packages marked **(installed)** are already dependencies of this project.
- Entries marked **(stdlib)** ship with Python; there is nothing to install.
- Some packages install under one name and import under another. Those are
  listed in [PyPI name vs. import name](#pypi-name-vs-import-name).

**Last verified: 2026-11-06** (latest release date on PyPI, and that each link resolves).

## Core stack

| Package | Use it when... |
| --- | --- |
| [NumPy](https://numpy.org/) (installed) | You need fast arrays and vectorized math instead of Python loops |
| [SciPy](https://scipy.org/) (installed) | You need integration, ODEs, interpolation, root finding, linear algebra, or statistics |
| [pandas](https://pandas.pydata.org/) (installed) | Your data is a table: test logs, CSV/Excel exports, time series |
| [Matplotlib](https://matplotlib.org/) (installed) | You need a plot, especially a publication-quality or MATLAB-style figure |
| [SymPy](https://www.sympy.org/) | You want to derive, simplify, differentiate, or solve equations symbolically |
| [Pint](https://pint.readthedocs.io/) (installed) | You want units carried through a calculation so mismatches raise errors |
| [Jupyter](https://jupyter.org/) (`jupyterlab`) | You want an interactive notebook to explore and document a calculation |
| [marimo](https://marimo.io/) | You want a reactive notebook stored as plain `.py` (clean diffs, runs as a script or app) |

## Mechanical and structural

| Package | Use it when... |
| --- | --- |
| [sectionproperties](https://sectionproperties.readthedocs.io/) | You need area, inertia, torsion constant, or stresses for an arbitrary cross-section |
| [anaStruct](https://anastruct.readthedocs.io/) (`anastruct`) | You want quick 2-D frame and truss analysis with plotted diagrams |
| [Pynite](https://github.com/JWock82/Pynite) (`PyNiteFEA`) | You need 3-D frame, beam, and plate finite element analysis |
| [OpenSeesPy](https://openseespydoc.readthedocs.io/) (`openseespy`) | You need nonlinear, seismic, or research-grade structural analysis |
| [scikit-fem](https://scikit-fem.readthedocs.io/) | You want to write your own finite element solver in pure Python |
| [FEniCSx](https://fenicsproject.org/) (DOLFINx) | You need large-scale or multiphysics PDE solves; install via conda/Docker, not `uv add` (no PyPI package) |

## Thermal and fluids

| Package | Use it when... |
| --- | --- |
| [CoolProp](http://www.coolprop.org/) | You need thermophysical properties of water, refrigerants, air, or other fluids |
| [Cantera](https://github.com/Cantera/cantera) | You are modeling combustion, chemical kinetics, or reacting flows |
| [fluids](https://fluids.readthedocs.io/) | You are sizing pipes, pumps, valves, or computing pressure drop and friction factors |
| [ht](https://ht.readthedocs.io/) | You need heat transfer correlations, heat exchanger sizing, or insulation calcs |

## Electrical and signals

| Package | Use it when... |
| --- | --- |
| [scipy.signal](https://docs.scipy.org/doc/scipy/reference/signal.html) (installed, part of SciPy) | You need filters, FFT-based spectra, convolution, or transfer functions |
| [scikit-rf](https://scikit-rf.org/) | You work with RF/microwave networks: S-parameters, Touchstone files, calibration |
| [lcapy](https://lcapy.readthedocs.io/) | You want symbolic circuit analysis (Laplace domain, node equations, drawn schematics) |
| [PySpice](https://github.com/PySpice-org/PySpice) (flagged) | You want to drive ngspice simulations from Python. **Last PyPI release 2021**; consider [InSpice](https://github.com/Innovoltive/InSpice), an actively released fork |

## Controls and robotics

| Package | Use it when... |
| --- | --- |
| [python-control](https://python-control.org/) (`control`) | You need transfer functions, Bode/Nyquist/root locus, state space, or LQR (MATLAB Control Toolbox style) |
| [Robotics Toolbox](https://petercorke.github.io/robotics-toolbox-python/) (`roboticstoolbox-python`) | You need forward/inverse kinematics, dynamics, or trajectory planning for robot arms |
| [harold](https://github.com/ilayn/harold) (flagged) | You want a lightweight alternative controls toolbox. **Last PyPI release 2022**; prefer python-control |

## CAD, geometry, and meshing

| Package | Use it when... |
| --- | --- |
| [CadQuery](https://cadquery.readthedocs.io/) | You want parametric 3-D CAD models as code, exported to STEP/STL |
| [build123d](https://build123d.readthedocs.io/) | Same as CadQuery, with a more Pythonic API (both use the OpenCascade kernel) |
| [trimesh](https://trimesh.org/) | You need to load, repair, measure, or slice triangle meshes (STL, OBJ, PLY) |
| [gmsh](https://gmsh.info/) | You need to generate a finite element mesh from geometry |
| [PyVista](https://docs.pyvista.org/) | You need 3-D visualization of meshes, FEA results, or volume data |

## Optimization and uncertainty

| Package | Use it when... |
| --- | --- |
| [scipy.optimize](https://docs.scipy.org/doc/scipy/reference/optimize.html) (installed, part of SciPy) | You need curve fitting, root finding, or small constrained optimization |
| [Pyomo](https://www.pyomo.org/) | You are building large LP/MILP/NLP models (scheduling, design, process optimization) |
| [CVXPY](https://www.cvxpy.org/) | Your problem is convex and you want to write it the way it reads on paper |
| [SALib](https://salib.readthedocs.io/) | You need sensitivity analysis: which inputs actually drive the output (Sobol, Morris) |
| [pymoo](https://pymoo.org/) | You have multiple competing objectives and want a Pareto front (NSGA-II and friends) |

## Data and ML

| Package | Use it when... |
| --- | --- |
| [scikit-learn](https://scikit-learn.org/) | You need classic ML: regression, classification, clustering, surrogate models |
| [statsmodels](https://www.statsmodels.org/) | You need statistical models with p-values, confidence intervals, ANOVA, or time-series fits |
| [PyTorch](https://pytorch.org/) (`torch`) | You need deep learning or GPU-accelerated tensors |

## Medical imaging

| Package | Use it when... |
| --- | --- |
| [pydicom](https://pydicom.github.io/) (installed) | You need to read, edit, or write DICOM files |
| [SimpleITK](https://simpleitk.org/) | You work with 3-D volumes: resampling, registration, segmentation, whole DICOM series |
| [nibabel](https://nipy.org/nibabel/) | You work with NIfTI or other neuroimaging formats (research MRI) |
| [scikit-image](https://scikit-image.org/) | You need filtering, thresholding, edge detection, or Radon transform / CT reconstruction demos |
| [highdicom](https://highdicom.readthedocs.io/) | You need to create DICOM segmentations, structured reports, or annotations |
| [pynetdicom](https://pydicom.github.io/pynetdicom/) | You need to talk to a PACS (C-FIND / C-MOVE / C-STORE) |
| [MONAI](https://monai.io/) | You are doing deep learning on medical images (built on PyTorch) |
| [TotalSegmentator](https://github.com/wasserth/TotalSegmentator) | You want pretrained automatic segmentation of 100+ structures on CT/MR |
| [pyradiomics](https://pyradiomics.readthedocs.io/) (flagged) | You need quantitative radiomic features from an image + mask. **Last PyPI release 2023, wheels only up to Python 3.9**; expect a source build on Python 3.14 |

## Tool building

| Package | Use it when... |
| --- | --- |
| [argparse](https://docs.python.org/3/library/argparse.html) (stdlib) | You want a command-line interface with no extra dependency |
| [Typer](https://typer.tiangolo.com/) | You want a CLI built from type hints, with help text and validation for free |
| [Streamlit](https://streamlit.io/) | You want to turn a calculation into a shareable web app with sliders and plots |
| [tkinter](https://docs.python.org/3/library/tkinter.html) (stdlib) | You want a simple desktop GUI with no extra dependency |
| [PyInstaller](https://pyinstaller.org/) | You want to ship a script as a standalone executable for people without Python |

## Performance

| Package | Use it when... |
| --- | --- |
| [Numba](https://numba.pydata.org/) | A numeric loop is too slow and you want to JIT-compile it with one decorator |
| [Cython](https://cython.org/) | You need C speed or want to wrap existing C/C++ code |
| [JAX](https://docs.jax.dev/) | You need automatic differentiation, GPU/TPU, or vectorizing a NumPy-style function |

## PyPI name vs. import name

`uv add` takes the PyPI name; `import` takes the module name.

| `uv add ...` | `import ...` |
| --- | --- |
| `scikit-learn` | `sklearn` |
| `scikit-image` | `skimage` |
| `scikit-rf` | `skrf` |
| `scikit-fem` | `skfem` |
| `PyNiteFEA` | `Pynite` |
| `openseespy` | `openseespy.opensees` |
| `control` | `control` (project is called python-control) |
| `roboticstoolbox-python` | `roboticstoolbox` |
| `TotalSegmentator` | `totalsegmentator` |
| `torch` | `torch` (project is called PyTorch) |
| `jupyterlab` | run with `uv run jupyter lab` |
| `pyinstaller` | run with `uv run pyinstaller` |

## More curated lists

- [awesome-scientific-python](https://github.com/rossant/awesome-scientific-python)
- [awesome-scientific-computing](https://github.com/nschloe/awesome-scientific-computing)
- [awesome-python: Science](https://github.com/vinta/awesome-python#science)
- [awesome-python-chemistry](https://github.com/lmmentel/awesome-python-chemistry)
