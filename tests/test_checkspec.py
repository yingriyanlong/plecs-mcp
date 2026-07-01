from plecs_mcp import server


def test_check_spec_flags_floating_and_ok():
    spec = {"name": "t",
            "components": [{"type": "DCVoltageSource", "name": "V1", "params": {"V": "10"}},
                           {"type": "Resistor", "name": "R1", "params": {"R": "5"}}],
            "connections": [{"kind": "Wire", "src": ["V1", 1], "dsts": [["R1", 1]]}]}
    r = server.plecs_check_spec(spec)
    assert r["ok"] is True
    assert any("floating" in w for w in r["warnings"])


def test_check_spec_reports_errors():
    spec = {"name": "t", "components": [{"type": "Nonsense", "name": "X"}], "connections": []}
    r = server.plecs_check_spec(spec)
    assert r["ok"] is False and r["errors"]
    assert any("no source" in w for w in r["warnings"])
