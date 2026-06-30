# plecs-mcp

An MCP (Model Context Protocol) server that gives an AI agent **full-scope
control of PLECS** power-electronics simulation: build circuits from a netlist,
auto-lay them out like the official demos, set parameters, simulate, sweep,
run AC/steady-state analyses, and read back metrics — all over PLECS's native
XML-RPC interface.

> Status: milestones **M0–M6 complete**, verified on live PLECS 4.9.5. See
> [CHANGELOG.md](CHANGELOG.md), [PROGRESS.md](PROGRESS.md) and
> [docs/development-plan.md](docs/development-plan.md).

## Why this exists

PLECS's RPC interface is **XML-RPC over HTTP** (default port 1080), methods under
the `plecs.` namespace. This server speaks it correctly and exposes well-typed MCP
tools. Circuits are *authored* by generating `.plecs` text — electrical
connectivity is symbolic (component name + terminal index), and layout follows the
two-rail conventions distilled from the 89 bundled PLECS demos
([docs/plecs-layout-conventions.md](docs/plecs-layout-conventions.md)).

## Requirements

- PLECS Standalone, **Preferences → General → RPC interface port** enabled (1080).
- Python 3.10+.

## Install & connect

```bash
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[sim,dev]"   # Windows
claude mcp add -s user plecs C:\path\to\plecs-mcp\.venv\Scripts\plecs-mcp.exe
```

Config via env: `PLECS_HOST` (localhost), `PLECS_RPC_PORT` (1080),
`PLECS_RPC_TIMEOUT` (30), `PLECS_DEMOS_DIR` (your PLECS `demos` folder, for
templates), `PLECS_MCP_MODEL_DIR` / `PLECS_MCP_PLOT_DIR` (output dirs).

## Tools

**Connectivity & models**
- `plecs_status` — is PLECS reachable?
- `plecs_load_model` / `plecs_close_model` — open/close a `.plecs` (load
  closes-then-loads so it never serves a stale model).

**Authoring**
- `plecs_build_model` — build a `.plecs` from a structured spec; **omit
  coordinates for automatic two-rail layout**; loads + validates.
- `plecs_validate_model` — load and report connectivity/parameter errors.
- `plecs_list_component_types` / `plecs_describe_component` — KB: curated core
  (terminal roles) + 91 harvested types; filter by domain
  (electrical/control/measurement/thermal/magnetic).
- `plecs_list_templates` / `plecs_describe_template` — 89 official demo
  topologies as clean starting points.

**Parameters & simulation**
- `plecs_set_param` — set a component parameter directly.
- `plecs_simulate` — run with `model_vars` / `solver_opts` overrides; returns a
  result handle + summary (no raw arrays).

**Results & analysis**
- `plecs_analyze_waveform` — steady_state, ripple_pp, mean, rms, min, max,
  overshoot, settling_time, rise_time.
- `plecs_get_waveform` / `plecs_plot_waveform` — downsampled series / PNG.
- `plecs_scan_parameter` — server-side sweep of a ModelVar → table + optimum.
- `plecs_run_analysis` — run a named PLECS Analysis (steady-state / AC) →
  bode summary (DC gain, gain-crossover, phase margin) + handle.

## Authoring example (auto-layout)

```python
spec = {
  "name": "buck", "time_span": "5e-3",
  "init": "Vi=24;\nD=0.5;\nLo=1e-4;\nCo=1e-4;\nRo=10;\nfsw=1e5;",
  "components": [
    {"type": "DCVoltageSource", "name": "VDCin", "params": {"V": "Vi"}},
    {"type": "Mosfet", "name": "FET1", "params": {"Ron": "1e-3"}},
    {"type": "Diode", "name": "D1", "params": {}},
    {"type": "Inductor", "name": "L1", "params": {"L": "Lo"}},
    {"type": "Capacitor", "name": "C1", "params": {"C": "Co"}},
    {"type": "Resistor", "name": "R1", "params": {"R": "Ro"}},
    {"type": "PulseGenerator", "name": "PWM", "params": {"f": "fsw", "DutyCycle": "D"}}
  ],
  "connections": [
    {"kind": "Wire", "src": ["VDCin", 1], "dsts": [["FET1", 1]]},
    {"kind": "Wire", "src": ["FET1", 2], "dsts": [["L1", 1], ["D1", 2]]},
    {"kind": "Wire", "src": ["L1", 2], "dsts": [["C1", 1], ["R1", 1]]},
    {"kind": "Wire", "src": ["C1", 2], "dsts": [["R1", 2], ["VDCin", 2], ["D1", 1]]},
    {"kind": "Signal", "src": ["PWM", 1], "dsts": [["FET1", 3]]}
  ],
  "outputs": [{"name": "Out1", "probe_component": "C1", "probe_signal": "Capacitor voltage"}]
}
# plecs_build_model(spec) -> writes buck.plecs, auto-lays it out, loads it.
```

## Golden models

`golden_models/` holds engine-generated, verified baselines: open-loop buck
(12.00 V), boost (48.02 V), inverting buck-boost (−24.07 V), and a closed-loop
buck (regulates to 15.00 V, 0.25% overshoot, 7.9 ms settling).

## Develop

```bash
ruff check .
pytest            # 17 offline tests; PLECS-dependent checks run manually on Windows
```
See [eval/](eval/) for the verifiable evaluation suite.

## License

MIT © 2026 yingriyanlong
