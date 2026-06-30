"""PLECS MCP server (stdio transport).

M0: connectivity. M1: run / observe existing models — load, set, simulate,
analyse, plot. Tools use the ``plecs_`` prefix, typed I/O, and return result
handles for large waveforms so the agent's context stays small.

Run via the ``plecs-mcp`` console script or ``python -m plecs_mcp.server``.
"""
from __future__ import annotations

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .results import STORE
from .results.analysis import metrics as _metrics
from .results.analysis import to_signals
from .results.plot import plot_series
from .rpc import client

mcp = FastMCP("plecs-mcp")

# Minimal session state: remember the last loaded model so model_name is optional.
_STATE: dict[str, Optional[str]] = {"current_model": None}


@mcp.tool()
def plecs_status() -> dict:
    """Check whether the local PLECS XML-RPC interface is reachable.

    Returns ``online`` (bool), ``host``, ``port`` and a ``detail`` string. Call
    this first to confirm PLECS is running with its RPC port enabled.
    """
    return client.ping(load_config())


@mcp.tool()
def plecs_load_model(model_path: str) -> dict:
    """Load a .plecs model by absolute path. Returns the model name to use in
    subsequent simulate/set calls."""
    if not os.path.isfile(model_path):
        return {"ok": False, "error": f"file not found: {model_path}"}
    client.load(model_path)
    name = os.path.splitext(os.path.basename(model_path))[0]
    _STATE["current_model"] = name
    return {"ok": True, "model_name": name, "path": model_path}


@mcp.tool()
def plecs_close_model(model_name: Optional[str] = None) -> dict:
    """Close an open model (defaults to the last loaded model)."""
    name = model_name or _STATE["current_model"]
    if not name:
        return {"ok": False, "error": "no model_name given and none loaded"}
    client.close(name)
    if _STATE["current_model"] == name:
        _STATE["current_model"] = None
    return {"ok": True, "closed": name}


@mcp.tool()
def plecs_set_param(component: str, parameter: str, value: float) -> dict:
    """Set a single component parameter directly (plecs.set), e.g.
    component='agent_buck/R1', parameter='R', value=10. For sweeping
    InitializationCommands variables (Vi, D, ...), prefer passing model_vars to
    plecs_simulate."""
    client.set_param(component, parameter, value)
    return {"ok": True, "component": component, "parameter": parameter, "value": value}


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
