"""In-memory store for simulation results, keyed by a short handle.

Large waveforms stay server-side; tools return handles + summaries instead of
raw arrays, to keep the agent's context small.
"""
from __future__ import annotations

import uuid
from typing import Any


class ResultStore:
    def __init__(self) -> None:
        self._d: dict[str, dict[str, Any]] = {}

    def add(self, model: str, time: list, values: list[list]) -> str:
        handle = "res_" + uuid.uuid4().hex[:8]
        self._d[handle] = {"model": model, "time": time, "values": values}
        return handle

    def get(self, handle: str) -> dict[str, Any] | None:
        return self._d.get(handle)


STORE = ResultStore()
