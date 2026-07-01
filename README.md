# plecs-mcp

An MCP (Model Context Protocol) server that gives an AI agent **full-scope control
of PLECS** power-electronics simulation: build circuits from a netlist, auto-lay
them out like the official demos, set parameters, simulate, sweep, run
AC/steady-state analyses, read back metrics, drive **C-Script** controllers, and
search the PLECS manual — all over PLECS's native XML-RPC interface.

> Status: milestones **M0–M6 complete** + auto-layout, C-Script control and an
> offline docs KB, all verified on live PLECS 4.9.5. See
> [CHANGELOG.md](CHANGELOG.md) and [PROGRESS.md](PROGRESS.md).

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **PLECS Standalone** 4.9.x | The RPC interface must be enabled (Step 1). Verified on 4.9.5. |
| **Python 3.10+** | `python --version`. Windows: tick "Add Python to PATH" during install. |
| **git** *(optional)* | To clone/version the repo. |
| **Claude Code CLI** *(optional)* | `claude` — to register the server with `claude mcp add`. |

No other services are required. The server talks to PLECS with Python's stdlib
`xmlrpc.client`; it does **not** need `pyplecs`, MATLAB, or any vector database.

---

## Installation (Windows, PowerShell)

### Step 1 — Enable the PLECS RPC interface (do this first)
In PLECS: **File → Preferences → General → RPC interface**, tick it and set the
port to **1080**. Leave PLECS running. (Without this, `plecs_status` returns
`online: false`.)

### Step 2 — Get the code
```powershell
git clone https://github.com/yingriyanlong/plecs-mcp.git
cd plecs-mcp
```

### Step 3 — Create a virtual environment and install dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```
What gets installed:
- **Core** (required): `mcp` (the MCP server), `pydantic` (typed specs),
  `numpy` (waveform metrics + bode), `matplotlib` (waveform PNGs).
- **`[dev]`** (optional): `pytest`, `ruff` for tests/linting — omit with
  `pip install -e .` if you don't need them.

*(macOS/Linux: `python3 -m venv .venv && ./.venv/bin/python -m pip install -e ".[dev]"`.)*

### Step 4 — Build the offline documentation index (recommended)
Extracts your **installed** PLECS manual (version-correct) into a local, gitignored
search index used by `plecs_search_docs` / `plecs_doc_for_component`:
```powershell
.\.venv\Scripts\python.exe -m plecs_mcp.docs.extract "<PLECS>\onlinehelp\plecshelp.qch" .docs_cache
```
Adjust the path to your PLECS install. Skip this if you don't need doc search.

### Step 5 — Register the server with Claude Code
```powershell
claude mcp add -s user plecs D:\path\to\plecs-mcp\.venv\Scripts\plecs-mcp.exe
```
Use the **absolute path** to `plecs-mcp.exe` inside your venv. Restart your Claude
session so the tools load.

### Step 6 — Verify
```powershell
.\.venv\Scripts\python.exe -m pytest -q     # offline tests should pass
claude mcp list                             # -> plecs  ✔ Connected
```
Then, in Claude, call the **`plecs_status`** tool → expect `online: true`.

---

## Configuration (environment variables)

All optional; sensible defaults shown.

| Variable | Default | Purpose |
|----------|---------|---------|
| `PLECS_HOST` | `localhost` | PLECS RPC host. |
| `PLECS_RPC_PORT` | `1080` | PLECS RPC port (match Step 1). |
| `PLECS_RPC_TIMEOUT` | `30` | RPC timeout, seconds. |
| `PLECS_DEMOS_DIR` | *(unset)* | Your PLECS `demos` folder, so `plecs_list_templates` resolves absolute paths. |
| `PLECS_MCP_MODEL_DIR` | temp dir | Where generated `.plecs` files are written. |
| `PLECS_MCP_PLOT_DIR` | temp dir | Where waveform PNGs are written. |
| `PLECS_MCP_DOCS_DIR` | `<repo>/.docs_cache` | Location of the extracted docs index. |

Set them per-session (PowerShell): `$env:PLECS_RPC_PORT = "1080"`, or bake them into
the `claude mcp add` command's environment.

---

## Tools (19)

**Connectivity & models** — `plecs_status`, `plecs_load_model`, `plecs_close_model`
(load closes-then-loads so it never serves a stale model).

**Authoring** — `plecs_build_model` (omit coordinates for automatic two-rail
layout; supports C-Script blocks), `plecs_validate_model`,
`plecs_list_component_types`, `plecs_describe_component`, `plecs_list_templates`,
`plecs_describe_template`.

**Parameters & simulation** — `plecs_set_param`, `plecs_simulate` (with
`model_vars` / `solver_opts`).

**Results & analysis** — `plecs_analyze_waveform`, `plecs_get_waveform`,
`plecs_plot_waveform`, `plecs_scan_parameter` (server-side sweep),
`plecs_run_analysis` (steady-state / AC → bode + phase margin).

**Documentation** — `plecs_search_docs`, `plecs_get_doc`, `plecs_doc_for_component`
(your installed manual; build the index in Step 4).

---

## Quick usage

Once connected, just ask Claude in natural language, e.g. *"Build a 24 V→12 V,
100 kHz buck, sweep the duty and report Vo"* or *"Search the PLECS docs for the
C-Script output function"*. Programmatic example (auto-layout — no coordinates):

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
# plecs_build_model(spec) -> writes buck.plecs, auto-lays it out, loads it into PLECS.
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `plecs_status` → `online: false` | PLECS not running, or RPC not enabled / wrong port (Step 1). Check `PLECS_RPC_PORT`. |
| `ModuleNotFoundError: mcp` / `numpy` | You didn't install into the venv, or skipped Step 3. Re-run the install. |
| `docs index not built` | Run Step 4 (`python -m plecs_mcp.docs.extract ...`). |
| `claude: command not found` | Install Claude Code, or call the MCP exe by absolute path. On Windows the app may cache PATH — use full paths. |
| `plecs.load` shows an old circuit | Fixed in this server (it closes-then-loads); if you load in the GUI, close the window first. |
| Simulation "state discontinuity" | A solver/plant issue for that model at those parameters, not the tool — adjust the model or duty range. |

---

## Golden models & development

`golden_models/` holds engine-generated, verified baselines: open-loop buck
(12.00 V), boost (48.02 V), inverting buck-boost (−24.07 V), a PI closed-loop buck
(15.00 V, 0.25% overshoot, 7.9 ms), and a **C-Script**-controlled buck.

```powershell
ruff check .
.\.venv\Scripts\python.exe -m pytest -q     # offline tests; PLECS tests run manually on Windows
```
See [eval/](eval/) for the verifiable evaluation suite and
[docs/](docs/) for layout, C-Script and thermal/magnetic notes.

## License

MIT © 2026 yingriyanlong. The PLECS manual extracted by the docs KB is Plexim
copyright and is never committed (kept local in `.docs_cache/`).
