"""Draft checks, never a manufacturing signoff. --release exits 1 until release."""
import ast
import csv
import json
import sys
from decimal import Decimal
from pathlib import Path
import sexpdata
from PIL import Image

root = Path(__file__).resolve().parents[1]
h = root / 'hardware'
for name in ['study-timer.kicad_sch','study-timer.kicad_pcb','source-symbols.kicad_sym']:
    sexpdata.load(open(h/name))
json.loads((h/'study-timer.kicad_pro').read_text())
ast.parse((root/'firmware/main.py').read_text())
assert len((root/'firmware/main.py').read_text().splitlines()) < 150
assert Image.open(h/'pcb.png').size == (800,600)
assert (h/'schematic.pdf').read_bytes().startswith(b'%PDF-')
rows=list(csv.DictReader(open(h/'BOM.csv')))
for row in rows:
    assert Decimal(row['Total']) == Decimal(row['Unit Price'])*int(row['Quantity'])
total=sum(Decimal(row['Total']) for row in rows)
readme=(root/'README.md').read_text()
for text in ['![PCB Render](hardware/pcb.png)', 'How to order from JLCPCB', 'How to flash firmware', 'Unit allowance']:
    assert text in readme
print(f'PASS: draft structure, firmware syntax, image dimensions, PDF header, BOM arithmetic (${total:.2f} parts allowance).')
print('NOT VALIDATED: native KiCad open/save, ERC, DRC, electrical connectivity, sourcing, delivered cost.')
print('RELEASE BLOCKED: placement envelopes have no electrical pads; routing and real manufacturing exports absent.')
if '--release' in sys.argv:
    sys.exit(1)
