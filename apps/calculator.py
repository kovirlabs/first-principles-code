# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""calculator.py - a web form for every calculation in fpc, written once.

``examples/tools/step4_web_app.py`` hand-builds a form for one calculation.
This app builds a form for *all* of them from :mod:`fpc.registry`: each input
already has a name, a type (number, whole number, list, choice) and a unit, so
the right widget can be chosen automatically. A method added to the library
tomorrow shows up here with no change to this file.

Run it::

    uv sync --group apps
    uv run streamlit run apps/calculator.py

Three tabs per calculation:

    * **Result** - the answer (a number, a table for several values, a chart
      for a list);
    * **Uncertainty** - give any input a +/- percentage and see the spread of
      the answer (Monte Carlo, :mod:`fpc.uncertainty`);
    * **Calc sheet** - download the calculation as a Markdown report for a
      design file (:mod:`fpc.report`).

Techniques shown: generating a UI from data instead of writing it by hand,
``st.session_state``-free Streamlit (every rerun recomputes from the widgets),
and caching a slow, unchanging result with ``st.cache_data``.
"""

import json
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from fpc import registry
from fpc.report import calc_report
from fpc.uncertainty import Normal, monte_carlo

st.set_page_config(page_title="fpc calculator", layout="wide")


def widget(calc_key: str, p: registry.Parameter) -> Any:
    """Draw the right input widget for one parameter and return its value.

    The JSON Schema from the registry decides the widget. A required input
    starts empty (``None``) so the user must type a value: a made-up default
    such as 0 could produce a plausible-looking wrong answer.

    Streamlit remembers a widget's value by its ``key``; including the
    calculation in the key keeps ``length`` in one form from leaking into
    another form that also has a ``length``.
    """
    label = p.name + (f" [{p.unit}]" if p.unit else "")
    schema = p.schema or {}
    default = None if p.required else p.default
    key = f"in:{calc_key}:{p.name}"
    if "enum" in schema:
        options = schema["enum"]
        index = options.index(default) if default in options else 0
        return st.selectbox(label, options, index=index, help=p.description, key=key)
    kind = schema.get("type")
    if kind == "boolean":
        return st.checkbox(label, value=bool(default), help=p.description, key=key)
    if kind == "integer":
        return st.number_input(label, value=default, step=1, help=p.description, key=key)
    if kind == "number":
        return st.number_input(label, value=default, format="%g", help=p.description, key=key)
    if kind == "string":
        return st.text_input(label, value=default or "", help=p.description, key=key) or None
    # Arrays, "number or array", and objects: typed as JSON, e.g. [1, 2, 3].
    text = st.text_input(
        label + "  (JSON, e.g. [1, 2, 3])",
        value="" if default is None else json.dumps(default),
        help=p.description,
        key=key,
    )
    if not text or not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        st.error(f"{p.name}: not valid JSON; write numbers like 2.5 or lists like [1, 2, 3]")
        st.stop()


def show_result(result: Any, returns: str) -> None:
    """Show a result in the most readable form for its shape."""
    st.caption(f"Returns: {returns}")
    if isinstance(result, dict):
        st.table(pd.DataFrame({"value": result}))
    elif isinstance(result, list) and result and all(isinstance(v, int | float) for v in result):
        st.line_chart(result)
        with st.expander("Values"):
            st.write(result)
    elif isinstance(result, int | float):
        st.metric("Result", f"{result:.6g}")
    else:
        st.write(result)


# --- Pick a calculation -------------------------------------------------------

with st.sidebar:
    st.header("Calculation")
    query = st.text_input("Search", placeholder="e.g. pipe pressure drop")
    if query:
        choices = [c.key for c in registry.search(query, limit=25)]
    else:
        domain = st.selectbox("Domain", sorted(registry.domains()))
        choices = [c.key for c in registry.calculations() if c.domain == domain]
    # Only offer calculations whose required inputs a form can collect.
    choices = [k for k in choices if registry.get(k).json_callable]
    if not choices:
        st.warning("No calculation matches.")
        st.stop()
    key = st.selectbox("Calculation", choices, format_func=lambda k: k.split(".", 1)[1])

calc = registry.get(key)
st.title(calc.summary)
st.caption(f"`{calc.key}`")
with st.expander("Method and assumptions", expanded=False):
    st.text(calc.description)

# --- Inputs -----------------------------------------------------------------------

st.subheader("Inputs")
columns = st.columns(2)
values: dict[str, Any] = {}
for i, p in enumerate(p for p in calc.parameters if p.schema is not None):
    with columns[i % 2]:
        values[p.name] = widget(key, p)

missing = [p.name for p in calc.parameters if p.required and values.get(p.name) is None]
# Leave out optional inputs the user cleared, so the method's default applies.
arguments = {name: v for name, v in values.items() if v is not None}

if missing:
    st.info("Enter " + ", ".join(f"**{name}**" for name in missing) + " to calculate.")
    st.stop()

try:
    result = registry.calculate(key, arguments)
except (ValueError, TypeError, KeyError, ZeroDivisionError, ArithmeticError) as error:
    st.error(f"{type(error).__name__}: {error}")
    st.stop()

# --- Outputs ---------------------------------------------------------------------

tab_result, tab_uncertainty, tab_sheet = st.tabs(["Result", "Uncertainty", "Calc sheet"])

with tab_result:
    show_result(result, calc.returns)

with tab_uncertainty:
    numeric = [
        n
        for n, v in arguments.items()
        if isinstance(v, int | float) and not isinstance(v, bool) and v != 0
    ]
    if not numeric:
        st.write("This calculation has no numeric inputs to vary.")
    else:
        st.write("Give inputs a spread (one standard deviation, as a percent of the value):")
        spread = {}
        for name in numeric:
            spread[name] = st.slider(f"{name} +/- %", 0.0, 20.0, 0.0, 0.5, key=f"pct:{key}:{name}")
        # Several results (a dict or tuple): pick which one to study.
        output: str | int | None = None
        if isinstance(result, dict):
            output = st.selectbox("Result to study", list(result))
        elif isinstance(result, list):
            output = st.number_input("Result index to study", 0, len(result) - 1, 0)
        if any(spread.values()):
            inputs = {
                n: Normal(mean=v, std=abs(v) * spread[n] / 100) if spread.get(n) else v
                for n, v in arguments.items()
            }
            mc = monte_carlo(key, inputs, samples=5_000, seed=0, output=output)
            low, high = mc.interval(95)
            a, b, c = st.columns(3)
            a.metric("Mean", f"{mc.mean:.6g}")
            b.metric("Std. deviation", f"{mc.std:.4g}")
            c.metric("95 % interval", f"{low:.4g} to {high:.4g}")
            counts, edges = np.histogram(mc.samples, bins=40)
            st.bar_chart(
                pd.DataFrame({"runs": counts}, index=np.round((edges[:-1] + edges[1:]) / 2, 6))
            )
            st.write("Share of the spread from each input:")
            st.bar_chart(pd.Series(mc.sensitivity, name="share"))

with tab_sheet:
    title = st.text_input("Title", value=calc.summary)
    checked_by = st.text_input("Checked by", value="")
    sheet = calc_report(key, arguments, title=title, checked_by=checked_by)
    st.download_button("Download calc sheet (.md)", sheet, file_name=f"{calc.key}.md")
    st.markdown(sheet)
