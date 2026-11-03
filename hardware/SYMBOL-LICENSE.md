# KiCad symbol attribution

`source-symbols.kicad_sym` and the embedded symbols in `study-timer.kicad_sch`
are derived from the standard KiCad symbol libraries, retrieved from the
apcountryman/kicad-symbols GitHub mirror on 2026-11-03:
https://github.com/apcountryman/kicad-symbols

Libraries: MCU_RaspberryPi, Device, Connector, Connector_Generic, Switch,
Regulator_Linear, Transistor_BJT, Memory_Flash. Symbol names retain their
standard library identifiers. The inherited AMS1117 symbol was flattened
for embedding; geometry sub-symbols were renamed to match the resolved name.

These library assets use KiCad's CC BY-SA 4.0 license with its schematic/PCB
exception, not this project's MIT license. KiCad library licensing:
https://www.kicad.org/libraries/license/
