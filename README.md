# plecs-mcp

An MCP (Model Context Protocol) server that gives an AI agent **full-scope
control of PLECS** power-electronics simulation: build circuits, set
parameters, run simulations, and analyse results — over PLECS's native
XML-RPC interface.

> Status: early development. Milestone **M0 (connectivity)** is in place; see
> [docs/development-plan.md](docs/development-plan.md) for the full roadmap
> (authoring engine, control loops, simulation scripts/analyses, thermal & magnetic).

## Why this exists

PLECS's RPC interface is **XML-RPC over HTTP** (default port 1080), with methods
under the `plecs.` namespace. This server talks to it correctly (verified
against live PLECS 4.7) and exposes well-typed MCP tools. Circuit *authoring*
is done by generating `.plecs` files — electrical connectivity is defined
symbolically by component name + terminal index, which a from-scratch buck
model proved loads and simulates correctly (Vo = 11.9985 V vs. theoretical
12 V). That verified model lives in [`golden_models/`](golden_models/).

## Requirements

- PLECS Standalone with **Preferences > General > RPC interface port** enabled (1080).
- Python 3.10+.

## Install

```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\python -m pip install -e ".[sim,dev]"
```

## Run / connect to Claude

```bash
# Windows absolute paths:
claude mcp add plecs C:\path\to\plecs-mcp\.venv\Scripts\python.exe -m plecs_mcp.server
```

Then call the `plecs_status` tool to confirm PLECS is reachable.

## Configuration

Environment variables: `PLECS_HOST` (default `localhost`), `PLECS_RPC_PORT`
(default `1080`), `PLECS_RPC_TIMEOUT` (seconds, default `30`).

## Develop

```bash
ruff check .
pytest            # offline tests; PLECS-dependent tests run manually on Windows
```

## License

MIT © 2026 yingriyanlong
