"""Offline tests for semiconductor loss / junction-temperature authoring.

Live-PLECS behaviour (Tj rise, heat flow) is verified manually; these cover the
generation logic: loss XML validity, HeatSink serialization, the multi-output
Terminal fix, and attach_heatsink structure/guards.
"""
import xml.dom.minidom as minidom

import pytest

from plecs_mcp.authoring.layout import auto_layout
from plecs_mcp.authoring.lossdata import semiconductor_xml
from plecs_mcp.authoring.serializer import serialize
from plecs_mcp.authoring.spec import CircuitSpec, Component, Output
from plecs_mcp.authoring.thermal import PROBE_SIGNALS, attach_heatsink


def test_loss_xml_is_valid_and_has_loss_tables():
    xml = semiconductor_xml(sclass="MOSFET", ron=0.05, eon_mJ=0.3, eoff_mJ=0.3,
                            rth=0.5, cth=0.02, v_test=48, i_max=10)
    minidom.parseString(xml)  # raises if malformed
    for tag in ("SemiconductorLibrary", "TurnOnLoss", "TurnOffLoss",
                "ConductionLoss", "ThermalModel", 'class="MOSFET"'):
        assert tag in xml


def test_heatsink_serializes_frame_and_heatport():
    s = CircuitSpec(name="t", components=[
        Component(type="Mosfet", name="Q1", position=[130, 95]),
        Component(type="HeatSink", name="HS", position=[130, 95], frame=[-22, -26, 22, 26]),
    ])
    text = serialize(s)
    assert "Type          HeatSink" in text
    assert "Frame         [-22, -26; 22, 26]" in text
    assert "Type          HeatPort" in text


def test_multiple_outputs_emit_distinct_terminals():
    # regression: the serializer used to emit only Terminal Index 1 no matter what,
    # so multi-output models returned a single signal.
    s = CircuitSpec(name="t", components=[Component(type="Resistor", name="R1", position=[100, 100])],
                    outputs=[Output(name="a", index=1, probe_component="R1", probe_signal="x"),
                             Output(name="b", index=2, probe_component="R1", probe_signal="y")])
    text = serialize(s)
    assert text.count("Type          Output") == 2 + 2  # 2 top Terminals + 2 Output blocks
    assert 'Index         "1"' in text and 'Index         "2"' in text


def _buck():
    return CircuitSpec(name="b", components=[
        Component(type="DCVoltageSource", name="V", params={"V": "48"}),
        Component(type="Mosfet", name="Q1", params={"Ron": "0.05"}),
        Component(type="Diode", name="D1", params={"Vf": "0"}),
        Component(type="Inductor", name="L1", params={"L": "200e-6"}),
        Component(type="Capacitor", name="C1", params={"C": "200e-6"}),
        Component(type="Resistor", name="R1", params={"R": "10"}),
        Component(type="PulseGenerator", name="PWM", params={"f": "1e5", "DutyCycle": "0.5"}),
    ], connections=[
        {"kind": "Wire", "src": ["V", 1], "dsts": [["Q1", 1]]},
        {"kind": "Wire", "src": ["Q1", 2], "dsts": [["L1", 1], ["D1", 2]]},
        {"kind": "Wire", "src": ["L1", 2], "dsts": [["C1", 1], ["R1", 1]]},
        {"kind": "Wire", "src": ["C1", 2], "dsts": [["R1", 2], ["V", 2], ["D1", 1]]},
        {"kind": "Signal", "src": ["PWM", 1], "dsts": [["Q1", 3]]},
    ])


def test_attach_heatsink_builds_network_and_datasheet():
    s = auto_layout(_buck())
    s, xmls = attach_heatsink(s, [{"name": "Q1", "sclass": "MOSFET", "ron": 0.05}])
    names = {c.name for c in s.components}
    assert {"HS_Q1", "Wm_Q1", "Rth_Q1", "Tamb_Q1"} <= names
    # device now points at its datasheet and the XML was produced
    q1 = next(c for c in s.components if c.name == "Q1")
    assert q1.params["thermal"] == "file:Q1"
    assert xmls and xmls[0][0] == "Q1" and "SemiconductorLibrary" in xmls[0][1]
    # Tj + dissipated-power probes added with the correct MOSFET signal string
    sigs = {o.probe_signal for o in s.outputs}
    assert PROBE_SIGNALS["MOSFET"][0] in sigs and "Measured heat flow" in sigs
    # heat sink frame encloses the switch but not its neighbours
    hs = next(c for c in s.components if c.name == "HS_Q1")
    qx = q1.position[0]
    x0, _, x1, _ = hs.frame
    for c in s.components:
        if c.name in ("Q1", "HS_Q1") or c.position is None:
            continue
        assert not (qx + x0 <= c.position[0] <= qx + x1 and abs(c.position[1] - q1.position[1]) <= 26)


def test_attach_heatsink_requires_positions():
    with pytest.raises(ValueError):
        attach_heatsink(_buck(), [{"name": "Q1"}])  # not laid out


def test_attach_heatsink_unknown_device():
    s = auto_layout(_buck())
    with pytest.raises(ValueError):
        attach_heatsink(s, [{"name": "NOPE"}])
