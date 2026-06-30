from plecs_mcp.authoring.kb import describe, known_types


def test_control_types_in_core():
    s = describe("Sum")
    assert s["source"] == "core" and s["terminals"][1] == "out"
    tf = describe("TransferFunction")
    assert tf["source"] == "core" and set(tf["terminals"].values()) == {"in", "out"}
    ro = describe("RelationalOperator")
    assert ro["terminals"][3] == "out"


def test_control_domain_listing():
    ctrl = known_types("control")
    for t in ("Sum", "Gain", "TransferFunction", "Saturation",
              "RelationalOperator", "TriangleGenerator", "Constant"):
        assert t in ctrl
