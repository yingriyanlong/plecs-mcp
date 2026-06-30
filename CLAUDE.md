# plecs-mcp — project guide for AI agents

MCP server for full-scope PLECS simulation. **Stack**: Python 3.10+, official
`mcp` SDK (FastMCP, stdio), pyplecs/XML-RPC backend, numpy/scipy/matplotlib
for analysis.

## Build & test
```bash
pip install -e ".[sim,dev]"
ruff check .
pytest                      # offline tests only
```
PLECS-dependent (integration) tests require Windows + PLECS on RPC port 1080 and
are run manually; never commit code that breaks the offline suite.

## Architecture (see docs/development-plan.md for full detail)
- `plecs_mcp/rpc/client.py` — thin, normalised wrapper over PLECS XML-RPC
  (`plecs.load/simulate/set/get/close`). The hard-won fact: PLECS speaks
  **XML-RPC over HTTP**, methods under `plecs.`; a raw-socket/JSON protocol does
  NOT work.
- `plecs_mcp/server.py` — FastMCP server; one `@mcp.tool()` per capability,
  `plecs_` prefix, typed I/O, actionable errors.
- Authoring (M2+): generate `.plecs` text. **Connectivity is symbolic**
  (`SrcComponent`/`SrcTerminal` -> `DstComponent`/`DstTerminal`), not pixel
  coordinates — so electrical correctness needs correct terminal indices, not
  exact geometry. A component knowledge base holds each type's terminal map +
  params; `golden_models/` are the verified baselines.
- Large waveforms are kept server-side behind result handles; tools return
  summaries/metrics, not raw arrays, to manage agent context.

## Milestones
M0 connectivity · M1 run/observe existing models · M2 authoring engine ·
M3 control loops · M4 simulation scripts & analyses · M5 thermal & magnetic ·
M6 hardening + evaluations.

## Task protocol
1. Clarify to ~90% before building; one capability per step with a pass/fail check.
2. Verify on the FULL path (load + simulate on live PLECS), judge on >=2 signals.
3. Update PROGRESS.md and this file's decision log when behaviour changes.

## Decision log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-30 | Python + official mcp SDK, stdio | PLECS stack is Python-native (pyplecs, xmlrpc, verified PoC); local stdio is simplest/safest. |
| 2026-06-30 | Author circuits via `.plecs` generation, not an API | PLECS XML-RPC cannot construct schematics; `.plecs` text is generatable and verified. |
| 2026-06-30 | Connectivity treated as symbolic (name+terminal) | Confirmed by from-scratch buck loading clean on live PLECS. |
| 2026-06-30 | M1: param tuning via `ModelVars` in simulate opts; results behind handles | Matches PLECS scripting (override init vars per run); keeps agent context small. |
| 2026-06-30 | M2: serialize `.plecs` with NO wire `Points`; connectivity symbolic | Verified boost + buck-boost built from scratch load+simulate correctly; simpler/robuster specs. |
| 2026-06-30 | Harvest all PLECS demos into KB LIBRARY + template catalog; two-rail layout convention | The 89 demos are the layout gold standard; codifying them gives ~92-type coverage and clean generation. See docs/plecs-layout-conventions.md. |
| 2026-06-30 | Auto-layout via net analysis (series vs bridge by ground-touching); rebuild 1 wire/net with Points | Clean demo-grade schematics from pure netlists, no manual coordinates; verified buck/boost/buck-boost on live PLECS. |
