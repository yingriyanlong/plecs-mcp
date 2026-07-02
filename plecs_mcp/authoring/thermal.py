"""Attach heat sinks + a sink-to-ambient thermal network to a laid-out circuit,
so semiconductor conduction/switching losses and junction temperature can be
simulated and read.

HARD PLECS FACT (verified on live 4.9.5): losses and junction temperature are
computed ONLY for a device whose symbol falls inside an active ``HeatSink``
frame — a wired thermal terminal is not enough. So each thermal device gets a
small HeatSink enclosing just it, whose HeatPort routes up into the clear band
above the circuit to a ``HeatFlowMeter -> ThermalResistor -> ConstantTemperatureGnd``
chain (measures total loss, sets the case-to-ambient path, fixes ambient).

Call AFTER layout (components must have positions). Returns the mutated spec and
the list of ``(name, xml_text)`` loss datasheets to write into ``<model>_plecs/``.
"""
from __future__ import annotations

from .lossdata import semiconductor_xml
from .spec import CircuitSpec, Component, Connection, Output

# device-type -> (junction-temp, conduction-loss, switching-loss) probe signal names.
# These are case-sensitive; a wrong string silently returns 0 (not an error).
PROBE_SIGNALS = {
    "MOSFET": ("MOSFET junction temp", "MOSFET conduction loss", "MOSFET switching loss"),
    "IGBT": ("IGBT junction temp", "IGBT conduction loss", "IGBT switching loss"),
    "Diode": ("Diode junction temp", "Diode conduction loss", "Diode switching loss"),
}
# PLECS component Type -> loss-datasheet class / probe key
_TYPE_CLASS = {"Mosfet": "MOSFET", "Igbt": "IGBT", "Diode": "Diode"}
_XML_KEYS = ("ron", "eon_mJ", "eoff_mJ", "rth", "cth", "v_test", "i_max", "partnumber")


def attach_heatsink(spec: CircuitSpec, devices: list[dict], *, net_y: int = 25,
                    probe: bool = True) -> tuple[CircuitSpec, list[tuple[str, str]]]:
    """Give each device in ``devices`` a heat sink + ambient network + probes.

    Each entry: ``{"name": <component>, "sclass": "MOSFET"|"IGBT"|"Diode",
    "rth_sink": 1.0, "t_amb": 25.0, and loss params ron/eon_mJ/eoff_mJ/rth/cth/
    v_test/i_max}``. Missing loss params fall back to ``semiconductor_xml`` defaults.
    """
    by = {c.name: c for c in spec.components}
    missing = [d["name"] for d in devices if d["name"] not in by]
    if missing:
        raise ValueError(f"thermal device(s) not in spec: {missing}")
    if any(by[d["name"]].position is None for d in devices):
        raise ValueError("attach_heatsink requires a laid-out spec (device positions set); "
                         "run layout first or pass explicit positions")

    net_x0 = max((c.position[0] for c in spec.components if c.position), default=200) + 140
    xmls: list[tuple[str, str]] = []
    for k, dev in enumerate(devices):
        name = dev["name"]
        d = by[name]
        sclass = dev.get("sclass") or _TYPE_CLASS.get(d.type, "MOSFET")
        t_amb = float(dev.get("t_amb", 25.0))
        rth_sink = float(dev.get("rth_sink", 1.0))

        # 1) point the device at its (generated) loss datasheet
        d.params = {**d.params, "thermal": f"file:{name}", "Rth": "0", "T_init": str(t_amb)}
        xml = semiconductor_xml(sclass=sclass, **{key: dev[key] for key in _XML_KEYS if key in dev})
        xmls.append((name, xml))

        # 2) heat sink enclosing ONLY this device (shrink if a neighbour is close)
        dx, dy = d.position
        hw, hh = 22, 26
        for c in spec.components:
            if c is d or c.position is None:
                continue
            cx, cy = c.position
            if abs(cx - dx) <= hw and abs(cy - dy) <= hh:
                hw = min(hw, max(4, abs(cx - dx) - 6))
        spec.components.append(Component(type="HeatSink", name=f"HS_{name}", position=[dx, dy],
                                         frame=[-hw, -hh, hw, hh], direction="up"))

        # 3) per-device ambient network on the clear band above, staggered to the right
        nx, ry = net_x0 + k * 320, net_y
        wm, rth, amb = f"Wm_{name}", f"Rth_{name}", f"Tamb_{name}"
        spec.components += [
            Component(type="HeatFlowMeter", name=wm, position=[nx, ry], direction="up"),
            Component(type="ThermalResistor", name=rth, position=[nx + 100, ry], direction="up",
                      params={"Rth": str(rth_sink)}),
            Component(type="ConstantTemperatureGnd", name=amb, position=[nx + 200, ry], direction="up",
                      params={"T": str(t_amb)}),
        ]
        # HeatPort (HS terminal 1) sits above the frame; route up to the rail then
        # across to the meter's left terminal, all in the clear band.
        spec.connections += [
            Connection(kind="HeatPipe", src=[f"HS_{name}", 1], points=[[dx, ry], [nx - 25, ry]],
                       dsts=[[wm, 2]]),
            Connection(kind="HeatPipe", src=[wm, 1], dsts=[[rth, 1]]),
            Connection(kind="HeatPipe", src=[rth, 2], dsts=[[amb, 1]]),
        ]

        # 4) probes: device junction temp + total dissipated power (heat-flow meter)
        if probe:
            tj_sig = PROBE_SIGNALS.get(sclass, PROBE_SIGNALS["MOSFET"])[0]
            base = len(spec.outputs)
            spec.outputs += [
                Output(name=f"Tj_{name}", index=base + 1, probe_component=name,
                       probe_signal=tj_sig, position=[nx, ry - 45]),
                Output(name=f"Ploss_{name}", index=base + 2, probe_component=wm,
                       probe_signal="Measured heat flow", position=[nx + 100, ry - 45]),
            ]
    return spec, xmls
