from plecs_mcp.authoring.kb import describe, known_types


def test_thermal_listing():
    th = known_types("thermal")
    for t in ("HeatSink", "ThermalResistor", "ConstantTemperature", "HeatFlowMeter"):
        assert t in th


def test_magnetic_listing():
    assert "Transformer" in known_types("magnetic")


def test_describe_library_domain():
    d = describe("ThermalChain")  # library-only thermal type
    assert d["source"] == "library" and d["domain"] == "thermal"
    assert d["terminals"] == 2


def test_heatsink_is_core_thermal():
    # HeatSink was promoted to the curated core (it needs a HeatPort terminal +
    # Frame to author semiconductor thermal models).
    d = describe("HeatSink")
    assert d["source"] == "core" and d["domain"] == "thermal"
