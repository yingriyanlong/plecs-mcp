"""Component knowledge base.

Maps each PLECS ``Type`` to its terminal indices (index -> role) and parameter
names/defaults. Terminal indices were verified against live PLECS 4.7 via the
``agent_buck`` golden model. This grounds the authoring engine so generated
circuits use correct terminals (which is what determines electrical
connectivity, since wiring is symbolic).
"""
from __future__ import annotations

KB: dict[str, dict] = {
    "DCVoltageSource": {"domain": "electrical", "terminals": {1: "+", 2: "-"}, "params": {"V": "0"}},
    "DCCurrentSource": {"domain": "electrical", "terminals": {1: "+", 2: "-"}, "params": {"I": "0"}},
    "Resistor": {"domain": "electrical", "terminals": {1: "a", 2: "b"}, "params": {"R": "1"}},
    "Inductor": {"domain": "electrical", "terminals": {1: "a", 2: "b"}, "params": {"L": "1e-3", "i_init": "0"}},
    "Capacitor": {"domain": "electrical", "terminals": {1: "a", 2: "b"}, "params": {"C": "1e-6", "v_init": "0"}},
    "Mosfet": {"domain": "electrical", "terminals": {1: "drain", 2: "source", 3: "gate"}, "params": {"Ron": "1e-3"}},
    "Diode": {"domain": "electrical", "terminals": {1: "anode", 2: "cathode"}, "params": {"Vf": "0", "Ron": "1e-3"}},
    "Ground": {"domain": "electrical", "terminals": {1: "gnd"}, "params": {}},
    "PulseGenerator": {"domain": "control", "terminals": {1: "out"},
                        "params": {"Hi": "1", "Lo": "0", "f": "1e3", "DutyCycle": "0.5",
                                   "Delay": "0", "DataType": "10"}},
    "PlecsProbe": {"domain": "measurement", "terminals": {1: "out"}, "params": {}},
    "Output": {"domain": "io", "terminals": {1: "in"}, "params": {"Index": "1", "Width": "-1"}},
}


def known_types(domain: str | None = None) -> list[str]:
    if domain:
        return sorted(t for t, v in KB.items() if v.get("domain") == domain)
    return sorted(KB)


def describe(type_name: str) -> dict | None:
    return KB.get(type_name)


def validate_spec(spec) -> list[str]:
    """Return a list of human-readable problems; empty means the spec is sound."""
    errs: list[str] = []
    names = {c.name for c in spec.components}
    for c in spec.components:
        if c.type not in KB:
            errs.append(f"unknown component type '{c.type}' (component {c.name})")
    for i, conn in enumerate(spec.connections):
        for ref in [conn.src, *conn.dsts]:
            cname, term = ref[0], int(ref[1])
            comp = next((c for c in spec.components if c.name == cname), None)
            if comp is None:
                errs.append(f"connection {i}: unknown component '{cname}'")
                continue
            terms = KB.get(comp.type, {}).get("terminals", {})
            if term not in terms:
                errs.append(
                    f"connection {i}: terminal {term} invalid for {comp.type} "
                    f"'{cname}' (valid: {sorted(terms)})"
                )
    for o in spec.outputs:
        if o.probe_component not in names:
            errs.append(f"output {o.name}: probe_component '{o.probe_component}' not in circuit")
    return errs
