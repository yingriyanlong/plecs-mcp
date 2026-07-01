import json

from plecs_mcp.docs.extract import html_to_text
from plecs_mcp.docs.search import DocIndex


def test_html_to_text():
    title, text = html_to_text("<html><head><title>MOSFET</title></head>"
                               "<body><p>Ideal MOSFET with on-resistance.</p></body></html>")
    assert title == "MOSFET"
    assert "on-resistance" in text


def _corpus(tmp):
    (tmp / "pages").mkdir()
    (tmp / "pages" / "mosfet.txt").write_text(
        "MOSFET\n\nIdeal MOSFET with on-resistance Ron and thermal ports.", encoding="utf-8")
    (tmp / "pages" / "diode.txt").write_text(
        "Diode\n\nIdeal diode with forward voltage Vf.", encoding="utf-8")
    idx = [{"name": "mosfet", "title": "MOSFET", "chars": 50, "summary": "Ideal MOSFET"},
           {"name": "diode", "title": "Diode", "chars": 40, "summary": "Ideal diode"}]
    (tmp / "docs_index.json").write_text(json.dumps(idx), encoding="utf-8")


def test_docindex_search(tmp_path):
    _corpus(tmp_path)
    di = DocIndex(str(tmp_path))
    res = di.search("on-resistance ron", top_k=1)
    assert res and res[0]["name"] == "mosfet"
    assert di.get("diode")["title"] == "Diode"
