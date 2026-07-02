"""Serialise a CircuitSpec to PLECS ``.plecs`` text.

The header/solver block mirrors a model verified to load on live PLECS 4.7.
Electrical connectivity is symbolic (SrcComponent/SrcTerminal ->
DstComponent/DstTerminal); ``Points`` are omitted (PLECS routes wires itself).
"""
from __future__ import annotations

from .spec import CircuitSpec, Component, Connection

_HEADER = [
    "  Version       \"4.7\"",
    "  CircuitModel  \"ContStateSpace\"",
    "  StartTime     \"0.0\"",
]

_SOLVER = [
    "  Timeout       \"\"",
    "  Solver        \"radau\"",
    "  MaxStep       \"1e-6\"",
    "  InitStep      \"-1\"",
    "  FixedStep     \"1e-3\"",
    "  Refine        \"1\"",
    "  ZCStepSize    \"1e-9\"",
    "  RelTol        \"1e-3\"",
    "  AbsTol        \"-1\"",
    "  TurnOnThreshold \"1\"",
    "  SyncFixedStepTasks \"2\"",
    "  UseSingleCommonBaseRate \"2\"",
    "  LossVariableLimitExceededMsg \"3\"",
    "  NegativeSwitchLossMsg \"3\"",
    "  DivisionByZeroMsg \"2\"",
    "  StiffnessDetectionMsg \"2\"",
    "  MaxConsecutiveZCs \"1000\"",
    "  AlgebraicLoopWithStateMachineMsg \"2\"",
    "  AssertionAction \"1\"",
]

_TAIL = [
    "  InitialState  \"1\"",
    "  SystemState   \"\"",
    "  TaskingMode   \"1\"",
    "  TaskConfigurations \"\"",
    "  CodeGenParameterInlining \"2\"",
    "  CodeGenFloatingPointFormat \"2\"",
    "  CodeGenAbsTimeUsageMsg \"3\"",
    "  CodeGenBaseName \"\"",
    "  CodeGenOutputDir \"\"",
    "  CodeGenExtraOpts \"\"",
    "  CodeGenTarget \"Generic\"",
    "  CodeGenTargetSettings \"\"",
    "  ExtendedMatrixPrecision \"2\"",
    "  MatrixSignificanceCheck \"2\"",
    "  EnableStateSpaceSplitting \"2\"",
    "  DisplayStateSpaceSplitting \"1\"",
    "  DiscretizationMethod \"2\"",
    "  ExternalModeSettings \"\"",
    "  AlgebraicLoopMethod \"1\"",
    "  AlgebraicLoopTolerance \"1e-6\"",
    "  ScriptsDialogGeometry \"\"",
    "  ScriptsDialogSplitterPos \"0\"",
]


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _params(params: dict) -> list[str]:
    out: list[str] = []
    for k, v in params.items():
        out += [
            "      Parameter {",
            f'        Variable      "{k}"',
            f'        Value         "{v}"',
            "        Show          off",
            "      }",
        ]
    return out


def _component(c, x: int, y: int) -> list[str]:
    out = [
        "    Component {",
        f"      Type          {c.type}",
        f'      Name          "{c.name}"',
        "      Show          on",
        f"      Position      [{x}, {y}]",
        f"      Direction     {c.direction}",
        f"      Flipped       {'on' if c.flipped else 'off'}",
        "      LabelPosition south",
    ]
    out += _params(c.params)
    out.append("    }")
    return out



def _heatsink(c, x: int, y: int) -> list[str]:
    """A HeatSink is a rectangular region; any semiconductor whose symbol falls
    inside ``frame`` dissipates its (datasheet) losses into this sink. PLECS
    computes junction temperature / conduction / switching loss ONLY for devices
    placed on an active heat sink — a wired thermal terminal is not enough.
    The HeatPort (terminal 1) connects the sink to an ambient thermal network."""
    fx0, fy0, fx1, fy1 = c.frame or [-30, -40, 30, 40]
    params = dict(c.params) or {}
    params.setdefault("Cth", "0")
    params.setdefault("T_init", "")
    params.setdefault("Width", "1")
    out = [
        "    Component {",
        "      Type          HeatSink",
        f'      Name          "{c.name}"',
        "      Show          on",
        f"      Position      [{x}, {y}]",
        f"      Direction     {c.direction}",
        f"      Flipped       {'on' if c.flipped else 'off'}",
        "      LabelPosition south",
        f"      Frame         [{fx0}, {fy0}; {fx1}, {fy1}]",
    ]
    out += _params(params)
    # HeatPort above the frame, pointing up: the band above a converter's top
    # rail is the most reliably empty area, so the sink-to-ambient thermal
    # network routes there without crossing power wires.
    out += [
        "      Terminal {",
        "        Type          HeatPort",
        f"        Position      [0, {fy0 - 20}]",
        "        Direction     up",
        "      }",
        "    }",
    ]
    return out


def _subsystem(c, x: int, y: int) -> list[str]:
    sch = c.schematic or {}
    inner = [d if isinstance(d, Component) else Component(**d) for d in sch.get("components", [])]
    conns = [d if isinstance(d, Connection) else Connection(**d) for d in sch.get("connections", [])]
    L = [
        "    Component {", "      Type          Subsystem",
        f'      Name          "{c.name}"', "      Show          on",
        f"      Position      [{x}, {y}]", f"      Direction     {c.direction}",
        f"      Flipped       {'on' if c.flipped else 'off'}", "      LabelPosition south",
        "      Frame         [-20, -10; 20, 10]", '      SampleTime    "-1"',
        '      CodeGenDiscretizationMethod "2"', '      CodeGenTarget "Generic"',
        "      MaskIconFrame on", "      MaskIconOpaque off", "      MaskIconRotates on",
    ]
    ports = sorted((int(p.params.get("Index", "1")), p.type) for p in inner
                   if p.type in ("Input", "Output"))
    for _idx, ptype in ports:
        if ptype == "Input":
            L += ["      Terminal {", "        Type          Input",
                  "        Position      [-20, 0]", "        Direction     left", "      }"]
        else:
            L += ["      Terminal {", "        Type          Output",
                  "        Position      [20, 0]", "        Direction     right", "      }"]
    L += ["      Schematic {", "        Location      [200, 200; 600, 420]",
          "        ZoomFactor    1", "        SliderPosition [0, 0]",
          "        ShowBrowser   off", "        BrowserWidth  100"]
    body: list[str] = []
    ix = 60
    for ic in inner:
        px, py = (ic.position or [ix, 100])
        body += _component(ic, px, py)
        ix += 70
    for conn in conns:
        body += _connection(conn)
    L += ["    " + line for line in body]
    L += ["      }", "    }"]
    return L


def _probe(o, x: int, y: int) -> list[str]:
    return [
        "    Component {",
        "      Type          PlecsProbe",
        f'      Name          "{o.name}_prb"',
        "      Show          on",
        f"      Position      [{x}, {y}]",
        "      Direction     right",
        "      Flipped       off",
        "      LabelPosition south",
        "      Probe {",
        f'        Component     "{o.probe_component}"',
        '        Path          ""',
        f'        Signals       {{"{o.probe_signal}"}}',
        "      }",
        "    }",
    ]


def _output(o, x: int, y: int) -> list[str]:
    return [
        "    Component {",
        "      Type          Output",
        f'      Name          "{o.name}"',
        "      Show          on",
        f"      Position      [{x}, {y}]",
        "      Direction     right",
        "      Flipped       off",
        "      LabelPosition south",
        "      Parameter {",
        '        Variable      "Index"',
        f'        Value         "{o.index}"',
        "        Show          on",
        "      }",
        "      Parameter {",
        '        Variable      "Width"',
        '        Value         "-1"',
        "        Show          off",
        "      }",
        "    }",
    ]


def _pts(points) -> str:
    return "[" + "; ".join(f"{int(x)}, {int(y)}" for x, y in points) + "]"


def _connection_raw(kind: str, src: list, dsts: list, points=None) -> list[str]:
    out = [
        "    Connection {",
        f"      Type          {kind}",
        f'      SrcComponent  "{src[0]}"',
        f"      SrcTerminal   {int(src[1])}",
    ]
    if points:
        out.append(f"      Points        {_pts(points)}")
    norm = [(d[0], d[1], d[2] if len(d) > 2 else None) for d in dsts]
    if len(norm) == 1 and norm[0][2] is None:
        out += [f'      DstComponent  "{norm[0][0]}"', f"      DstTerminal   {int(norm[0][1])}"]
    else:
        for name, term, p in norm:
            b = ["      Branch {"]
            if p:
                b.append(f"        Points        {_pts(p)}")
            b += [f'        DstComponent  "{name}"', f"        DstTerminal   {int(term)}", "      }"]
            out += b
    out.append("    }")
    return out


def _connection(conn) -> list[str]:
    return _connection_raw(conn.kind, conn.src, conn.dsts, getattr(conn, "points", None))


def serialize(spec: CircuitSpec) -> str:
    L: list[str] = ["Plecs {", f'  Name          "{spec.name}"']
    L += _HEADER
    L += [f'  TimeSpan      "{spec.time_span}"']
    L += _SOLVER
    L += [f'  InitializationCommands "{_esc(spec.init)}"']
    L += _TAIL
    out_indices = [int(o.index) for o in spec.outputs]
    out_indices += [int(c.params.get("Index", "1")) for c in spec.components if c.type == "Output"]
    for idx in sorted(set(out_indices)):
        L += ["  Terminal {", "    Type          Output", f'    Index         "{idx}"', "  }"]
    L += [
        "  Schematic {",
        "    Location      [915, 288; 1725, 613]",
        "    ZoomFactor    1",
        "    SliderPosition [0, 0]",
        "    ShowBrowser   off",
        "    BrowserWidth  100",
    ]
    x = 85
    for c in spec.components:
        px, py = (c.position or [x, 100])
        if getattr(c, "schematic", None):
            L += _subsystem(c, px, py)
        elif c.type == "HeatSink":
            L += _heatsink(c, px, py)
        else:
            L += _component(c, px, py)
        x += 90
    for i, o in enumerate(spec.outputs):
        px, py = (o.position or [x + 80, 100 + i * 40])
        L += _probe(o, px - 60, py)
        L += _output(o, px, py)
    for conn in spec.connections:
        L += _connection(conn)
    for o in spec.outputs:
        L += _connection_raw("Signal", [f"{o.name}_prb", 1], [[o.name, 1]])
    L += ["  }", "}", ""]
    return "\n".join(L)
