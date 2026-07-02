"""Generate a PLECS semiconductor loss-data sheet (SemiconductorLibrary XML) from
simple parameters, so thermal models can be authored end to end.

Referenced from a device via its ``thermal`` parameter as ``file:<name>``; the XML
must sit in the model's ``<model>_plecs/`` resource folder. See the bundled
buck_converter_with_thermal_model demo for the format this mirrors.
"""
from __future__ import annotations


def _row(vals) -> str:
    return " ".join(f"{v:g}" for v in vals)


def semiconductor_xml(sclass: str = "MOSFET", ron: float = 0.05, eon_mJ: float = 0.5,
                      eoff_mJ: float = 0.5, rth: float = 0.5, cth: float = 0.02,
                      v_test: float = 400.0, i_max: float = 20.0,
                      partnumber: str = "Generic") -> str:
    """Build a minimal, valid loss datasheet.

    Conduction: linear V_drop = ron * i. Switching: energy linear in current at
    v_test (mJ). Thermal: one Cauer R-C branch (junction-to-case).
    """
    iax = [0, i_max * 0.25, i_max * 0.5, i_max * 0.75, i_max]
    eon = [eon_mJ * i / i_max for i in iax]
    eoff = [eoff_mJ * i / i_max for i in iax]
    vdrop = [ron * i for i in iax]
    zeros = [0] * len(iax)

    def sw_block(tag, energy):
        # two temperatures (25, 125), voltages (0, v_test); energy at 0 V = 0
        return (f"            <{tag}>\n"
                f"                <ComputationMethod>Table only</ComputationMethod>\n"
                f"                <CurrentAxis>{_row(iax)}</CurrentAxis>\n"
                f"                <VoltageAxis>0 {v_test:g}</VoltageAxis>\n"
                f"                <TemperatureAxis>25 125</TemperatureAxis>\n"
                f'                <Energy scale="0.001">\n'
                f"                    <Temperature>\n"
                f"                        <Voltage>{_row(zeros)}</Voltage>\n"
                f"                        <Voltage>{_row(energy)}</Voltage>\n"
                f"                    </Temperature>\n"
                f"                    <Temperature>\n"
                f"                        <Voltage>{_row(zeros)}</Voltage>\n"
                f"                        <Voltage>{_row([e * 1.2 for e in energy])}</Voltage>\n"
                f"                    </Temperature>\n"
                f"                </Energy>\n"
                f"            </{tag}>\n")

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<SemiconductorLibrary xmlns="http://www.plexim.com/xml/semiconductors/" version="1.1">\n'
        f'    <Package class="{sclass}" vendor="plecs-mcp" partnumber="{partnumber}">\n'
        "        <Variables/>\n"
        f'        <SemiconductorData type="{sclass}">\n'
        + sw_block("TurnOnLoss", eon)
        + sw_block("TurnOffLoss", eoff)
        + "            <ConductionLoss>\n"
          "                <ComputationMethod>Table only</ComputationMethod>\n"
          f"                <CurrentAxis>{_row(iax)}</CurrentAxis>\n"
          "                <TemperatureAxis>25 125</TemperatureAxis>\n"
          '                <VoltageDrop scale="1">\n'
          f"                    <Temperature>{_row(vdrop)}</Temperature>\n"
          f"                    <Temperature>{_row([1.2 * v for v in vdrop])}</Temperature>\n"
          "                </VoltageDrop>\n"
          "            </ConductionLoss>\n"
          "        </SemiconductorData>\n"
          "        <ThermalModel>\n"
          '            <Branch type="Cauer">\n'
          f'                <RCElement R="{rth:g}" C="{cth:g}"/>\n'
          "            </Branch>\n"
          "        </ThermalModel>\n"
          "        <Comment><Line></Line></Comment>\n"
          "    </Package>\n"
          "</SemiconductorLibrary>\n"
    )
