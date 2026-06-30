"""Authoring logic + MCP tool registration.

Core functions are module-level (callable from tests and other code); the MCP
tools are thin wrappers registered onto the FastMCP instance.
"""
from __future__ import annotations

import os
import tempfile

from ..rpc import client
from .kb import describe as kb_describe
from .kb import known_types, validate_spec
from .serializer import serialize
from .spec import CircuitSpec


def list_types(domain: str | None = None) -> dict:
    return {"types": known_types(domain)}


def describe_type(type_name: str) -> dict:
    d = kb_describe(type_name)
    if not d:
        return {"ok": False, "error": f"unknown type '{type_name}'; see plecs_list_component_types"}
    return {"ok": True, "type": type_name, **d}


def build_model(spec: dict, out_dir: str | None = None, load: bool = True) -> dict:
    try:
        s = CircuitSpec(**spec)
    except Exception as e:
        return {"ok": False, "error": f"invalid spec: {e}"}
    errs = validate_spec(s)
    if errs:
        return {"ok": False, "errors": errs}
    text = serialize(s)
    d = out_dir or os.environ.get("PLECS_MCP_MODEL_DIR", tempfile.gettempdir())
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{s.name}.plecs")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    res: dict = {"ok": True, "model_name": s.name, "path": path,
                 "n_components": len(s.components), "n_connections": len(s.connections)}
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
    @mcp.tool()
    def plecs_list_component_types(domain: str | None = None) -> dict:
        """List component types in the knowledge base. Optional domain filter:
        electrical, control, measurement, io."""
        return list_types(domain)

    @mcp.tool()
    def plecs_describe_component(type_name: str) -> dict:
        """Return the terminal map (index -> role) and parameters for a component
        type, so connections use correct terminal indices."""
        return describe_type(type_name)

    @mcp.tool()
    def plecs_build_model(spec: dict, out_dir: str | None = None, load: bool = True) -> dict:
        """Build a .plecs model from a structured spec, write it to disk, and
        (by default) load it into PLECS to validate.

        Spec shape: {name, init (InitializationCommands string), time_span,
        components: [{type, name, params}], connections:
        [{kind: "Wire"|"Signal", src: [name, terminal], dsts: [[name, terminal], ...]}],
        outputs: [{name, probe_component, probe_signal, index}]}.
        Connectivity is symbolic; use plecs_describe_component for terminal numbering.
        """
        return build_model(spec, out_dir=out_dir, load=load)

    @mcp.tool()
    def plecs_validate_model(model_path: str) -> dict:
        """Load a .plecs file in PLECS and report whether it loads cleanly
        (catches connectivity / parameter errors)."""
        return validate_model(model_path)
