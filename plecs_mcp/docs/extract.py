"""Extract the local PLECS help (.qch = Qt Help SQLite) into a plain-text corpus
+ JSON index for offline search. Version-correct: reads the installed manual.

Usage: python -m plecs_mcp.docs.extract <path-to-plecshelp.qch> <out_dir>
"""
from __future__ import annotations

import html
import json
import re
import sqlite3
import sys
import zlib
from pathlib import Path

_SCRIPT = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_HEAD = re.compile(r"<head>.*?</head>", re.S | re.I)
_BLOCK = re.compile(r"<(p|div|br|li|h[1-6]|tr|table|/table)\b[^>]*>", re.I)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f]+")
_NL = re.compile(r"\n\s*\n\s*\n+")


def _decompress(blob: bytes) -> bytes:
    # Qt qCompress prepends a 4-byte big-endian uncompressed size before zlib data.
    try:
        return zlib.decompress(blob[4:])
    except Exception:
        return zlib.decompress(blob)


def html_to_text(h: str) -> tuple[str, str]:
    title = ""
    m = re.search(r"<title>(.*?)</title>", h, re.S | re.I)
    if m:
        title = html.unescape(m.group(1)).strip()
    h = _SCRIPT.sub(" ", h)
    h = _HEAD.sub(" ", h)
    h = _BLOCK.sub("\n", h)
    t = html.unescape(_TAG.sub(" ", h))
    t = _NL.sub("\n\n", _WS.sub(" ", t))
    return title, t.strip()


def build(qch_path: str, out_dir: str) -> int:
    db = sqlite3.connect(qch_path)
    c = db.cursor()
    out = Path(out_dir)
    (out / "pages").mkdir(parents=True, exist_ok=True)
    index = []
    q = ("SELECT f.Name, d.Data FROM FileNameTable f "
         "JOIN FileDataTable d ON f.FileId = d.Id WHERE f.Name LIKE '%.html'")
    for name, blob in c.execute(q):
        try:
            page = _decompress(blob).decode("utf-8", "replace")
        except Exception:
            continue
        title, text = html_to_text(page)
        if len(text) < 20:
            continue
        stem = name[:-5].replace("/", "__").replace("\\", "__")
        body = (title + "\n\n" + text) if title else text
        (out / "pages" / f"{stem}.txt").write_text(body, encoding="utf-8")
        index.append({"name": stem, "title": title or stem, "chars": len(text),
                      "summary": re.sub(r"\s+", " ", text[:240])})
    (out / "docs_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    return len(index)


if __name__ == "__main__":
    n = build(sys.argv[1], sys.argv[2])
    print(f"extracted {n} doc pages to {sys.argv[2]}")
