from plecs_mcp.authoring.serializer import serialize
from plecs_mcp.authoring.spec import CircuitSpec


def test_subsystem_serializes_nested_schematic():
    sub = {"components": [
        {"type": "Input", "name": "in1", "params": {"Index": "1"}},
        {"type": "Gain", "name": "G", "params": {"K": "2"}},
        {"type": "Output", "name": "out1", "params": {"Index": "2"}},
    ], "connections": [
        {"kind": "Signal", "src": ["in1", 1], "dsts": [["G", 1]]},
        {"kind": "Signal", "src": ["G", 2], "dsts": [["out1", 1]]},
    ]}
    spec = CircuitSpec(name="t",
                       components=[{"type": "Subsystem", "name": "Sub", "schematic": sub}],
                       connections=[])
    txt = serialize(spec)
    assert "Type          Subsystem" in txt
    # 2 external terminals (Input + Output) + nested port components
    assert txt.count("Type          Input") >= 2 and txt.count("Type          Output") >= 2
    assert "Type          Gain" in txt  # inner logic is nested
