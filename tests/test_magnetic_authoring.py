"""Offline tests for magnetic permeance-network authoring.

Live-PLECS behaviour is verified manually (single winding on a permeance loop
gives L = n^2*P = 0.0996 H; a 2-winding shared-core transformer gives
V2/V1 = n2/n1 = 0.5000). These cover the generation logic: KB entries, the
"Magnetic" connection kind serializing, and a full magnetic spec validating +
serializing.
"""
from plecs_mcp.authoring.kb import describe, known_types, validate_spec
from plecs_mcp.authoring.serializer import serialize
from plecs_mcp.authoring.spec import CircuitSpec
from plecs_mcp.authoring.tools import build_model


def test_magnetic_kb_entries():
    mi = describe("MagneticInterface")
    assert mi["source"] == "core" and mi["domain"] == "magnetic"
    # winding: 1,2 electrical + 3,4 magnetic
    assert set(mi["terminals"]) == {1, 2, 3, 4}
    assert describe("MagneticPermeance")["terminals"] == {1: "a", 2: "b"}
    assert describe("ACVoltageSource")["domain"] == "electrical"
    for t in ("MagneticInterface", "MagneticPermeance", "MagneticResistance"):
        assert t in known_types("magnetic")


def _inductor_spec():
    return {
        "name": "ind", "init": "n=10;\nP=1e-3;", "time_span": "1e-3",
        "components": [
            {"type": "DCVoltageSource", "name": "V1", "params": {"V": "10"}, "position": [100, 180]},
            {"type": "MagneticInterface", "name": "W1", "params": {"n": "n"}, "position": [300, 180]},
            {"type": "MagneticPermeance", "name": "Pc", "params": {"P": "P"}, "position": [460, 180]},
        ],
        "connections": [
            {"kind": "Wire", "src": ["V1", 1], "dsts": [["W1", 1]]},
            {"kind": "Wire", "src": ["W1", 2], "dsts": [["V1", 2]]},
            {"kind": "Magnetic", "src": ["W1", 3], "dsts": [["Pc", 1]]},
            {"kind": "Magnetic", "src": ["W1", 4], "dsts": [["Pc", 2]]},
        ],
    }


def test_magnetic_connection_serializes():
    s = CircuitSpec(**_inductor_spec())
    assert validate_spec(s) == []  # magnetic terminals 3/4 + "Magnetic" kind accepted
    text = serialize(s)
    assert "Type          Magnetic" in text
    assert "Type          MagneticInterface" in text
    assert "Type          MagneticPermeance" in text


def test_build_magnetic_no_load(tmp_path):
    # build without touching PLECS: writes a .plecs with the magnetic net intact
    res = build_model(_inductor_spec(), out_dir=str(tmp_path), load=False, layout="manual")
    assert res["ok"] and res["n_connections"] == 4
    text = (tmp_path / "ind.plecs").read_text(encoding="utf-8")
    assert text.count("Type          Magnetic\n") == 2
