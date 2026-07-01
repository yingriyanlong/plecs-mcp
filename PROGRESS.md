# PROGRESS

**Goal**: ship a production-grade MCP server giving an agent full-scope PLECS
control (build / run / tune / analyse), covering electrical, control, thermal,
magnetic, plus simulation scripts and analyses.

## Verified (evidence-backed)
- PLECS RPC = XML-RPC over HTTP on port 1080; raw-socket JSON does NOT work
  (reproduced on live PLECS: repo client timed out, xmlrpc Fault returned).
- From-scratch agent-authored buck loads + simulates on live PLECS 4.7:
  **Vo = 11.9985 V** (theory 12 V). Model: `golden_models/agent_buck.plecs`.
- M0 connectivity layer (`rpc/client.ping`, `plecs_status` tool) implemented.

## Decisions / constraints
- Stack: Python + mcp SDK (stdio). Backend: pyplecs/XML-RPC.
- Authoring via `.plecs` generation; connectivity symbolic (name + terminal).
- Out of scope: pixel-perfect auto-routing of arbitrary complex schematics;
  bypassing PLECS; destructive ops without confirmation.

## Now / next
- [x] M0 scaffold + connectivity + git repo + push to GitHub (private).
- [ ] M1: load/set/simulate(single+batch)/waveform metrics/plot; verify on
      `simple_buck` sample and `agent_buck` golden model.
- [ ] M2: Spec -> .plecs serializer + component KB (electrical) + build/validate.

## Environment notes
- PLECS on Windows, RPC port 1080. (If `gh` isn't on PATH after install, call it
  by its full install path until the app's PATH refreshes.)

## M1 done (2026-06-30)
Run/observe tools implemented and verified on live PLECS 4.7:
- Tools: plecs_load_model, plecs_close_model, plecs_set_param, plecs_simulate
  (with model_vars / solver_opts overrides), plecs_analyze_waveform,
  plecs_get_waveform, plecs_plot_waveform. Results held server-side behind
  handles; tools return summaries/metrics, not raw arrays.
- Verified: agent_buck Vo=11.9985 V, ripple 0.377 V, overshoot 85.3%
  (matches ζ≈0.05), settling 3.42 ms. model_vars tuning: Vi=12 -> Vo=5.999 V;
  D=0.4 -> Vo=9.606 V. simple_buck sample: 13-signal outport parsed. Plot PNG OK.
- Offline pytest: 3 passed. Registered via `claude mcp add -s user plecs` ->
  `claude mcp list` shows plecs ✔ Connected.

Next: M2 authoring engine — Spec -> .plecs serializer + component KB (electrical)
+ plecs_build_model/validate + golden topologies (boost, buck-boost).

## M2 done (2026-06-30)
Authoring engine implemented and verified — the agent can build circuits from scratch.
- `authoring/`: `kb.py` (component knowledge base: PLECS type -> terminal map +
  params, verified indices), `spec.py` (pydantic CircuitSpec), `serializer.py`
  (Spec -> .plecs; Points omitted, connectivity symbolic), `tools.py`.
- Tools: plecs_build_model, plecs_validate_model, plecs_list_component_types,
  plecs_describe_component.
- Verified from-scratch builds on live PLECS: agent_boost Vo=48.019 V
  (Vi/(1-D)=48), agent_buckboost Vo=-24.071 V (-Vi*D/(1-D)=-24, sign correct).
  Both added to golden_models. Offline pytest: 6 passed.
- Confirmed: omitting wire `Points` loads cleanly — wiring is purely symbolic.

Next: M3 control loops — control-domain KB (sum, gain, PI/PID, PWM comparator,
sawtooth, limiter, sensors) + closed-loop golden (regulated buck).

## M2.5 layout + demo knowledge (2026-06-30)
Studied the 89 bundled PLECS demos and codified them into the engine.
- Layout: confirmed why generated circuits looked messy (single row, no wire
  Points). Added `points` support to the serializer; adopted the demos' two-rail
  grid (top rail y=95, ground y~185, vertical bridges y=140, ~50px spacing).
  Re-generated agent_boost demo-grade clean AND correct (Vo=48.019 V) — verified
  visually in PLECS. Conventions written to docs/plecs-layout-conventions.md.
- Demo harvest: parsed all 89 demos -> reference/harvested_components.json
  (91 component types with params + terminal counts) and reference/demo_catalog.json
  (89 reference topologies). KB now has curated CORE (terminal roles) + full
  LIBRARY (harvested) backing describe/list/validate for ~92 types.
- New tools: plecs_list_templates / plecs_describe_template (use a demo as a clean
  starting point). Offline pytest: 9 passed.

TODO: re-layout agent_buckboost to demo-grade; add a role-based auto-layout helper
so generation is clean without manual coordinates; expand CORE roles for control
parts (M3).

## Auto-layout helper (2026-06-30)
`authoring/layout.py`: net-analysis two-rail layouter. From components + symbolic
connections only (no coordinates), it infers the ground net, ranks nodes along the
current path, classifies each part as series (both terminals non-ground -> top
rail) or bridge (one terminal on ground -> vertical), places them on the demo grid,
and rebuilds one orthogonal wire per net with Points. build_model auto-runs it when
no positions are given (layout='manual' to keep explicit coords).
- Verified from ZERO coordinates on live PLECS, clean + correct (visually checked):
  buck Vo=12.04, boost Vo=48.02, buck-boost Vo=-24.07. Inductor correctly drawn as
  series (buck/boost) vs shunt-to-ground (buck-boost) via connectivity.
- All three golden_models regenerated via auto-layout (now engine-reproducible).
  Offline pytest: 11 passed.

## M3 control loops (2026-06-30)
Learned the analog control chain from buck_converter_with_voltage_controls and
built a FLAT (no-subsystem) closed loop the engine can generate.
- CORE KB gained control types with terminal roles: Sum (1=out,2=in+,3=in-),
  TransferFunction (1=in,2=out), Saturation, RelationalOperator (1,2=in,3=out),
  TriangleGenerator, plus Gain/Constant. Param formats from the demo (Sum
  Inputs "|+-", RelationalOperator Operator 6 = ">=", TF Numerator/Denominator
  "[a b]").
- golden_models/agent_buck_closedloop: voltage-mode PI + triangle-carrier PWM.
  Sensor (Voltmeter) -> Sum(Vref-Vo) -> PI (TransferFunction [Kp Ki]/[1 0]) ->
  Saturation -> RelationalOperator vs TriangleGenerator -> MOSFET gate. Output
  cap ESR for damping.
- Verified on live PLECS: Vo=15.00 V (target 15), overshoot 0.25%, settling
  7.9 ms, ripple 0.075 V; tracks reference (Vref=10 -> Vo=10.00).
- BUG FIX: plecs.load did not refresh an already-open model -> rpc.client.load
  now closes-then-loads. (Earlier closed-loop "ringing" was the stale base model;
  the real model is well damped.)
- Offline pytest: 13 passed.

Honest limits: control-block auto-layout is power-focused (control parts are
strung along the top rail — functional, not pretty). A single PI on a high-Q LC
is marginal; proper compensator design wants the AC/bode tools in M4.

## M4 simulation scripts & analyses (2026-06-30)
- plecs_scan_parameter: server-side sweep of a ModelVar over a range; simulates
  each, extracts a metric, returns (value, metric) table + optimum; per-run errors
  captured gracefully. Verified: buck D-sweep 0.2..0.8 -> Vo=D*Vin for valid runs
  (high-D runs hit a PLECS "state discontinuity" and were recorded, not crashed).
- plecs_run_analysis: runs a named PLECS Analysis (SteadyState / ACSweep /
  ImpulseResponse / Multitone) via plecs.analyze. Frequency responses -> bode
  (dc_gain_db, gain_crossover_hz, phase_margin_deg) + result handle (sig0=mag dB,
  sig1=phase deg). rpc.client.analyze + results.analysis.bode added.
  Verified on buck_converter_with_analysis_tools: control-to-output TF 300 pts,
  DC gain 29.0 dB, crossover 5.42 kHz (bare LC plant TF).
- Offline pytest: 14 passed (added synthetic bode test).

Note: running an analysis needs it defined in the model (PLECS Analysis dialog +
SmallSignalPerturbation/Response blocks for AC). Generating analyses from scratch
is future work; running them on existing/demo models works now.

## M5 thermal & magnetic (2026-06-30)
- The simulate/analyze/scan tools are domain-agnostic and already run thermal &
  magnetic models (verified: buck_converter_with_thermal_model loads + simulates
  through the MCP).
- KB now classifies the harvested LIBRARY by inferred domain, so
  plecs_list_component_types("thermal"|"magnetic") work and describe tags domain.
  Thermal: HeatSink, ThermalResistor, ThermalChain, ConstantTemperature(/Gnd),
  ThermalGround, HeatFlowMeter, SwitchLossCalculator. Magnetic: Transformer,
  MagneticInterface.
- docs/thermal-magnetic-notes.md records the measurement signal names (IGBT/Diode
  "... junction temp", HeatSink "Temperature", HeatFlowMeter "Measured heat flow",
  DCVoltageSource "Source power").
- Offline pytest: 17 passed.

Honest limit: AUTHORING thermal/magnetic models from scratch (loss tables, thermal
port netlist, permeance network) is not yet generated — start from a demo via
plecs_list_templates. Running + reading them works now.

## M6 hardening + evaluations (2026-06-30) — v0.5.0
- eval/evaluation.xml: 10 verifiable tasks (mcp-builder Phase 4), each checked on
  live PLECS (build/sim/sweep/analysis) or offline (KB/templates). eval/README.md.
- CHANGELOG.md (M0–M6), comprehensive README with full tool reference + auto-layout
  authoring example. Version bumped 0.1.0 -> 0.5.0.
- Final verification: 17 offline tests pass; stdio server launches and registers
  all 16 tools (plecs_status/load/close/set/simulate/analyze_waveform/get_waveform/
  plot_waveform/scan_parameter/run_analysis + build/validate/list_component_types/
  describe_component/list_templates/describe_template).

## Status: M0–M6 complete and verified on live PLECS 4.9.5.
Remaining future work (documented honestly): control-block & thermal/magnetic
auto-layout; thermal/magnetic authoring (loss tables, permeance nets); generating
AC-analysis blocks; broader auto-layout (bridges, 3-phase).

## C-Script control (2026-07-01)
- Added CScript to the KB (variable-port block; validation allows any terminal
  index) and Terminal{Output} emission for manual Output components. C-Script code
  sections are ordinary string params (escaped like InitializationCommands).
- Verified end-to-end on live PLECS: minimal CScript computes Output=2*Input=10;
  golden_models/agent_buck_cscript = digital PI (discrete integrator in UpdateFcn,
  ParamRealData/Input/Output/DiscState macros) regulates buck to Vo=15.00 V
  (0.25% overshoot, 7.9 ms), tracks Vref=10 -> 10.00 V. See docs/cscript-notes.md.

## Correction to M5 (honest)
Earlier I wrote M5 "verified domain-agnostic on thermal demo". More precisely: the
thermal demo LOADS and SIMULATES through the MCP without error, but plecs_simulate
returned 0 signals (that demo routes junction temp to a Scope, not an RPC outport),
so reading a thermal quantity back end-to-end is NOT yet verified. The tools are
domain-agnostic in principle; a model that exposes Tj as an outport is needed to
confirm the readout.

## Documentation KB (2026-07-01)
- Source: the LOCAL 4.9.5 manual `onlinehelp/plecshelp.qch` (Qt Help = SQLite),
  so it matches the installed version (online docs are 5.0). Extracted 408 doc
  pages (HTML -> text) via plecs_mcp/docs/extract.py.
- Corpus + index are Plexim copyright -> built locally, gitignored (.docs_cache/);
  only the extractor/search code is committed. (Same choice the reference RAG mcp
  made with its PDF; zotero-mcp likewise indexes the user's own library locally.)
- search.py: stdlib TF-IDF (no heavy deps). Tools: plecs_search_docs,
  plecs_get_doc, plecs_doc_for_component (camelCase-aware exact match).
- Verified: "steady state analysis"->Analysis Tools/AC Sweep; "c-script..."->
  C-Scripts; "thermal junction temp"->Thermal Modeling/Heat Sink; component->doc
  resolves Diode/MOSFET/Inductor/Transfer Function/IGBT/Triangular Wave/Relational.
- Build once: python -m plecs_mcp.docs.extract <plecshelp.qch> .docs_cache

Note: an optional semantic layer (sentence-transformers embeddings, like the RAG
mcp) could improve recall; the stdlib keyword index is the dependency-free default.

## MCP best-practice pass (2026-07-01)
Adopted patterns from well-designed MCPs (MATLAB MCP: resources + static check +
capability detection; mcp-builder: annotations/resources/prompts).
- plecs_capabilities: one-call health/setup report (PLECS online, KB sizes,
  templates dir, docs index, config) — like MATLAB detect_toolboxes.
- plecs_check_spec: offline static validation (unknown types, bad terminals,
  floating electrical terminals, missing source) — like MATLAB check_matlab_code.
- MCP Resources: plecs://components, plecs://conventions/layout,
  plecs://conventions/cscript. MCP Prompts: design_converter, tune_control_loop.
- Tool annotations (readOnly/openWorld hints) on the new tools.
- Verified via stdio: 21 tools, 3 resources, 2 prompts; check_spec flags floating
  terminals offline. Offline pytest: 23 passed.

Roadmap (proposed next): full annotation pass + output schemas on all tools;
an eval runner that executes eval/evaluation.xml on live PLECS; optional semantic
docs layer (embeddings); plecs_simulate_batch (parallel sweeps); structured
logging; subsystem authoring (removes the flat-only control limitation).

## #7 Subsystem authoring (2026-07-01)
The serializer can now emit PLECS `Subsystem` blocks: a component with a
`schematic` = {components, connections} (including inner Input/Output port
components with Index params) is rendered as a Subsystem with external Terminal
blocks (ordered by port Index) + a nested Schematic. Removes the flat-only limit.
- Verified on live PLECS: golden_models/agent_buck_subsystem encapsulates the
  whole voltage controller (Vref/Sum/PI/Saturation/carrier/comparator) in one
  "Controller" block; top level = power stage + Controller. Loads + regulates
  Vo=15.00 V (0.25% overshoot, 7.9 ms). Added `Input` to the KB.
- Offline test verifies the nested-subsystem structure. pytest: 28 passed.

## #8 Thermal readout end-to-end (2026-07-01) — closes the M5 gap
Built a thermal-domain circuit (ConstantTemperatureGnd + HeatFlowMeter +
ThermalResistor + ThermalGround) with `HeatPipe` connections and read a thermal
quantity through the MCP: golden_models/agent_thermal_min gives heat flow =
50.0 W (= 100 C / 2 K/W) on live PLECS. So the M5 "reading a thermal quantity
back" gap is now CLOSED for a purpose-built model. (The remaining gap is only
semiconductor loss data / junction-temp, which needs a thermal description.)
Added verified thermal types (with terminal roles + param Rth) to the KB CORE.
The docs KB proved its worth: found the `Rth` param name instead of guessing.
