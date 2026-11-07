# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""python_support.py - keep the supported Python versions in step, and ratchet them.

Policy (docs/python-versions.md): support every CPython version that has not
reached end-of-life (EOL). Python releases a new version every October and
retires the oldest one five years after its release, so the supported range
slides forward one version a year.

The range is written down in several files, and they must agree:

    pyproject.toml   requires-python, classifiers, ruff target, mypy version
    tests.yml        the CI matrix (one test job per version)
    docs.yml / release.yml   which Python builds the docs and the release

This script is the one place that knows about all of them::

    uv run scripts/python_support.py check     # do all the files agree? (CI runs this)
    uv run scripts/python_support.py status    # compare with python.org's EOL dates
    uv run scripts/python_support.py set --oldest 3.12 --newest 3.16

``set`` rewrites every file; then run ``uv lock`` and the tests. ``status``
runs monthly in CI (.github/workflows/python-versions.yml) and opens an issue
when it is time to ratchet.

Techniques shown: ``tomllib`` (read TOML, standard library since 3.11),
``re`` for editing text without destroying comments, ``urllib`` for a JSON web
API, ``argparse`` subcommands, and exit codes as a way to signal CI.
"""

import argparse
import datetime
import json
import re
import sys
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
# Workflows that need just one Python (the newest supported) to do their job.
SINGLE_VERSION_WORKFLOWS = [
    ROOT / ".github" / "workflows" / "docs.yml",
    ROOT / ".github" / "workflows" / "release.yml",
]
# In those workflows the version appears twice: installed, then selected for
# every later uv command through the UV_PYTHON environment variable.
_SINGLE_VERSION = r"(uv python install |UV_PYTHON=)(\d+\.\d+)"
# endoflife.date publishes CPython's release and EOL dates as JSON.
EOL_API = "https://endoflife.date/api/python.json"

# A version is a (major, minor) tuple like (3, 11): tuples compare the way
# versions should, so (3, 9) < (3, 11), which the *strings* "3.9" < "3.11" get wrong.
Version = tuple[int, int]


def parse(text: str) -> Version:
    """``"3.11"`` -> ``(3, 11)``."""
    major, minor = text.split(".")[:2]
    return int(major), int(minor)


def fmt(version: Version) -> str:
    """``(3, 11)`` -> ``"3.11"``."""
    return f"{version[0]}.{version[1]}"


def span(oldest: Version, newest: Version) -> list[Version]:
    """Every minor version from oldest to newest inclusive (same major)."""
    return [(oldest[0], minor) for minor in range(oldest[1], newest[1] + 1)]


# --- Reading what the files currently say ----------------------------------


def current() -> dict[str, list[Version]]:
    """Collect every version statement from every file, keyed by where it came from."""
    text = PYPROJECT.read_text()
    data = tomllib.loads(text)
    found: dict[str, list[Version]] = {}

    floor = re.fullmatch(r">=\s*(\d+\.\d+)", data["project"]["requires-python"].strip())
    if not floor:
        sys.exit("requires-python must be a simple floor such as '>=3.11'")
    found["requires-python (oldest)"] = [parse(floor[1])]

    found["classifiers"] = [
        parse(c.rsplit("::", 1)[1])
        for c in data["project"]["classifiers"]
        if re.fullmatch(r"Programming Language :: Python :: \d+\.\d+", c)
    ]
    target = data["tool"]["ruff"]["target-version"]  # e.g. "py311"
    found["ruff target-version (oldest)"] = [(int(target[2]), int(target[3:]))]
    found["mypy python_version (oldest)"] = [parse(data["tool"]["mypy"]["python_version"])]

    matrix = re.search(r"python-version:\s*\[([^\]]*)\]", TESTS_WORKFLOW.read_text())
    if not matrix:
        sys.exit(f"no 'python-version: [...]' matrix found in {TESTS_WORKFLOW}")
    found["tests.yml matrix"] = [parse(v) for v in re.findall(r"\d+\.\d+", matrix[1])]

    for path in SINGLE_VERSION_WORKFLOWS:
        found[f"{path.name} (newest)"] = [
            parse(version) for _, version in re.findall(_SINGLE_VERSION, path.read_text())
        ]
    return found


def stale_constraints(oldest: Version) -> list[str]:
    """``[tool.uv]`` constraints whose marker is now always true and can go.

    A line such as ``"numpy>=2.5; python_version >= '3.12'"`` exists only to
    split the lockfile for older Pythons. Once the oldest supported version is
    3.12, the marker is always true and the line is clutter.
    """
    data = tomllib.loads(PYPROJECT.read_text())
    stale = []
    for line in data.get("tool", {}).get("uv", {}).get("constraint-dependencies", []):
        marker = re.search(r"python_version\s*>=\s*'(\d+\.\d+)'", line)
        if marker and parse(marker[1]) <= oldest:
            stale.append(line)
    return stale


# --- Subcommands -------------------------------------------------------------


def check(_args: argparse.Namespace) -> int:
    """Exit 1 (and explain) if the files disagree about the supported range."""
    found = current()
    oldest = found["requires-python (oldest)"][0]
    newest = max(found["classifiers"])
    expected = span(oldest, newest)

    problems = []
    for where, versions in found.items():
        if "(oldest)" in where:
            want = [oldest]
        elif "(newest)" in where:
            want = [newest] * max(1, len(versions))
        else:
            want = expected
        if versions != want:
            has, expect = list(map(fmt, versions)), list(map(fmt, want))
            problems.append(f"  {where}: has {has}, expected {expect}")
    if problems:
        problems.append(
            "  -> fix with: uv run scripts/python_support.py set "
            f"--oldest {fmt(oldest)} --newest {fmt(newest)}"
        )
    for line in stale_constraints(oldest):
        problems.append(f"  [tool.uv] constraint is now always true; delete it: {line!r}")

    if problems:
        print(f"Supported range is {fmt(oldest)}-{fmt(newest)}, but:")
        print("\n".join(problems))
        return 1
    print(f"OK: Python {fmt(oldest)}-{fmt(newest)} declared consistently.")
    return 0


def status(args: argparse.Namespace) -> int:
    """Compare our range with CPython's real release/EOL dates.

    Exit 0 if nothing to do, 1 if it is time to ratchet (CI turns that into
    an issue). Uses ``--today`` if given, so the logic is testable.
    """
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    with urllib.request.urlopen(EOL_API, timeout=30) as response:
        cycles = json.load(response)

    # Released (not just announced) and not yet EOL on `today`.
    supported = sorted(
        parse(c["cycle"])
        for c in cycles
        if c["cycle"].startswith("3.")
        and datetime.date.fromisoformat(c["releaseDate"]) <= today
        and datetime.date.fromisoformat(c["eol"]) > today
    )
    found = current()
    ours = (found["requires-python (oldest)"][0], max(found["classifiers"]))
    upstream = (supported[0], supported[-1])
    print(
        f"We support Python {fmt(ours[0])}-{fmt(ours[1])}; "
        f"CPython supports {fmt(upstream[0])}-{fmt(upstream[1])} as of {today}."
    )

    if ours == upstream:
        print("Nothing to do.")
        return 0
    print("\nTime to update. Run:")
    print(
        f"    uv run scripts/python_support.py set --oldest {fmt(upstream[0])} "
        f"--newest {fmt(upstream[1])}"
    )
    print("    uv lock && uv run pytest")
    if upstream[0] > ours[0]:
        print(f"\nPython {fmt(ours[0])} is end-of-life: raising the floor is a breaking")
        print("change for users still on it, so note it in CHANGELOG.md and bump the")
        print("minor version. Also look for code that existed only for the old version")
        print("(search for its number, e.g. 'Python 3.11' or 'py311').")
    if upstream[1] > ours[1]:
        print(f"\nPython {fmt(upstream[1])} is out: the new CI job will show whether every")
        print("dependency already ships wheels for it.")
    return 1


def set_range(args: argparse.Namespace) -> int:
    """Rewrite every file to declare ``--oldest`` .. ``--newest``."""
    oldest, newest = parse(args.oldest), parse(args.newest)
    if oldest > newest:
        sys.exit("--oldest must not be newer than --newest")
    versions = span(oldest, newest)
    compact = f"{oldest[0]}{oldest[1]}"  # (3, 11) -> "311"

    text = PYPROJECT.read_text()
    text = re.sub(r'(requires-python = ">=)\d+\.\d+', rf"\g<1>{fmt(oldest)}", text)
    text = re.sub(r'(target-version = "py)\d+', rf"\g<1>{compact}", text)
    text = re.sub(r'(\npython_version = ")\d+\.\d+', rf"\g<1>{fmt(oldest)}", text)
    # Replace the run of per-version classifiers with a freshly generated run.
    classifier = '    "Programming Language :: Python :: {}",\n'
    text = re.sub(
        r'(    "Programming Language :: Python :: \d+\.\d+",\n)+',
        "".join(classifier.format(fmt(v)) for v in versions),
        text,
    )
    PYPROJECT.write_text(text)

    matrix = ", ".join(f'"{fmt(v)}"' for v in versions)
    tests = re.sub(
        r"python-version:\s*\[[^\]]*\]", f"python-version: [{matrix}]", TESTS_WORKFLOW.read_text()
    )
    TESTS_WORKFLOW.write_text(tests)

    for path in SINGLE_VERSION_WORKFLOWS:
        path.write_text(re.sub(_SINGLE_VERSION, rf"\g<1>{fmt(newest)}", path.read_text()))

    print(f"Declared Python {fmt(oldest)}-{fmt(newest)} in pyproject.toml and the workflows.")
    for line in stale_constraints(oldest):
        print(f"Now remove from [tool.uv] constraint-dependencies: {line!r}")
    print("Next: uv lock && uv run pytest, then note the change in CHANGELOG.md.")
    print("Prose that names the range (update by hand): README.md, CLAUDE.md,")
    print("docs/python-versions.md; search for the old version number.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="verify every file agrees").set_defaults(func=check)
    st = commands.add_parser("status", help="compare with CPython's EOL schedule (needs internet)")
    st.add_argument("--today", help="pretend today is YYYY-MM-DD (for testing)")
    st.set_defaults(func=status)
    sr = commands.add_parser("set", help="rewrite every file to a new range")
    sr.add_argument("--oldest", required=True, help="e.g. 3.12")
    sr.add_argument("--newest", required=True, help="e.g. 3.16")
    sr.set_defaults(func=set_range)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
