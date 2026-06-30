# Golden models

Verified `.plecs` models that double as **authoring templates** and
**regression baselines**. Each must load cleanly and simulate to a result that
matches an analytic expectation within tolerance. The `agent_*` models were
authored from scratch by the MCP authoring engine (`plecs_build_model`), not
copied from any sample.

| Model | Topology | Check | Result (live PLECS 4.7) |
|-------|----------|-------|--------------------------|
| `agent_buck.plecs` | Open-loop buck (Vi=24, D=0.5) | Vo ≈ D·Vi = 12 | ✅ 11.9985 V |
| `agent_boost.plecs` | Open-loop boost (Vi=24, D=0.5) | Vo ≈ Vi/(1−D) = 48 | ✅ 48.019 V |
| `agent_buckboost.plecs` | Inverting buck-boost (Vi=24, D=0.5) | Vo ≈ −Vi·D/(1−D) = −24 | ✅ −24.071 V |

Regenerate any of these with `plecs_build_model` (see
`docs/development-plan.md` and the M2 entry in `PROGRESS.md`).

**Layout note:** `agent_boost` uses the two-rail demo-grade layout
(see `docs/plecs-layout-conventions.md`); `agent_buck` is hand-authored and tidy;
`agent_buckboost` is electrically verified but its layout is not yet demo-grade
(tracked in PROGRESS.md).
