# Changelog

## 0.5.0 (2026-06-30)
Milestones M0–M6 complete and verified on live PLECS 4.9.5.

- **M0 connectivity** — stdio FastMCP server, normalized XML-RPC client,
  `plecs_status`, packaging, `claude mcp add`.
- **M1 run/observe** — load/close/set, `plecs_simulate` (ModelVars/solver
  overrides), result handles, waveform metrics, plotting.
- **M2 authoring** — component KB, pydantic `CircuitSpec`, `.plecs` serializer
  (symbolic connectivity), `plecs_build_model`/`validate`; buck/boost/buck-boost
  built from scratch and verified.
- **M2.5 demo knowledge** — harvested all 89 PLECS demos: 91-type component
  library + template catalog; `plecs_list_templates`/`describe_template`; two-rail
  layout conventions.
- **Auto-layout** — net-analysis two-rail layouter: positions + orthogonal
  `Points` from a pure netlist; clean buck/boost/buck-boost verified.
- **M3 control loops** — flat voltage-mode PI + PWM closed-loop buck
  (Vo=15.00 V, 0.25% overshoot, 7.9 ms); control KB; fixed `plecs.load` stale
  model (close-then-load).
- **M4 scripts & analyses** — `plecs_scan_parameter` (server-side sweep),
  `plecs_run_analysis` (steady-state / AC → bode + phase margin).
- **M5 thermal & magnetic** — domain-classified library; thermal/magnetic
  discoverable; measurement-signal docs; simulate/analyze verified domain-agnostic.
- **M6 hardening** — evaluation suite, docs, changelog.

Honest gaps: control-block and thermal/magnetic auto-layout, and thermal/magnetic
*authoring* (loss tables, permeance nets), are future work — start from a demo
template for those.
