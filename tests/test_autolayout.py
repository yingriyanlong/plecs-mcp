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


def _closed_loop():
    # buck + a signal-flow control chain (Vref -> Err -> Gain -> gate)
    return CircuitSpec(name="cl", components=[
        {"type": "DCVoltageSource", "name": "V", "params": {"V": "24"}},
        {"type": "Mosfet", "name": "Q", "params": {"Ron": "1e-3"}},
        {"type": "Diode", "name": "D", "params": {}},
        {"type": "Inductor", "name": "L", "params": {"L": "1e-4"}},
        {"type": "Capacitor", "name": "C", "params": {"C": "1e-4"}},
        {"type": "Resistor", "name": "R", "params": {"R": "10"}},
        {"type": "Voltmeter", "name": "Vm", "params": {}},
        {"type": "Constant", "name": "Ref", "params": {"Value": "15"}},
        {"type": "Sum", "name": "Err", "params": {"Inputs": "|+-"}},
        {"type": "Gain", "name": "K", "params": {"K": "0.1"}},
    ], connections=[
        {"kind": "Wire", "src": ["V", 1], "dsts": [["Q", 1]]},
        {"kind": "Wire", "src": ["Q", 2], "dsts": [["L", 1], ["D", 2]]},
        {"kind": "Wire", "src": ["L", 2], "dsts": [["C", 1], ["R", 1], ["Vm", 1]]},
        {"kind": "Wire", "src": ["C", 2], "dsts": [["R", 2], ["V", 2], ["D", 1], ["Vm", 2]]},
        {"kind": "Signal", "src": ["Ref", 1], "dsts": [["Err", 2]]},
        {"kind": "Signal", "src": ["Vm", 3], "dsts": [["Err", 3]]},
        {"kind": "Signal", "src": ["Err", 1], "dsts": [["K", 1]]},
        {"kind": "Signal", "src": ["K", 2], "dsts": [["Q", 3]]},
    ])


def test_control_blocks_on_dedicated_rail_in_flow_order():
    s = auto_layout(_closed_loop())
    pos = {c.name: c.position for c in s.components}
    # control/signal blocks sit on a rail below the power stage (y>=260)...
    for n in ("Ref", "Err", "K"):
        assert pos[n][1] >= 260, f"{n} not on the control rail: {pos[n]}"
    # ...power devices stay on the two-rail grid (y in {95,140,185})
    for n in ("V", "Q", "L", "C", "R"):
        assert pos[n][1] <= 185, f"{n} pushed off the power rails: {pos[n]}"
    # signal-flow order left-to-right: Ref -> Err -> K
    assert pos["Ref"][0] < pos["Err"][0] < pos["K"][0]
    # no two components share a center
    centers = [tuple(c.position) for c in s.components if c.position]
    assert len(set(centers)) == len(centers)
