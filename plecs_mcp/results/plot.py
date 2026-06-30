"""Render waveforms to a PNG (matplotlib, headless)."""
from __future__ import annotations

import os
import tempfile
import uuid

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def plot_series(time, series: dict, out_path: str | None = None, title: str = "PLECS waveforms") -> str:
    if out_path is None:
        d = os.environ.get("PLECS_MCP_PLOT_DIR", tempfile.gettempdir())
        os.makedirs(d, exist_ok=True)
        out_path = os.path.join(d, f"plecs_{uuid.uuid4().hex[:8]}.png")
    fig, ax = plt.subplots(figsize=(8, 4))
    for name, y in series.items():
        ax.plot(time, y, label=str(name))
    ax.set_xlabel("Time (s)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
