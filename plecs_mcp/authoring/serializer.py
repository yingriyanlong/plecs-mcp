"""Serialise a CircuitSpec to PLECS ``.plecs`` text.

The header/solver block mirrors a model verified to load on live PLECS 4.7.
Electrical connectivity is symbolic (SrcComponent/SrcTerminal ->
DstComponent/DstTerminal); ``Points`` are omitted (PLECS routes wires itself).
"""
from __future__ import annotations

from .spec import CircuitSpec

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


def _connection(kind: str, src: list, dsts: list) -> list[str]:
    out = [
        "    Connection {",
        f"      Type          {kind}",
        f'      SrcComponent  "{src[0]}"',
        f"      SrcTerminal   {int(src[1])}",
    ]
    if len(dsts) == 1:
        out += [f'      DstComponent  "{dsts[0][0]}"', f"      DstTerminal   {int(dsts[0][1])}"]
    else:
        for d in dsts:
            out += ["      Branch {", f'        DstComponent  "{d[0]}"',
                    f"        DstTerminal   {int(d[1])}", "      }"]
    out.append("    }")
    return out


def serialize(spec: CircuitSpec) -> str:
    L: list[str] = ["Plecs {", f'  Name          "{spec.name}"']
    L += _HEADER
    L += [f'  TimeSpan      "{spec.time_span}"']
    L += _SOLVER
    L += [f'  InitializationCommands "{_esc(spec.init)}"']
    L += _TAIL
    if spec.outputs:
        L += ["  Terminal {", "    Type          Output", '    Index         "1"', "  }"]
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
        L += _component(c, px, py)
        x += 90
    for i, o in enumerate(spec.outputs):
        px, py = (o.position or [x + 80, 100 + i * 40])
        L += _probe(o, px - 60, py)
        L += _output(o, px, py)
    for conn in spec.connections:
        L += _connection(conn.kind, conn.src, conn.dsts)
    for o in spec.outputs:
        L += _connection("Signal", [f"{o.name}_prb", 1], [[o.name, 1]])
    L += ["  }", "}", ""]
    return "\n".join(L)
