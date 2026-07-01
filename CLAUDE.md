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
| 2026-06-30 | M3: flat closed-loop (Sum/PI TransferFunction/Saturation/RelationalOperator+TriangleGenerator PWM); client.load closes-then-loads | Subsystems can't be generated, so use flat primitives; PLECS won't refresh an open model on reload. Verified regulated buck Vo=15.00, 0.25% overshoot, 7.9ms. |
| 2026-06-30 | M4: plecs_scan_parameter (server-side sweep) + plecs_run_analysis (plecs.analyze -> bode/PM) | Sweeps and AC/steady-state analyses are core PLECS workflows; bode+PM from impulse-response analysis verified on the analysis-tools demo. |
| 2026-06-30 | M5: domain-classify LIBRARY (thermal/magnetic discoverable); document thermal signal names | simulate/analyze are domain-agnostic (thermal demo runs); authoring thermal/magnetic from scratch deferred (needs loss tables/permeance nets). |
| 2026-06-30 | M6: eval suite + docs + v0.5.0; stdio smoke (16 tools) | mcp-builder Phase-4 capstone; production server verified launching with full tool surface. |
| 2026-07-01 | C-Script control blocks authorable (CScript in KB; variable-port; code as string params) | Realistic digital control; verified C-Script PI regulates buck (Vo=15.00). Macros: Input/Output/DiscState/ParamRealData. See docs/cscript-notes.md. |
| 2026-07-01 | Docs KB from local plecshelp.qch (version-correct 4.9.5), TF-IDF search, corpus gitignored | Online docs are 5.0; the .qch matches the install. Copyright -> extract locally, commit only code. Tools: plecs_search_docs/get_doc/doc_for_component. |
