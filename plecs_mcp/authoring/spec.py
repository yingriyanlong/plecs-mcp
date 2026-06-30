"""Structured circuit specification (the single source of truth for authoring).

A CircuitSpec is serialised to a .plecs file. Connectivity is symbolic:
each Connection references components by name and terminal index.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Component(BaseModel):
    type: str                       # PLECS Type, e.g. "Mosfet" (see knowledge base)
    name: str
    params: dict[str, str] = {}     # parameter name -> value/expression (e.g. {"L": "Lo"})
    position: Optional[list[int]] = None
    direction: str = "up"
    flipped: bool = False


class Connection(BaseModel):
    kind: str = "Wire"              # "Wire" (power net) or "Signal" (control)
    src: list                       # [component_name, terminal_index]
    dsts: list                      # [[component_name, terminal_index], ...]


class Output(BaseModel):
    name: str = "Out1"
    index: int = 1
    probe_component: str            # component to measure
    probe_signal: str               # e.g. "Capacitor voltage"
    position: Optional[list[int]] = None


class CircuitSpec(BaseModel):
    name: str
    init: str = ""                  # PLECS InitializationCommands (variables)
    time_span: str = "5e-3"
    components: list[Component]
    connections: list[Connection] = []
    outputs: list[Output] = []
    solver: dict = {}
