"""Automatic two-rail layout for converter-style circuits.

Given a spec with only components + symbolic connections (no coordinates), fill
positions/directions/flipped and rebuild the power wires with orthogonal `Points`
so the schematic follows the PLECS demo convention
(docs/plecs-layout-conventions.md). Electrical connectivity is preserved exactly
(wires are regrouped per electrical net, not rerouted electrically).

Classification is by connectivity, not just type: a 2-terminal component is a
horizontal *series* element when both terminals are on non-ground nets, and a
vertical *bridge* when one terminal is on ground. Scope: single-source DC-DC
converter family (buck, boost, buck-boost and similar two-rail ladders).
"""
from __future__ import annotations

from collections import deque

from .spec import Connection, CircuitSpec

TOP, MID, BOT = 95, 140, 185
X0, DX = 60, 70

_SOURCE = {"DCVoltageSource", "DCCurrentSource"}
_SWITCH = {"Mosfet", "Igbt", "MosfetWithDiode"}
_CONTROL = {"PulseGenerator", "Constant", "Step", "Gain", "Sum"}
_SKIP = {"PlecsProbe", "Output"}

# preferred orientation when used as a vertical bridge: (direction, flipped, natural_top_term)
_VBRIDGE = {
    "Capacitor": ("down", True, 1),
    "Resistor": ("down", False, 2),
    "Voltmeter": ("up", False, 1),
    "Inductor": ("up", False, 1),
    "Diode": ("up", True, 2),
}
# preferred orientation when used as a horizontal series element: (direction, flipped, left_term, right_term)
_HSERIES = {
    "Inductor": ("left", False, 1, 2),
    "Diode": ("right", True, 1, 2),
}


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        r = x
        while self.p[r] != r:
            r = self.p[r]
        while self.p[x] != r:
            self.p[x], x = r, self.p[x]
        return r

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def auto_layout(spec: CircuitSpec) -> CircuitSpec:
    comps = list(spec.components)
    wires = [c for c in spec.connections if c.kind == "Wire"]
    sigs = [c for c in spec.connections if c.kind != "Wire"]

    uf = _UF()
    for conn in wires:
        s = (conn.src[0], int(conn.src[1]))
        for d in conn.dsts:
            uf.union(s, (d[0], int(d[1])))

    def tnet(name, term):
        return uf.find((name, term))

    gnd = input_net = None
    for c in comps:
        if c.type in _SOURCE:
            gnd, input_net = tnet(c.name, 2), tnet(c.name, 1)
            break

    nets = set()
    for conn in wires:
        for node in [(conn.src[0], int(conn.src[1]))] + [(d[0], int(d[1])) for d in conn.dsts]:
            nets.add(uf.find(node))

    def touches_gnd(c):
        return gnd in (tnet(c.name, 1), tnet(c.name, 2))

    # order non-ground nets by BFS from input net along series links (both ends non-ground)
    adj = {n: set() for n in nets}
    for c in comps:
        if c.type in _SKIP or c.type in _CONTROL or c.type in _SOURCE:
            continue
        a, b = tnet(c.name, 1), tnet(c.name, 2)
        if a != gnd and b != gnd and a in adj and b in adj:
            adj[a].add(b)
            adj[b].add(a)
    rank = {}
    if input_net is not None:
        rank[input_net] = 0
        q = deque([input_net])
        while q:
            n = q.popleft()
            for m in adj[n]:
                if m not in rank:
                    rank[m] = rank[n] + 1
                    q.append(m)
    nxt = (max(rank.values()) + 1) if rank else 0
    for n in nets:
        if n != gnd and n not in rank:
            rank[n] = nxt
            nxt += 1

    def prim_rank(c):
        if c.type in _SOURCE:
            return -1
        rs = [rank.get(tnet(c.name, t), 0) for t in (1, 2) if tnet(c.name, t) != gnd]
        return max(rs) if rs else 0

    placeable = [c for c in comps if c.type not in _CONTROL and c.type not in _SKIP]
    placeable.sort(key=lambda c: (prim_rank(c), comps.index(c)))
    x_of = {c.name: X0 + i * DX for i, c in enumerate(placeable)}
    pin = {}

    for c in placeable:
        x = x_of[c.name]
        if c.type in _SOURCE:
            c.position, c.direction, c.flipped = [x, MID], "down", True
            pin[(c.name, 1)], pin[(c.name, 2)] = (x, TOP), (x, BOT)
            continue
        if touches_gnd(c):  # vertical bridge
            direction, flipped, ntop = _VBRIDGE.get(c.type, ("up", False, 1))
            if c.type in _SWITCH:
                direction, flipped, ntop = "up", False, 1
            top_t = 2 if tnet(c.name, 1) == gnd else 1
            bot_t = 1 if top_t == 2 else 2
            if ntop != top_t:
                flipped = not flipped
            c.position, c.direction, c.flipped = [x, MID], direction, flipped
            pin[(c.name, top_t)], pin[(c.name, bot_t)] = (x, TOP), (x, BOT)
            if c.type in _SWITCH:
                pin[(c.name, 3)] = (x - 25, MID)
        else:  # horizontal series
            direction, flipped, lt, rt = _HSERIES.get(c.type, ("left", False, 1, 2))
            if rank.get(tnet(c.name, lt), 0) > rank.get(tnet(c.name, rt), 0):
                flipped = not flipped
                lt, rt = rt, lt
            c.position, c.direction, c.flipped = [x, TOP], direction, flipped
            pin[(c.name, lt)], pin[(c.name, rt)] = (x - 25, TOP), (x + 25, TOP)
            if c.type in _SWITCH:
                pin[(c.name, 3)] = (x, MID + 35)

    rightmost = max(x_of.values(), default=X0)
    for c in comps:
        if c.type in _CONTROL:
            tx = X0
            for s in sigs:
                if s.src[0] == c.name and s.dsts:
                    tx = x_of.get(s.dsts[0][0], X0)
            c.position, c.direction, c.flipped = [tx - 30, MID + 70], "right", False
            pin[(c.name, 1)] = (tx - 10, MID + 70)
    px = rightmost + DX
    for c in comps:
        if c.type == "PlecsProbe":
            c.position = [px, TOP]
            pin[(c.name, 1)] = (px + 20, TOP)
        elif c.type == "Output":
            c.position = [px + 70, TOP]
            pin[(c.name, 1)] = (px + 55, TOP)

    # rebuild one wire per electrical net, routed along its rail
    net_terms = {}
    for conn in wires:
        for node in [(conn.src[0], int(conn.src[1]))] + [(d[0], int(d[1])) for d in conn.dsts]:
            net_terms.setdefault(uf.find(node), []).append(node)
    new_wires = []
    for n, raw in net_terms.items():
        terms = sorted(set(raw), key=lambda t: pin.get(t, (0, 0))[0])
        if len(terms) < 2:
            continue
        rail = BOT if n == gnd else TOP
        src = terms[0]
        dsts = [[t[0], t[1], [[pin.get(t, (X0, rail))[0], rail]]] for t in terms[1:]]
        new_wires.append(Connection(kind="Wire", src=[src[0], src[1]],
                                    points=[[pin.get(src, (X0, rail))[0], rail]], dsts=dsts))
    spec.connections = new_wires + sigs
    return spec
