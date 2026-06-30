from plecs_mcp.authoring.kb import validate_spec
from plecs_mcp.authoring.serializer import serialize
from plecs_mcp.authoring.spec import CircuitSpec


def _spec(**over):
    base = dict(
        name="t",
        init="Vi=1;",
        components=[
            {"type": "DCVoltageSource", "name": "V1", "params": {"V": "Vi"}},
            {"type": "Resistor", "name": "R1", "params": {"R": "1"}},
        ],
        connections=[
            {"kind": "Wire", "src": ["V1", 1], "dsts": [["R1", 1]]},
            {"kind": "Wire", "src": ["V1", 2], "dsts": [["R1", 2]]},
        ],
    )
    base.update(over)
    return CircuitSpec(**base)


def test_serialize_contains_components():
    txt = serialize(_spec())
    assert 'Name          "t"' in txt
    assert "Type          DCVoltageSource" in txt
    assert "Type          Resistor" in txt
    assert 'SrcComponent  "V1"' in txt
    assert txt.strip().endswith("}")


def test_validate_catches_bad_terminal():
    s = _spec(connections=[{"kind": "Wire", "src": ["V1", 9], "dsts": [["R1", 1]]}])
    errs = validate_spec(s)
    assert any("terminal 9 invalid" in e for e in errs)


def test_validate_catches_unknown_type():
    s = _spec(components=[{"type": "Nonsense", "name": "X"}])
    errs = validate_spec(s)
    assert any("unknown component type" in e for e in errs)
