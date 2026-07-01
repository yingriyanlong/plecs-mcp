from plecs_mcp.authoring.serializer import serialize
from plecs_mcp.authoring.spec import CircuitSpec


def test_thermal_heatpipe_serializes():
    spec = CircuitSpec(name="t", components=[
        {"type": "ConstantTemperatureGnd", "name": "Thot", "params": {"T": "100"}},
        {"type": "ThermalResistor", "name": "Rth", "params": {"Rth": "2"}},
        {"type": "ThermalGround", "name": "G", "params": {}},
    ], connections=[
        {"kind": "HeatPipe", "src": ["Thot", 1], "dsts": [["Rth", 1]]},
        {"kind": "HeatPipe", "src": ["Rth", 2], "dsts": [["G", 1]]},
    ])
    txt = serialize(spec)
    assert "Type          HeatPipe" in txt
    assert "Type          ThermalResistor" in txt
