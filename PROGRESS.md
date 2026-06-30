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
- PLECS 4.7, Windows, RPC port 1080. gh CLI authed as `yingriyanlong`
  (call by full path `<git-cli>\gh.exe` until app PATH refresh).

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
