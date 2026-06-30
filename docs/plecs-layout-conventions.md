# PLECS layout conventions (learned from the bundled demos)

Distilled from the 89 official Plexim demo models (`plecs_mcp/authoring/reference/`).
These rules make agent-generated `.plecs` schematics look like the official ones,
instead of a single messy row. Electrical correctness is symbolic (component name +
terminal index); these conventions are purely about a clean, readable drawing.

## Coordinate grid
- PLECS uses a tight grid; a single converter fits roughly in x ∈ [40, 450],
  y ∈ [70, 190]. Keep component spacing ~45–55 px. (Our first attempt used 90+ px
  and no routing, which looked sparse and tangled.)
- Two horizontal rails:
  - **Top rail** (positive / output node) at **y = 95**.
  - **Bottom rail** (ground / return) at **y ≈ 185**.
  - Vertical "bridge" components sit at **y = 140**, so their top pin reaches the
    top rail and their bottom pin reaches the ground rail.

## Role → orientation (from boost_converter.plecs)
| Role | Type | Direction | Flipped | Row |
|------|------|-----------|---------|-----|
| Input source | DCVoltageSource | down | on | bridge (x at far left) |
| Series inductor | Inductor | left | off | top rail (y=95) |
| Series diode | Diode | right | on | top rail (y=95) |
| Switch (low side) | Mosfet/Igbt | up | off | bridge (y=140) |
| Output capacitor | Capacitor | down | on | bridge (y=140) |
| Load resistor | Resistor | down | off | bridge (y=140) |
| Gate driver | PulseGenerator | right | off | below switch |

Note: terminal index → physical pin depends on Direction/Flipped. With the table
above: source/cap top pin = terminal 1; resistor top pin = terminal 2; mosfet
drain = 1 (top), source = 2 (bottom), gate = 3; diode anode = 1, cathode = 2.

## Wire routing (Points)
- Draw rails as horizontal wires at y=95 (top) and y≈185 (bottom); drop vertically
  to each component pin.
- In a spec, give each `Wire` a `points` list to the rail, and per-branch points at
  `[component_x, rail_y]`. Example (boost output rail):
  `{"src":["C1",1],"points":[[285,95]],"dsts":[["R1",2,[[340,95]]],["D1",2]]}`.
- Measurements use `PlecsProbe` (references a component by name — no power wire),
  feeding an `Output` port.

## Standard topologies: prefer the demos
For any standard converter (buck, boost, buck-boost, cuk, sepic, flyback, forward,
full/half bridge, LLC, dual-active-bridge, inverters, PFC, ...) the bundled demo is
already perfectly laid out. Use `plecs_list_templates` to find it and load it as a
clean starting point rather than generating from scratch. Generation is for novel
or parameterised topologies, following the rules above.
