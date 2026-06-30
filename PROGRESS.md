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
