"""Component knowledge base.

Two layers:
- CORE: curated electrical/control parts with verified terminal ROLES
  (index -> drain/source/gate ...), used by the authoring engine to place and
  wire circuits. Terminal indices verified against live PLECS 4.7.
- LIBRARY: the full set of component types + parameters + terminal counts
  harvested from the 89 bundled PLECS demos (reference/harvested_components.json).
  Gives describe/list/validate coverage for ~90 types beyond the curated core.
"""
from __future__ import annotations

import json
from pathlib import Path

_REF = Path(__file__).resolve().parent / "reference"

CORE: dict[str, dict] = {
    "DCVoltageSource": {"domain": "electrical", "terminals": {1: "+", 2: "-"}, "params": {"V": "0"}},
    "DCCurrentSource": {"domain": "electrical", "terminals": {1: "+", 2: "-"}, "params": {"I": "0"}},
    "Resistor": {"domain": "electrical", "terminals": {1: "a", 2: "b"}, "params": {"R": "1"}},
    "Inductor": {"domain": "electrical", "terminals": {1: "a", 2: "b"}, "params": {"L": "1e-3", "i_init": "0"}},
    "Capacitor": {"domain": "electrical", "terminals": {1: "a", 2: "b"}, "params": {"C": "1e-6", "v_init": "0"}},
    "Mosfet": {"domain": "electrical", "terminals": {1: "drain", 2: "source", 3: "gate"}, "params": {"Ron": "1e-3"}},
    "Diode": {"domain": "electrical", "terminals": {1: "anode", 2: "cathode"}, "params": {"Vf": "0", "Ron": "1e-3"}},
    "Igbt": {"domain": "electrical", "terminals": {1: "collector", 2: "emitter", 3: "gate"}, "params": {"Vf": "0", "Ron": "1e-3"}},
    "Voltmeter": {"domain": "measurement", "terminals": {1: "+", 2: "-", 3: "out"}, "params": {}},
    "Ammeter": {"domain": "measurement", "terminals": {1: "in", 2: "out", 3: "signal"}, "params": {}},
    "Ground": {"domain": "electrical", "terminals": {1: "gnd"}, "params": {}},
    "PulseGenerator": {"domain": "control", "terminals": {1: "out"},
                        "params": {"Hi": "1", "Lo": "0", "f": "1e3", "DutyCycle": "0.5", "Delay": "0", "DataType": "10"}},
    "Constant": {"domain": "control", "terminals": {1: "out"}, "params": {"Value": "0", "DataType": "10"}},
    "Gain": {"domain": "control", "terminals": {1: "in", 2: "out"}, "params": {"K": "1"}},
    "Sum": {"domain": "control", "terminals": {1: "in1", 2: "in2", 3: "out"}, "params": {"Inputs": "+-"}},
    "Step": {"domain": "control", "terminals": {1: "out"}, "params": {"Time": "0", "Before": "0", "After": "1"}},
    "Sum": {"domain": "control", "terminals": {1: "out", 2: "in+", 3: "in-"}, "params": {"Inputs": "|+-"}},
    "TransferFunction": {"domain": "control", "terminals": {1: "in", 2: "out"}, "params": {"Numerator": "[1]", "Denominator": "[1]", "X0": "0"}},
    "Saturation": {"domain": "control", "terminals": {1: "in", 2: "out"}, "params": {"UpperLimit": "1", "LowerLimit": "0"}},
    "RelationalOperator": {"domain": "control", "terminals": {1: "in1", 2: "in2", 3: "out"}, "params": {"Operator": "6"}},
    "TriangleGenerator": {"domain": "control", "terminals": {1: "out"}, "params": {"Min": "0", "Max": "1", "f": "1e3", "DutyCycle": "0.5"}},
    "PlecsProbe": {"domain": "measurement", "terminals": {1: "out"}, "params": {}},
    "Output": {"domain": "io", "terminals": {1: "in"}, "params": {"Index": "1", "Width": "-1"}},
}

# Backwards-compatible alias used elsewhere.
KB = CORE


def _load_library() -> dict:
    f = _REF / "harvested_components.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


LIBRARY = _load_library()


def known_types(domain: str | None = None) -> list[str]:
    if domain:
        return sorted(t for t, v in CORE.items() if v.get("domain") == domain)
    return sorted(set(CORE) | set(LIBRARY))


def describe(type_name: str) -> dict | None:
    if type_name in CORE:
        c = CORE[type_name]
        return {"source": "core", "domain": c.get("domain"),
                "terminals": c["terminals"], "params": c["params"]}
    if type_name in LIBRARY:
        lib = LIBRARY[type_name]
        return {"source": "library", "terminals": lib.get("terminals"),
                "params": lib.get("params", []), "seen_in_demos": lib.get("count")}
    return None


def _terminal_ok(type_name: str, term: int) -> bool:
    if type_name in CORE:
        return term in CORE[type_name]["terminals"]
    if type_name in LIBRARY:
        n = LIBRARY[type_name].get("terminals", 0)
        return (1 <= term <= n) if n else True
    return False


def validate_spec(spec) -> list[str]:
    errs: list[str] = []
    names = {c.name for c in spec.components}
    known = set(CORE) | set(LIBRARY)
    for c in spec.components:
        if c.type not in known:
            errs.append(f"unknown component type '{c.type}' (component {c.name}); see plecs_list_component_types")
    for i, conn in enumerate(spec.connections):
        for ref in [conn.src, *conn.dsts]:
            cname, term = ref[0], int(ref[1])
            comp = next((c for c in spec.components if c.name == cname), None)
            if comp is None:
                errs.append(f"connection {i}: unknown component '{cname}'")
                continue
            if not _terminal_ok(comp.type, term):
                errs.append(f"connection {i}: terminal {term} invalid for {comp.type} '{cname}'")
    for o in spec.outputs:
        if o.probe_component not in names:
            errs.append(f"output {o.name}: probe_component '{o.probe_component}' not in circuit")
    return errs
