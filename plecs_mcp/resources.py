"""MCP resources + prompts for plecs-mcp.

Resources let clients browse reference material without a tool call; prompts are
reusable guided workflows. (Patterns adopted from well-designed MCP servers such
as the MATLAB MCP, which exposes coding-guideline resources.)
"""
from __future__ import annotations

from pathlib import Path

_DOCS = Path(__file__).resolve().parents[1] / "docs"


def register_resources_and_prompts(mcp) -> None:
    from .authoring.kb import CORE, LIBRARY, known_types

    @mcp.resource("plecs://components", mime_type="text/markdown")
    def components_resource() -> str:
        """The component types plecs-mcp can author/validate, grouped by domain."""
        out = ["# plecs-mcp component types", "",
               f"{len(CORE)} curated (with terminal roles) + {len(LIBRARY)} harvested.", ""]
        for dom in ["electrical", "control", "measurement", "thermal", "magnetic", "io"]:
            ts = known_types(dom)
            if ts:
                out.append(f"## {dom} ({len(ts)})\n" + ", ".join(ts) + "\n")
        return "\n".join(out)

    def _doc(fname: str, fallback: str) -> str:
        f = _DOCS / fname
        return f.read_text(encoding="utf-8") if f.exists() else fallback

    @mcp.resource("plecs://conventions/layout", mime_type="text/markdown")
    def layout_conventions() -> str:
        """Two-rail layout conventions used by the auto-layouter."""
        return _doc("plecs-layout-conventions.md", "See docs/plecs-layout-conventions.md")

    @mcp.resource("plecs://conventions/cscript", mime_type="text/markdown")
    def cscript_conventions() -> str:
        """C-Script component structure + code macros, with a verified PI example."""
        return _doc("cscript-notes.md", "See docs/cscript-notes.md")

    @mcp.prompt()
    def design_converter(topology: str = "buck", vin: str = "24", vout: str = "12",
                         fsw: str = "100e3") -> str:
        """Guided workflow to design and verify a converter."""
        return (
            f"Design and verify a {topology} converter in PLECS: Vin={vin} V, "
            f"Vout={vout} V, switching frequency {fsw} Hz.\n"
            "1) plecs_status / plecs_capabilities to confirm setup.\n"
            "2) Choose parts via plecs_list_component_types; for any you're unsure about, "
            "read plecs_doc_for_component.\n"
            "3) plecs_check_spec, then plecs_build_model (omit coordinates for auto-layout).\n"
            "4) plecs_simulate + plecs_analyze_waveform; confirm the output ~ target.\n"
            "5) If closed-loop is wanted, add a PI or C-Script controller and tune.\n"
            "Report the steady-state output and key metrics."
        )

    @mcp.prompt()
    def tune_control_loop() -> str:
        """Guided workflow to tune a control loop with sweeps + AC analysis."""
        return (
            "Tune the control loop of the loaded PLECS model.\n"
            "- plecs_scan_parameter to sweep controller gains (Kp, Ki).\n"
            "- plecs_analyze_waveform for overshoot / settling_time.\n"
            "- plecs_run_analysis (AC) for gain-crossover and phase margin.\n"
            "Aim for a stable response with adequate phase margin (>45 deg); "
            "report the chosen gains and the resulting metrics."
        )
