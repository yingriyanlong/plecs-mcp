"""Authoring logic + MCP tool registration.

Core functions are module-level (callable from tests/other code); the MCP tools
are thin wrappers registered onto the FastMCP instance.
"""
from __future__ import annotations

import os
import tempfile

from mcp.types import ToolAnnotations

from ..rpc import client
from . import templates
from .kb import describe as kb_describe
from .kb import known_types, validate_spec
from .layout import auto_layout
from .serializer import serialize
from .spec import CircuitSpec


def list_types(domain: str | None = None) -> dict:
    return {"types": known_types(domain)}


def describe_type(type_name: str) -> dict:
    d = kb_describe(type_name)
    if not d:
        return {"ok": False, "error": f"unknown type '{type_name}'; see plecs_list_component_types"}
    return {"ok": True, "type": type_name, **d}


def build_model(spec: dict, out_dir: str | None = None, load: bool = True,
                layout: str | None = None, thermal: list | None = None) -> dict:
    try:
        s = CircuitSpec(**spec)
    except Exception as e:
        return {"ok": False, "error": f"invalid spec: {e}"}
    errs = validate_spec(s)
    if errs:
        return {"ok": False, "errors": errs}
    # auto-layout when requested, or by default when no coordinates were given
    auto = (layout == "auto") or (layout is None and all(c.position is None for c in s.components))
    if auto:
        try:
            s = auto_layout(s)
        except Exception as e:
            return {"ok": False, "error": f"auto-layout failed: {e}; pass explicit positions or layout='manual'"}
    # attach heat sinks + loss datasheets for thermal devices (needs positions)
    loss_files: list = []
    if thermal:
        from .thermal import attach_heatsink
        try:
            s, loss_files = attach_heatsink(s, thermal)
        except Exception as e:
            return {"ok": False, "error": f"thermal attach failed: {e}"}
    text = serialize(s)
    d = out_dir or os.environ.get("PLECS_MCP_MODEL_DIR", tempfile.gettempdir())
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{s.name}.plecs")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    # loss datasheets live in the model's <name>_plecs/ resource folder
    if loss_files:
        resdir = os.path.join(d, f"{s.name}_plecs")
        os.makedirs(resdir, exist_ok=True)
        for nm, xml in loss_files:
            with open(os.path.join(resdir, f"{nm}.xml"), "w", encoding="utf-8") as f:
                f.write(xml)
    res: dict = {"ok": True, "model_name": s.name, "path": path,
                 "n_components": len(s.components), "n_connections": len(s.connections),
                 "thermal_devices": [nm for nm, _ in loss_files]}
    if load:
        try:
            client.load(path)
            res["loaded"] = True
        except Exception as e:
            res["loaded"] = False
            res["load_error"] = str(e)[:200]
    return res


def validate_model(model_path: str) -> dict:
    if not os.path.isfile(model_path):
        return {"ok": False, "error": f"file not found: {model_path}"}
    try:
        client.load(model_path)
        return {"ok": True, "loaded": True, "path": model_path}
    except Exception as e:
        return {"ok": True, "loaded": False, "error": str(e)[:200]}


def register_authoring_tools(mcp) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True))
    def plecs_list_component_types(domain: str | None = None) -> dict:
        """List known component types (curated core + full demo-harvested library).
        Optional domain filter for core: electrical, control, measurement, io."""
        return list_types(domain)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True))
    def plecs_describe_component(type_name: str) -> dict:
        """Return terminal map/count and parameters for a component type. Core
        types include terminal ROLES (drain/source/gate); library types (from the
        PLECS demos) include terminal count + parameter names."""
        return describe_type(type_name)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True, idempotentHint=False))
    def plecs_build_model(spec: dict, out_dir: str | None = None, load: bool = True,
                          layout: str | None = None, thermal: list | None = None) -> dict:
        """Build a .plecs model from a structured spec, write it, and (by default)
        load it into PLECS to validate.

        Spec: {name, init, time_span, components: [{type, name, params, position,
        direction, flipped}], connections: [{kind: "Wire"|"Signal", src: [name,
        term], points: [[x,y],...], dsts: [[name, term] | [name, term, [[x,y]]]]}],
        outputs: [{name, probe_component, probe_signal, index, position}]}.
        Connectivity is symbolic (component name + terminal index). Omit positions to get
        automatic two-rail layout (layout='manual' to keep your coordinates).

        thermal: optional list to make semiconductors lossy and read junction
        temperature. Each entry {name: <device in spec>, sclass: 'MOSFET'|'IGBT'|
        'Diode', ron, eon_mJ, eoff_mJ, rth, cth, v_test, i_max, rth_sink, t_amb}.
        Each device is placed on a generated Heat Sink (required by PLECS to compute
        losses) wired to an ambient network; a loss datasheet XML is written to
        <name>_plecs/, and Tj + dissipated-power probes are added automatically."""
        return build_model(spec, out_dir=out_dir, load=load, layout=layout, thermal=thermal)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, openWorldHint=True, idempotentHint=True))
    def plecs_validate_model(model_path: str) -> dict:
        """Load a .plecs file in PLECS and report whether it loads cleanly."""
        return validate_model(model_path)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True))
    def plecs_list_templates(query: str | None = None) -> dict:
        """List reference topologies from the bundled PLECS demos (89 models) —
        the gold standard for layout. Filter by name or component type (e.g.
        'buck', 'flyback', 'inverter', 'thermal'). Set PLECS_DEMOS_DIR to resolve
        absolute paths, then load one with plecs_load_model."""
        return templates.list_templates(query)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True))
    def plecs_describe_template(name: str) -> dict:
        """Return a demo template's relative/absolute path and component types,
        so it can be loaded as a clean starting point or studied for layout."""
        return templates.describe_template(name)
