"""Lightweight offline search over the extracted PLECS docs corpus (TF-IDF,
stdlib only). Corpus dir defaults to <repo>/.docs_cache or $PLECS_MCP_DOCS_DIR."""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from pathlib import Path

_WORD = re.compile(r"[a-z0-9]+")


def _tok(s: str) -> list[str]:
    return _WORD.findall(s.lower())


def default_dir() -> str:
    return os.environ.get("PLECS_MCP_DOCS_DIR") or str(
        Path(__file__).resolve().parents[2] / ".docs_cache")


class DocIndex:
    def __init__(self, root: str):
        self.root = Path(root)
        self.index = json.loads((self.root / "docs_index.json").read_text(encoding="utf-8"))
        self.by_name = {d["name"]: d for d in self.index}
        self._tf: dict[str, Counter] = {}
        self._df: dict[str, int] = {}
        for d in self.index:
            toks = _tok(d["title"]) * 3 + _tok(self._text(d["name"]))
            tf = Counter(toks)
            self._tf[d["name"]] = tf
            for t in tf:
                self._df[t] = self._df.get(t, 0) + 1
        self._n = max(1, len(self.index))

    def _text(self, name: str) -> str:
        p = self.root / "pages" / f"{name}.txt"
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        qt = _tok(query)
        scored = []
        for name, tf in self._tf.items():
            s = 0.0
            for t in set(qt):
                if t in tf:
                    idf = math.log(1 + self._n / (1 + self._df.get(t, 0)))
                    s += (1 + math.log(tf[t])) * idf
            if s > 0:
                scored.append((s, name))
        scored.sort(reverse=True)
        out = []
        for sc, name in scored[:top_k]:
            d = self.by_name[name]
            out.append({"name": name, "title": d["title"], "score": round(sc, 2),
                        "summary": d["summary"]})
        return out

    def get(self, name: str) -> dict | None:
        d = self.by_name.get(name)
        if not d:
            key = name.lower()
            d = next((x for x in self.index if key in x["name"].lower()
                      or key in x["title"].lower()), None)
        if not d:
            return None
        return {"name": d["name"], "title": d["title"], "text": self._text(d["name"])}


_INDEX = None


def get_index():
    global _INDEX
    if _INDEX is None:
        d = default_dir()
        if not (Path(d) / "docs_index.json").exists():
            return None
        _INDEX = DocIndex(d)
    return _INDEX
