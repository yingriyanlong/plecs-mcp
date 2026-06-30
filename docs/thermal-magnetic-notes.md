# Thermal & magnetic modeling notes (from the PLECS demos)

The MCP's simulate / analyze / scan tools are **domain-agnostic** — they already
run thermal and magnetic models (verified: buck_converter_with_thermal_model
loads and simulates through the MCP). Component discovery covers these domains:
`plecs_list_component_types("thermal")` and `("magnetic")` list them, and
`plecs_describe_component` returns terminal counts + parameters.

## Thermal
- Component types: `Igbt`/`Diode`/`Mosfet` with a thermal description, `HeatSink`,
  `ThermalResistor`, `ThermalChain`, `ConstantTemperature`, `ConstantTemperatureGnd`,
  `ThermalGround`, `HeatFlowMeter`, `SwitchLossCalculator`.
- Read results with a `PlecsProbe` on the device, using these signal names
  (from buck_converter_with_thermal_model):
  - IGBT junction temperature: `"IGBT junction temp"`
  - Diode junction temperature: `"Diode junction temp"`
  - Heat sink temperature: `HeatSink` signal `"Temperature"`
  - Dissipated power / heat flow: `HeatFlowMeter` signal `"Measured heat flow"`
  - Source power: `DCVoltageSource` signal `"Source power"` (for efficiency)
- Conduction loss comes from `Ron`/`Vf`; switching loss needs a loss table in the
  device's thermal description.

## Magnetic
- Component types: `Transformer`, `MagneticInterface` (permeance/winding domain).

## Status / limits (honest)
- Running thermal/magnetic models and reading their probe signals works today.
- AUTHORING thermal/magnetic models from scratch is future work: it needs the
  thermal-port netlist and device loss-data/thermal descriptions (loss tables),
  and the magnetic permeance network — none of which the current two-rail
  electrical layouter/serializer generates. Use `plecs_list_templates` to start
  from a demo (e.g. buck_converter_with_thermal_model, flyback_converter_with_magnetics).
