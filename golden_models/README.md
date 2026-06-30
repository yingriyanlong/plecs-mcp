# Golden models

Verified `.plecs` models that double as **authoring templates** and
**regression baselines**. Each must load cleanly and simulate to a result that
matches an analytic expectation within tolerance.

| Model | Topology | Check | Status |
|-------|----------|-------|--------|
| `agent_buck.plecs` | Open-loop buck (Vi=24, D=0.5, fs=100k, L=100u, C=100u, R=10) | Vo steady ≈ 12 V (= D·Vi) | ✅ Vo = 11.9985 V on live PLECS 4.7 |

`agent_buck.plecs` was authored from scratch by the agent (not copied from any
sample) to prove the symbolic-connection authoring approach end to end.
