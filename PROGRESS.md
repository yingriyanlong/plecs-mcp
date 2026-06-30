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
