# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""registry.py - a machine-readable catalogue of every calculation in ``fpc``.

The library is written for people: keyword-only arguments, and docstrings that
give every parameter's unit (``:param density: fluid density [kg/m^3]``). This
module reads those same signatures and docstrings with Python's *introspection*
tools and turns them into data that programs can use:

    * the ``fpc search`` / ``fpc describe`` / ``fpc run`` commands,
    * the MCP server (``fpc/mcp_server.py``) that lets an AI model call the
      library as a calculator,
    * the generated ``llms.txt`` index for AI coding assistants.

Because everything is derived from the code, a new method shows up in all of
those places the moment it is written; there is no second list to keep in sync.

Techniques this module teaches:

    * ``inspect`` - list a class's methods and read each one's signature;
    * ``typing.get_type_hints`` - read type hints and turn them into JSON Schema;
    * ``re`` (regular expressions) - pull ``:param`` lines and ``[unit]`` tags
      out of docstrings;
    * ``dataclasses`` - small, immutable records (``Parameter``, ``Calculation``).

Example::

    from fpc import registry

    calc = registry.get("Fluids.reynolds_number")
    calc.parameters[0].unit                       # 'kg/m^3'
    registry.calculate("Fluids.reynolds_number",
                       {"density": 998, "velocity": 2, "length": 0.05,
                        "viscosity": 1e-3})        # 99800.0
"""

import inspect
import math
import re
import types
import typing
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike

import fpc

# Classes that are not exposed as calculations, and why. ``Utility`` and
# ``Dicom`` read and write files on disk (and Utility opens dialogs), which an
# AI tool should never be able to do on its own. ``Beam`` is a unit-aware
# dataclass you construct, not a set of standalone formulas.
EXCLUDED_CLASSES = {
    "Utility": "file input/output and dialogs",
    "Dicom": "reads and writes medical image files",
    "Beam": "a dataclass built from Pint quantities, not standalone formulas",
}

# JSON Schema for "a number, or a (possibly nested) list of numbers" - what
# ``ArrayLike`` means for the inputs a JSON client can actually send. Items are
# left open so a matrix (a list of lists) is accepted too.
_NUMBER_OR_ARRAY = {"anyOf": [{"type": "number"}, {"type": "array"}]}

# Matches a ``[unit]`` tag. Units never contain brackets themselves, so the
# pattern is "an opening bracket, anything that is not a bracket, a closing one".
_UNIT_TAG = re.compile(r"\[([^\[\]]+)\]")

# Matches one docstring field such as ``:param density: text`` or ``:returns: text``.
# The field's text runs until the next field (a line starting with ``:``) or
# the end of the docstring; ``re.DOTALL`` lets ``.`` cross line breaks.
_FIELD = re.compile(
    r"^:(?P<kind>param|returns?|raises)\s*(?P<name>\w*)\s*:(?P<text>.*?)(?=^:|\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass(frozen=True)
class Parameter:
    """One input of a calculation.

    :param name: keyword argument name
    :param description: the docstring text for this parameter
    :param unit: unit from the docstring's ``[unit]`` tag, or ``None``
    :param schema: JSON Schema for the value, or ``None`` if JSON cannot carry it
        (a DataFrame or a function, for example)
    :param required: ``True`` when the parameter has no default
    :param default: the default value (``None`` when required)
    """

    name: str
    description: str
    unit: str | None
    schema: dict[str, Any] | None
    required: bool
    default: Any = None


@dataclass(frozen=True)
class Calculation:
    """One public method of a domain class, described as data.

    :param domain: class name, e.g. ``"Fluids"``
    :param name: method name, e.g. ``"reynolds_number"``
    :param summary: first line of the docstring
    :param description: the docstring text before the ``:param`` fields
    :param parameters: the inputs, in signature order
    :param returns: the docstring's ``:returns:`` text
    """

    domain: str
    name: str
    summary: str
    description: str
    parameters: tuple[Parameter, ...]
    returns: str
    # The class itself; excluded from equality/printing to keep records tidy.
    cls: type = field(repr=False, compare=False)

    @property
    def key(self) -> str:
        """Unique name used everywhere else: ``"Domain.method"``."""
        return f"{self.domain}.{self.name}"

    @property
    def json_callable(self) -> bool:
        """``True`` if every *required* input can be sent as JSON.

        Optional inputs that JSON cannot carry are fine; they keep their
        default. This is what decides whether an AI tool may call it.
        """
        return all(p.schema is not None for p in self.parameters if p.required)

    def input_schema(self) -> dict[str, Any]:
        """JSON Schema (an ``object``) describing this calculation's inputs."""
        properties = {}
        for p in self.parameters:
            if p.schema is None:
                continue
            prop = dict(p.schema)
            prop["description"] = p.description
            if not p.required and _is_jsonable(p.default):
                prop["default"] = p.default
            properties[p.name] = prop
        return {
            "type": "object",
            "properties": properties,
            "required": [p.name for p in self.parameters if p.required],
            "additionalProperties": False,
        }

    def to_dict(self) -> dict[str, Any]:
        """A JSON-friendly description (used by ``describe`` and the MCP server)."""
        return {
            "key": self.key,
            "summary": self.summary,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "unit": p.unit,
                    "required": p.required,
                    "default": p.default if _is_jsonable(p.default) else repr(p.default),
                    "description": p.description,
                }
                for p in self.parameters
            ],
            "returns": self.returns,
            "input_schema": self.input_schema(),
        }


# --- Building the catalogue ------------------------------------------------


@cache
def calculations() -> tuple[Calculation, ...]:
    """Every public calculation in the library, in a stable (sorted) order.

    ``@cache`` means the (fairly slow) introspection runs only once per
    process; later calls return the same tuple instantly.

    :returns: tuple of :class:`Calculation`
    """
    found = []
    for class_name in sorted(fpc.__all__):
        cls = getattr(fpc, class_name)
        # Skip non-classes (``ureg``), Pint's ``Q_``, and the excluded classes.
        if not inspect.isclass(cls) or cls.__module__.split(".")[0] != "fpc":
            continue
        if class_name in EXCLUDED_CLASSES:
            continue
        for method_name, function in inspect.getmembers(cls, inspect.isfunction):
            if method_name.startswith("_"):
                continue  # private helpers are not part of the public API
            found.append(_describe(cls, method_name, function))
    return tuple(found)


def domains() -> dict[str, str]:
    """Map each domain class name to the first line of its docstring.

    :returns: dict such as ``{"Fluids": "Fluid dynamics helpers.", ...}``
    """
    out = {}
    for calc in calculations():
        if calc.domain not in out:
            out[calc.domain] = _first_line(calc.cls.__doc__ or "")
    return out


def get(key: str) -> Calculation:
    """Look one calculation up by ``"Domain.method"``.

    :param key: e.g. ``"Thermo.lmtd"``
    :returns: the :class:`Calculation`
    :raises KeyError: with close matches, if the key is unknown
    """
    for calc in calculations():
        if calc.key == key:
            return calc
    suggestions = [c.key for c in search(key.replace(".", " "), limit=5)]
    raise KeyError(f"unknown calculation {key!r}; did you mean one of {suggestions}?")


def search(query: str, *, limit: int = 10, domain: str | None = None) -> list[Calculation]:
    """Find calculations whose name or docstring mentions the query words.

    A deliberately simple ranking (no AI needed): each query word scores
    3 points if it is in the method name, 2 in the domain or summary, and 1
    anywhere else in the docstring. Highest score first.

    :param query: free text, e.g. ``"pipe pressure drop"``
    :param limit: maximum number of results [-]
    :param domain: only search this class (e.g. ``"Fluids"``)
    :returns: list of :class:`Calculation`, best match first
    """
    words = [w for w in re.split(r"[^a-z0-9]+", query.lower()) if w]
    scored = []
    for calc in calculations():
        if domain and calc.domain.lower() != domain.lower():
            continue
        name = calc.name.lower()
        head = f"{calc.domain} {calc.summary}".lower()
        body = calc.description.lower() + " " + " ".join(p.description for p in calc.parameters)
        score = sum(3 * (w in name) + 2 * (w in head) + (w in body.lower()) for w in words)
        if score or not words:
            scored.append((score, calc.key, calc))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [calc for _, _, calc in scored[:limit]]


def calculate(key: str, arguments: Mapping[str, Any]) -> Any:
    """Run a calculation from JSON-style arguments and return a JSON-style result.

    This is the single doorway the CLI and the MCP server use. It checks the
    argument names first so a caller (often an AI model) gets a helpful
    message instead of a Python traceback.

    :param key: ``"Domain.method"``
    :param arguments: keyword arguments as plain JSON values
    :returns: the result converted by :func:`to_jsonable`
    :raises ValueError: for unknown or missing arguments
    """
    calc = get(key)
    known = {p.name: p for p in calc.parameters}
    unknown = sorted(set(arguments) - set(known))
    if unknown:
        raise ValueError(f"{key} got unknown argument(s) {unknown}; expected {sorted(known)}")
    missing = [p.name for p in calc.parameters if p.required and p.name not in arguments]
    if missing:
        raise ValueError(f"{key} is missing required argument(s) {missing}")

    kwargs = {}
    for name, value in arguments.items():
        # JSON has no NumPy arrays, only lists. Methods that accept arrays do
        # maths like ``2 * x``, which on a *list* would repeat it, so convert.
        if isinstance(value, list) and known[name].schema == _NUMBER_OR_ARRAY:
            value = np.asarray(value, dtype=float)
        kwargs[name] = value

    # The domain classes hold no state, so a fresh instance per call is fine.
    result = getattr(calc.cls(), calc.name)(**kwargs)
    return to_jsonable(result)


def to_jsonable(value: Any) -> Any:
    """Convert a result into plain JSON types (numbers, strings, lists, dicts).

    NumPy arrays become lists, NumPy scalars become Python numbers, Pint
    quantities become ``{"magnitude": ..., "units": ...}``, and pandas tables
    become a list of row dicts. ``inf`` and ``nan`` (not valid JSON) become
    the strings ``"inf"``, ``"-inf"`` and ``"nan"``.

    :param value: anything a calculation returns
    :returns: an equivalent value built from JSON types only
    """
    if isinstance(value, bool | str | int) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, np.generic):  # NumPy scalar such as np.float64(3.0)
        return to_jsonable(value.item())
    if isinstance(value, np.ndarray):
        return [to_jsonable(v) for v in value.tolist()]
    if isinstance(value, Mapping):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "magnitude") and hasattr(value, "units"):  # a Pint quantity
        return {"magnitude": to_jsonable(value.magnitude), "units": str(value.units)}
    if hasattr(value, "to_dict"):  # a pandas DataFrame or Series
        return to_jsonable(
            value.to_dict(orient="records") if hasattr(value, "columns") else value.to_dict()
        )
    return repr(value)


def missing_units() -> list[str]:
    """List numeric parameters whose docstring has no ``[unit]`` tag.

    A quality check: every number an engineer passes in should say what
    unit it is in. Dimensionless numbers are tagged ``[-]``.

    :returns: ``"Domain.method(param)"`` strings
    """
    out = []
    for calc in calculations():
        for p in calc.parameters:
            numeric = p.schema in ({"type": "number"}, {"type": "integer"}, _NUMBER_OR_ARRAY)
            if numeric and p.unit is None:
                out.append(f"{calc.key}({p.name})")
    return out


def llms_txt() -> str:
    """Render a compact Markdown index of every calculation, for AI assistants.

    The format follows the https://llmstxt.org convention: a title, a short
    summary, then one line per item. Regenerate with ``fpc llms-txt > llms.txt``.

    :returns: the Markdown text
    """
    lines = [
        "# First Principles Code (fpc)",
        "",
        "> First-principles engineering calculations in Python. Every method is",
        "> keyword-only and takes plain SI floats unless its docstring says otherwise.",
        "",
        "Usage: `from fpc import Fluids; Fluids().reynolds_number(density=998, ...)`.",
        "Reference tables live in `fpc/data/` and are read with `fpc.Properties`.",
        "Files, dialogs and DICOM I/O are in `fpc.Utility` and `fpc.Dicom`.",
        "Each line below is `method(param [unit], optional=…)`; call it on an",
        "instance of the class named in the heading, e.g. `fpc.CT().apply_window(...)`.",
    ]
    current = None
    for calc in calculations():
        if calc.domain != current:
            current = calc.domain
            lines += ["", f"## {current}", ""]
        args = ", ".join(
            f"{p.name}" + (f" [{p.unit}]" if p.unit else "") + ("" if p.required else "=…")
            for p in calc.parameters
        )
        lines.append(f"- `{calc.name}({args})`: {calc.summary}")
    return "\n".join(lines) + "\n"


# --- Helpers ---------------------------------------------------------------


def _describe(cls: type, method_name: str, function: types.FunctionType) -> Calculation:
    """Build a :class:`Calculation` from one method."""
    doc = inspect.getdoc(function) or ""
    fields = _parse_fields(doc)
    try:
        hints = typing.get_type_hints(function)
    except Exception:  # an unresolvable hint must not break the whole catalogue
        hints = {}

    params = []
    for p in inspect.signature(function).parameters.values():
        if p.name == "self":
            continue
        text = fields.get(("param", p.name), "")
        required = p.default is inspect.Parameter.empty
        params.append(
            Parameter(
                name=p.name,
                description=text,
                unit=_unit_of(text),
                schema=_schema_for(hints.get(p.name), p.default),
                required=required,
                default=None if required else p.default,
            )
        )

    # The description is the prose above the first ``:param`` field.
    prose = re.split(r"^:", doc, maxsplit=1, flags=re.MULTILINE)[0].strip()
    return Calculation(
        domain=cls.__name__,
        name=method_name,
        summary=_first_line(doc),
        description=prose,
        parameters=tuple(params),
        returns=fields.get(("returns", ""), ""),
        cls=cls,
    )


def _parse_fields(doc: str) -> dict[tuple[str, str], str]:
    """Return ``{("param", name): text, ("returns", ""): text}`` from a docstring."""
    out = {}
    for match in _FIELD.finditer(doc):
        kind = "returns" if match["kind"].startswith("return") else match["kind"]
        # Collapse the wrapped lines of one field into a single line of text.
        out[(kind, match["name"])] = " ".join(match["text"].split())
    return out


def _unit_of(text: str) -> str | None:
    """The last ``[unit]`` tag in a parameter's text, or ``None``."""
    tags = _UNIT_TAG.findall(text)
    return tags[-1].strip() if tags else None


def _first_line(doc: str) -> str:
    return doc.strip().splitlines()[0].strip() if doc.strip() else ""


def _schema_for(hint: Any, default: Any) -> dict[str, Any] | None:
    """Translate a type hint into JSON Schema (``None`` if JSON cannot carry it).

    Without a hint we fall back on the default value's type, and failing
    that assume a number - most inputs in this library are.
    """
    if hint is None:
        if default is inspect.Parameter.empty or default is None:
            return {"type": "number"}
        return _schema_for(type(default), inspect.Parameter.empty)

    # Check ArrayLike *before* unwrapping aliases: NumPy defines it as an alias
    # for a long union that also contains ``str`` and ``bytes``, which would
    # wrongly turn an array input into a string.
    if hint is ArrayLike or hint == ArrayLike:
        return _NUMBER_OR_ARRAY
    # A ``type X = ...`` statement (Python 3.12+), or ``typing_extensions``'
    # equivalent, makes an alias object that stores the real type in
    # ``__value__``. Checking for the attribute instead of the class keeps
    # this working on Python 3.11, where ``typing.TypeAliasType`` is missing.
    if hasattr(hint, "__value__") and hasattr(hint, "__type_params__"):
        return _schema_for(hint.__value__, default)
    simple = {float: "number", int: "integer", bool: "boolean", str: "string"}
    if hint in simple:
        return {"type": simple[hint]}

    origin = typing.get_origin(hint)
    args = typing.get_args(hint)
    if origin is Literal:
        return {"enum": list(args)}
    if origin in (typing.Union, types.UnionType):
        # Keep the members JSON can express; ``str | DataFrame`` -> string.
        options = [s for a in args if a is not type(None) and (s := _schema_for(a, default))]
        if not options:
            return None
        return options[0] if len(options) == 1 else {"anyOf": options}
    if origin is np.ndarray:
        return {"type": "array", "items": {"type": "number"}}
    if origin in (list, tuple, Sequence) or hint in (list, tuple):
        item = _schema_for(args[0], inspect.Parameter.empty) if args else None
        return {"type": "array", "items": item or {}}
    if origin is dict or hint is dict:
        return {"type": "object"}
    return None  # DataFrame, Callable, pydicom Dataset, ...


def _is_jsonable(value: Any) -> bool:
    return value is None or isinstance(value, bool | int | float | str)
