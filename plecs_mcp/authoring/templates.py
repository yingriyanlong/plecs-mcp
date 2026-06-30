"""Reference-topology catalog harvested from the bundled PLECS demos.

89 official Plexim demo models (reference/demo_catalog.json) — the gold standard
for layout. For a standard converter, starting from a demo gives a perfectly
laid-out model. Set PLECS_DEMOS_DIR to your PLECS install's `demos` folder to
resolve absolute paths.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_REF = Path(__file__).resolve().parent / "reference"


def _load() -> list:
    f = _REF / "demo_catalog.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


CATALOG = _load()


def demos_root() -> str:
    return os.environ.get("PLECS_DEMOS_DIR", "")


def list_templates(query: str | None = None) -> dict:
    items = CATALOG
    if query:
        q = query.lower()
        items = [c for c in CATALOG if q in c["name"].lower() or any(q in t.lower() for t in c["types"])]
    return {"count": len(items), "demos_root": demos_root(),
            "templates": [{"name": c["name"], "rel": c["rel"], "n_components": c["n_components"]} for c in items[:200]]}


def describe_template(name: str) -> dict:
    c = next((x for x in CATALOG if x["name"] == name), None)
    if not c:
        return {"ok": False, "error": f"no template '{name}'; use plecs_list_templates to search"}
    root = demos_root()
    path = os.path.join(root, c["rel"].replace("/", os.sep)) if root else c["rel"]
    return {"ok": True, "name": name, "rel": c["rel"], "path": path,
            "n_components": c["n_components"], "types": c["types"],
            "note": "Set PLECS_DEMOS_DIR to your PLECS demos folder, then load `path` with plecs_load_model."}
