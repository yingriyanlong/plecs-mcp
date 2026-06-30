# Evaluation set

10 realistic, verifiable tasks for plecs-mcp, following the mcp-builder Phase-4
guidance. Each answer was checked on live PLECS 4.9.5 (RPC port 1080) using the
MCP tools.

- Items 1–6 and 9 require a **live PLECS** connection (build/simulate/analyze).
- Items 7, 8, 10 are offline (knowledge base / demo-template catalog).

To run an item, drive the corresponding tools (`plecs_build_model`,
`plecs_simulate`, `plecs_scan_parameter`, `plecs_run_analysis`,
`plecs_list_templates`, `plecs_describe_component`) and compare the result to the
expected answer in `evaluation.xml`.
