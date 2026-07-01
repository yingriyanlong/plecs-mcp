from plecs_mcp.authoring.kb import describe, validate_spec
from plecs_mcp.authoring.spec import CircuitSpec


def test_cscript_in_kb():
    d = describe("CScript")
    assert d["source"] == "core" and d["domain"] == "control"


def test_variable_terminals_allowed():
    # CScript has a variable number of ports; validation must not reject high indices.
    s = CircuitSpec(name="t", components=[
        {"type": "CScript", "name": "CS", "params": {"NumInputs": "2", "NumOutputs": "1"}},
        {"type": "Constant", "name": "K", "params": {}},
    ], connections=[
        {"kind": "Signal", "src": ["K", 1], "dsts": [["CS", 3]]},
    ])
    assert not any("terminal 3 invalid" in e for e in validate_spec(s))
