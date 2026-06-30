from plecs_mcp.authoring.layout import auto_layout
from plecs_mcp.authoring.spec import CircuitSpec


def _buck():
    return CircuitSpec(name="t", components=[
        {"type": "DCVoltageSource", "name": "VDCin", "params": {"V": "24"}},
        {"type": "Inductor", "name": "L1", "params": {"L": "1e-4"}},
        {"type": "Mosfet", "name": "FET1", "params": {"Ron": "1e-3"}},
        {"type": "Diode", "name": "D1", "params": {}},
        {"type": "Capacitor", "name": "C1", "params": {"C": "1e-4"}},
        {"type": "Resistor", "name": "R1", "params": {"R": "10"}},
    ], connections=[
        {"kind": "Wire", "src": ["VDCin", 1], "dsts": [["FET1", 1]]},
        {"kind": "Wire", "src": ["FET1", 2], "dsts": [["L1", 1], ["D1", 2]]},
        {"kind": "Wire", "src": ["L1", 2], "dsts": [["C1", 1], ["R1", 1]]},
        {"kind": "Wire", "src": ["C1", 2], "dsts": [["R1", 2], ["VDCin", 2], ["D1", 1]]},
    ])


def test_auto_layout_assigns_positions_and_points():
    s = auto_layout(_buck())
    assert all(c.position is not None for c in s.components)
    assert any(getattr(c, "points", None) for c in s.connections if c.kind == "Wire")
    ys = {c.position[1] for c in s.components}
    assert ys & {95, 140}  # uses the two-rail grid


def test_source_placed_leftmost():
    s = auto_layout(_buck())
    src = next(c for c in s.components if c.name == "VDCin")
    others = [c.position[0] for c in s.components if c.name != "VDCin" and c.position]
    assert src.position[0] <= min(others)
