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
    schematic: Optional[dict] = None  # Type "Subsystem": {"components":[...], "connections":[...]}
    frame: Optional[list[int]] = None  # Type "HeatSink": [x0,y0,x1,y1] rectangle (relative to Position)
                                       # enclosing the semiconductor(s) that dissipate into this sink


class Connection(BaseModel):
    kind: str = "Wire"              # "Wire" (power net) or "Signal" (control)
    src: list                       # [component_name, terminal_index]
    points: list = []               # waypoints after src, e.g. [[40, 95]]
    dsts: list                      # [name, term] or [name, term, [[x,y],...]] (per-branch points)


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
