from plecs_mcp.authoring import templates
from plecs_mcp.authoring.kb import LIBRARY, describe, known_types


def test_library_loaded():
    # Harvested from the PLECS demos; should cover many types.
    assert len(LIBRARY) > 50
    assert "Inductor" in known_types()


def test_describe_core_vs_library():
    core = describe("Mosfet")
    assert core["source"] == "core" and 3 in core["terminals"]
    lib = describe("Scope")
    assert lib and lib["source"] == "library"


def test_template_catalog():
    out = templates.list_templates("boost")
    assert out["count"] >= 1
    names = [t["name"] for t in out["templates"]]
    assert any("boost" in n for n in names)
