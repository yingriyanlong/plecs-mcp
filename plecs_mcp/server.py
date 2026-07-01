"""PLECS MCP server (stdio transport).

M0: connectivity. M1: run / observe existing models — load, set, simulate,
analyse, plot. Tools use the ``plecs_`` prefix, typed I/O, and return result
handles for large waveforms so the agent's context stays small.

Run via the ``plecs-mcp`` console script or ``python -m plecs_mcp.server``.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .config import load_config
from .results import STORE
from .results.analysis import metrics as _metrics
from .results.analysis import bode as _bode
from .results.analysis import to_signals
from .results.plot import plot_series
from .rpc import client

mcp = FastMCP("plecs-mcp")

# Minimal session state: remember the last loaded model so model_name is optional.
_STATE: dict[str, Optional[str]] = {"current_model": None}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True, idempotentHint=True))
def plecs_status() -> dict:
    """Check whether the local PLECS XML-RPC interface is reachable.

    Returns ``online`` (bool), ``host``, ``port`` and a ``detail`` string. Call
    this first to confirm PLECS is running with its RPC port enabled.
    """
    return client.ping(load_config())


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True, idempotentHint=False))
def plecs_load_model(model_path: str) -> dict:
    """Load a .plecs model by absolute path. Returns the model name to use in
    subsequent simulate/set calls."""
    if not os.path.isfile(model_path):
        return {"ok": False, "error": f"file not found: {model_path}"}
    client.load(model_path)
    name = os.path.splitext(os.path.basename(model_path))[0]
    _STATE["current_model"] = name
    return {"ok": True, "model_name": name, "path": model_path}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True, idempotentHint=True))
def plecs_close_model(model_name: Optional[str] = None) -> dict:
    """Close an open model (defaults to the last loaded model)."""
    name = model_name or _STATE["current_model"]
    if not name:
        return {"ok": False, "error": "no model_name given and none loaded"}
    client.close(name)
    if _STATE["current_model"] == name:
        _STATE["current_model"] = None
    return {"ok": True, "closed": name}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True, idempotentHint=True))
def plecs_set_param(component: str, parameter: str, value: float) -> dict:
    """Set a single component parameter directly (plecs.set), e.g.
    component='agent_buck/R1', parameter='R', value=10. For sweeping
    InitializationCommands variables (Vi, D, ...), prefer passing model_vars to
    plecs_simulate."""
    client.set_param(component, parameter, value)
    return {"ok": True, "component": component, "parameter": parameter, "value": value}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True, idempotentHint=True))
def plecs_simulate(
    model_name: Optional[str] = None,
    model_vars: Optional[dict] = None,
    solver_opts: Optional[dict] = None,
) -> dict:
    """Run a simulation and store the result server-side.

    ``model_vars`` overrides model InitializationCommands variables for this run
    (e.g. {"Vi": 48, "D": 0.4}); ``solver_opts`` overrides solver settings.
    Returns a ``handle`` plus a summary (point count, signal count, time span,
    last values). Use plecs_analyze_waveform / plecs_plot_waveform on the handle.
    """
    name = model_name or _STATE["current_model"]
    if not name:
        return {"ok": False, "error": "no model loaded; call plecs_load_model first"}
    opts: dict = {}
    if model_vars:
        opts["ModelVars"] = model_vars
    if solver_opts:
        opts["SolverOpts"] = solver_opts
    r = client.simulate(name, opts or None)
    time, values = to_signals(r.get("Time") or [], r.get("Values") or [])
    handle = STORE.add(name, time, values)
    last = [sig[-1] for sig in values] if (values and time) else []
    return {
        "ok": True,
        "handle": handle,
        "model": name,
        "n_points": len(time),
        "n_signals": len(values),
        "t_start": time[0] if time else None,
        "t_end": time[-1] if time else None,
        "last_values": last,
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True))
def plecs_analyze_waveform(
    handle: str,
    signal: int = 0,
    metrics: Optional[list] = None,
    target: Optional[float] = None,
) -> dict:
    """Compute scalar metrics on one signal of a stored result.

    Supported metrics: steady_state, ripple_pp, mean, rms, min, max, overshoot,
    settling_time, rise_time. ``target`` (optional) is the reference for
    overshoot/settling/rise; otherwise the steady-state value is used.
    """
    rec = STORE.get(handle)
    if not rec:
        return {"ok": False, "error": f"unknown handle: {handle}"}
    vals = rec["values"]
    if signal < 0 or signal >= len(vals):
        return {"ok": False, "error": f"signal {signal} out of range (0..{len(vals)-1})"}
    m = _metrics(rec["time"], vals[signal], names=metrics, target=target)
    return {"ok": True, "handle": handle, "signal": signal, "metrics": m}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True))
def plecs_get_waveform(handle: str, signal: int = 0, max_points: int = 500) -> dict:
    """Return a downsampled (time, value) series for one signal, for plotting or
    inspection. Capped at ``max_points`` to protect context."""
    rec = STORE.get(handle)
    if not rec:
        return {"ok": False, "error": f"unknown handle: {handle}"}
    vals = rec["values"]
    if signal < 0 or signal >= len(vals):
        return {"ok": False, "error": f"signal {signal} out of range (0..{len(vals)-1})"}
    t, y = rec["time"], vals[signal]
    step = max(1, len(t) // max_points)
    return {"ok": True, "handle": handle, "signal": signal,
            "time": t[::step], "values": y[::step], "downsample_step": step}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=False, idempotentHint=True))
def plecs_plot_waveform(handle: str, signals: Optional[list] = None,
                        out_path: Optional[str] = None, title: str = "PLECS waveforms") -> dict:
    """Render one or more signals of a stored result to a PNG; returns its path."""
    rec = STORE.get(handle)
    if not rec:
        return {"ok": False, "error": f"unknown handle: {handle}"}
    vals = rec["values"]
    idxs = signals if signals is not None else list(range(len(vals)))
    series = {f"signal[{i}]": vals[i] for i in idxs if 0 <= i < len(vals)}
    if not series:
        return {"ok": False, "error": "no valid signals selected"}
    path = plot_series(rec["time"], series, out_path=out_path, title=title)
    return {"ok": True, "handle": handle, "path": path, "signals": list(idxs)}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True, idempotentHint=True))
def plecs_scan_parameter(param: str, start: float, end: float, points: int,
                         model_name: Optional[str] = None, signal: int = 0,
                         metric: str = "steady_state", minimize: bool = False,
                         base_vars: Optional[dict] = None) -> dict:
    """Sweep a model variable over [start, end] in `points` steps, simulating each
    run and extracting `metric` from `signal`. Returns the (value, metric) table
    plus the optimum. `base_vars` holds other ModelVars fixed. Runs server-side so
    the agent gets a compact result instead of many raw waveforms."""
    name = model_name or _STATE["current_model"]
    if not name:
        return {"ok": False, "error": "no model loaded; call plecs_load_model first"}
    points = max(2, int(points))
    step = (end - start) / (points - 1)
    rows = []
    for i in range(points):
        v = start + i * step
        mv = dict(base_vars or {})
        mv[param] = v
        try:
            r = client.simulate(name, {"ModelVars": mv})
        except Exception as e:
            rows.append({"value": v, metric: None, "error": str(e)[:80]})
            continue
        time, values = to_signals(r.get("Time") or [], r.get("Values") or [])
        val = _metrics(time, values[signal], names=[metric]).get(metric) if values else None
        rows.append({"value": v, metric: val})
    valid = [r for r in rows if r.get(metric) is not None]
    if not valid:
        return {"ok": False, "error": "no successful runs", "rows": rows}
    opt = (min if minimize else max)(valid, key=lambda r: r[metric])
    return {"ok": True, "param": param, "metric": metric, "signal": signal,
            "n": points, "rows": rows, "optimum": opt}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True, idempotentHint=True))
def plecs_run_analysis(analysis_name: str, model_name: Optional[str] = None) -> dict:
    """Run a named PLECS Analysis defined in the model (Steady-State / AC Sweep /
    Impulse Response / Multitone). For frequency-response analyses, returns a bode
    summary (DC gain dB, gain-crossover Hz, phase margin deg) and a result handle
    (signal 0 = magnitude dB, signal 1 = phase deg vs frequency) for plotting.
    The analysis must be defined in the model (PLECS Analysis dialog)."""
    name = model_name or _STATE["current_model"]
    if not name:
        return {"ok": False, "error": "no model loaded; call plecs_load_model first"}
    try:
        r = client.analyze(name, analysis_name)
    except Exception as e:
        return {"ok": False, "error": f"analyze failed: {str(e)[:200]}"}
    if isinstance(r, dict) and "F" in r and ("Gr" in r or "Gi" in r):
        b = _bode(r["F"], r.get("Gr") or [], r.get("Gi") or [])
        handle = STORE.add(name + ":" + analysis_name, b["f"], [b["mag_db"], b["phase_deg"]])
        return {"ok": True, "type": "frequency_response", "analysis": analysis_name,
                "handle": handle, "n_points": len(b["f"]),
                "f_start_hz": b["f"][0], "f_end_hz": b["f"][-1],
                "dc_gain_db": round(b["dc_gain_db"], 2),
                "gain_crossover_hz": (round(b["gain_crossover_hz"], 1) if b["gain_crossover_hz"] else None),
                "phase_margin_deg": (round(b["phase_margin_deg"], 1) if b["phase_margin_deg"] else None)}
    return {"ok": True, "type": "operating_point", "analysis": analysis_name,
            "keys": list(r.keys()) if isinstance(r, dict) else None,
            "note": "non-frequency analysis (e.g. steady-state sets the operating point; no series returned)"}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True))
def plecs_search_docs(query: str, top_k: int = 5) -> dict:
    """Search the offline PLECS manual (your installed version) and return the
    best-matching topics (title + summary + page name). Use plecs_get_doc to read
    a page. If the index isn't built, run:
    python -m plecs_mcp.docs.extract <plecshelp.qch> .docs_cache"""
    from .docs.search import get_index
    idx = get_index()
    if idx is None:
        return {"ok": False, "error": "docs index not built; run "
                "'python -m plecs_mcp.docs.extract <PLECS>/onlinehelp/plecshelp.qch .docs_cache'"}
    return {"ok": True, "query": query, "results": idx.search(query, top_k)}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True))
def plecs_get_doc(name: str) -> dict:
    """Return the text of a PLECS manual page by name (from plecs_search_docs)."""
    from .docs.search import get_index
    idx = get_index()
    if idx is None:
        return {"ok": False, "error": "docs index not built"}
    d = idx.get(name)
    if not d:
        return {"ok": False, "error": f"no doc '{name}'; use plecs_search_docs"}
    text = d["text"]
    return {"ok": True, "name": d["name"], "title": d["title"],
            "text": text[:6000], "truncated": len(text) > 6000}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True))
def plecs_doc_for_component(type_name: str) -> dict:
    """Return the manual page for a component type (e.g. Mosfet, Diode,
    TransferFunction), so parameters/terminals come from the real docs."""
    from .docs.search import get_index
    idx = get_index()
    if idx is None:
        return {"ok": False, "error": "docs index not built"}
    key = type_name.lower()
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", type_name).replace("_", " ").lower()
    exact = next((x for x in idx.index if x["name"].lower() == key
                  or x["title"].lower() in (key, spaced)), None)
    if exact is None:
        res = idx.search(spaced, top_k=1)
        exact = idx.by_name.get(res[0]["name"]) if res else None
    if exact is None:
        return {"ok": False, "error": f"no doc for '{type_name}'"}
    d = idx.get(exact["name"])
    return {"ok": True, "type": type_name, "name": d["name"], "title": d["title"],
            "text": d["text"][:6000]}


_RO = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
def plecs_capabilities() -> dict:
    """One-call health + capability report: PLECS reachability + config, whether the
    docs index is built, the demos dir, knowledge-base sizes, and golden models.
    Use this first to diagnose setup before other calls."""
    cfg = load_config()
    ping = client.ping(cfg)
    from .authoring import templates
    from .authoring.kb import CORE, LIBRARY, known_types
    from .docs.search import default_dir, get_index
    idx = get_index()
    return {
        "plecs": {"online": ping["online"], "host": cfg.host, "port": cfg.port,
                  "detail": ping["detail"]},
        "knowledge_base": {"core_types": len(CORE), "library_types": len(LIBRARY),
                           "total_types": len(known_types())},
        "templates": {"count": len(templates.CATALOG),
                      "demos_dir": templates.demos_root() or "(set PLECS_DEMOS_DIR)"},
        "docs": {"index_built": idx is not None, "pages": len(idx.index) if idx else 0,
                 "dir": default_dir()},
        "config": {"model_dir": os.environ.get("PLECS_MCP_MODEL_DIR", "(system temp)"),
                   "plot_dir": os.environ.get("PLECS_MCP_PLOT_DIR", "(system temp)")},
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def plecs_check_spec(spec: dict) -> dict:
    """Statically validate a circuit spec WITHOUT touching PLECS: unknown component
    types, invalid terminal indices, floating electrical terminals (not wired), and
    whether a source exists. A fast pre-check before plecs_build_model."""
    from .authoring.kb import CORE, validate_spec
    from .authoring.spec import CircuitSpec
    try:
        s = CircuitSpec(**spec)
    except Exception as e:
        return {"ok": False, "errors": [f"invalid spec: {e}"], "warnings": []}
    errors = validate_spec(s)
    referenced = set()
    for conn in s.connections:
        if conn.kind != "Wire":
            continue
        referenced.add((conn.src[0], int(conn.src[1])))
        for d in conn.dsts:
            referenced.add((d[0], int(d[1])))
    warnings = []
    for c in s.components:
        info = CORE.get(c.type)
        if info and info.get("domain") == "electrical":
            for term, role in info["terminals"].items():
                if (c.name, term) not in referenced:
                    warnings.append(f"floating: {c.type} '{c.name}' terminal {term} ({role}) not wired")
    if not any(c.type in ("DCVoltageSource", "DCCurrentSource") for c in s.components):
        warnings.append("no source (DCVoltageSource/DCCurrentSource) in the circuit")
    return {"ok": not errors, "errors": errors, "warnings": warnings}


from .authoring.tools import register_authoring_tools
register_authoring_tools(mcp)
from .resources import register_resources_and_prompts
register_resources_and_prompts(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
