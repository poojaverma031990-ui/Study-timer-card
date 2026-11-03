"""Generate review-only KiCad 7 design and documentation from design.json.
Not a router, ERC engine, DRC engine, or manufacturing exporter.
Run with Python dependencies in tools/requirements.txt.
"""
import copy
import csv
import json
import math
import uuid
from pathlib import Path
import sexpdata as sx
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / 'hardware'
S = sx.Symbol

def uid():
    return str(uuid.uuid4())

def get(node, key):
    return next((x for x in node if isinstance(x, list) and str(x[0]) == key), None)

def walk(node, key):
    if isinstance(node, list):
        if node and str(node[0]) == key:
            yield node
        else:
            for child in node:
                yield from walk(child, key)


def build():
    design = json.loads((H / 'design.json').read_text())
    symbols = sx.load(open(H / 'source-symbols.kicad_sym'))
    libs = {z[1]: z for z in symbols if isinstance(z, list) and str(z[0]) == 'symbol'}
    root = uid()
    schematic = ['(kicad_sch (version 20230121) (generator eeschema)',
                 f'(uuid {root}) (paper "A2")',
                 '(title_block (title "LED Study Timer Card") (rev "DRAFT-1") (company "Harsh | AI-assisted design; NOT RELEASED"))',
                 '(lib_symbols ' + '\n'.join(sx.dumps(x) for x in libs.values()) + ')']
    nets = sorted({net for c in design for net in c['nets'].values() if net})
    netids = {n: i + 1 for i, n in enumerate(nets)}
    board = ['(kicad_pcb (version 20221018) (generator pcbnew)',
             '(general (thickness 1.6)) (paper "A4")',
             '(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user "b.silkscreen") (37 "F.SilkS" user "f.silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user))',
             '(setup (pad_to_mask_clearance 0)) (net 0 "")']
    board += [f'(net {i} "{n}")' for n, i in netids.items()]
    pdf = canvas.Canvas(str(H / 'schematic.pdf'), pagesize=(1191, 842))
    pdf.setTitle('LED Study Timer Card')
    pdf.setFont('Helvetica-Bold', 20)
    pdf.drawString(30, 800, 'LED Study Timer Card - Electrical connection review')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(30, 778, 'NOT a KiCad schematic export. Open study-timer.kicad_sch for graphical schematic. ERC not run.')
    py = 750
    for c in design:
        sym = libs[c['symbol']]
        x, y = c['schematic']
        instid = uid()
        props = f'(property "Reference" "{c["ref"]}" (at {x} {y-5} 0) (effects (font (size 1 1)))) (property "Value" "{c["value"]}" (at {x} {y+5} 0) (effects (font (size 1 1))))'
        schematic.append(f'(symbol (lib_id "{c["symbol"]}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (uuid {instid}) {props} (instances (project "study-timer" (path "/{root}" (reference "{c["ref"]}") (unit 1)))))')
        seen = set()
        for pin in walk(sym, 'pin'):
            num = str(get(pin, 'number')[1])
            at = get(pin, 'at')
            px, pyin, angle = float(at[1]), float(at[2]), float(at[3])
            ax, ay = round(x+px, 4), round(y-pyin, 4)
            net = c['nets'].get(num)
            if (ax, ay) in seen:
                continue  # Stacked power pins share the same physical endpoint.
            seen.add((ax, ay))
            if not net:
                schematic.append(f'(no_connect (at {ax} {ay}) (uuid {uid()}))')
                continue
            ex = round(ax - 5.08*math.cos(math.radians(angle)), 4)
            ey = round(ay + 5.08*math.sin(math.radians(angle)), 4)
            schematic.append(f'(wire (pts (xy {ax} {ay}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid {uid()}))')
            schematic.append(f'(label "{net}" (at {ex} {ey} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid()}))')
        bx, by = c['pcb']
        # Deliberately a non-electrical placement envelope: no invented land patterns.
        board.append(f'(footprint "StudyTimer:REVIEW_ENVELOPE" (layer "F.Cu") (at {bx} {by}) (attr board_only exclude_from_pos_files exclude_from_bom) (fp_text reference "{c["ref"]}" (at 0 -2.5) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12)))) (fp_text value "{c["value"]}" (at 0 2.5) (layer "F.SilkS") hide (effects (font (size 0.6 0.6) (thickness 0.1)))) (fp_rect (start -2 -1.5) (end 2 1.5) (stroke (width 0.15) (type default)) (fill none) (layer "F.SilkS")))')
        text = c['ref'] + ' ' + c['value'] + ': ' + ', '.join(f'{k}={v or "NC"}' for k,v in c['nets'].items())
        if py < 45:
            pdf.showPage(); py = 790; pdf.setFont('Helvetica', 8)
        pdf.setFont('Helvetica', 8)
        # Wrap long pin maps without truncation.
        while text:
            pdf.drawString(30, py, text[:175]); text = text[175:]; py -= 12
        py -= 3
    pdf.save()
    for a,b in [((0,0),(85,0)),((85,0),(85,54)),((85,54),(0,54)),((0,54),(0,0))]:
        board.append(f'(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts"))')
    for text,x,y,layer,size in [('STUDY TIMER',42,7,'F.SilkS',2),('FOCUS > PHONE',42,27,'B.SilkS',2),('Harsh 2026',70,51,'F.SilkS',1),('PLACEMENT STUDY - NOT FOR FAB',42,40,'F.SilkS',1)]:
        mirror = ' (justify mirror)' if layer == 'B.SilkS' else ''
        board.append(f'(gr_text "{text}" (at {x} {y}) (layer "{layer}") (effects (font (size {size} {size}) (thickness 0.15)){mirror}))')
    (H / 'study-timer.kicad_sch').write_text('\n'.join(schematic) + '\n)\n')
    (H / 'study-timer.kicad_pcb').write_text('\n'.join(board) + '\n)\n')
    project = {'meta': {'filename':'study-timer.kicad_pro','version':1}, 'board': {'design_settings': {'defaults': {'track_width':0.25}, 'track_widths':[0.25,0.5], 'via_dimensions':[{'diameter':0.8,'drill':0.4}]}}, 'net_settings': {'classes':[{'name':'Default','clearance':0.2,'track_width':0.25,'via_diameter':0.8,'via_drill':0.4,'description':'Signals; route power at 0.5 mm'}], 'meta':{'version':3}}, 'schematic':{}, 'pcbnew':{}}
    (H / 'study-timer.kicad_pro').write_text(json.dumps(project, indent=2)+'\n')
    image = Image.new('RGB', (800,600), '#101a26')
    d = ImageDraw.Draw(image)
    d.text((40,22), 'LED STUDY TIMER CARD | PLACEMENT CONCEPT', fill='white')
    d.rounded_rectangle((60,80,740,512), radius=10, fill='#176253', outline='#c9dbca', width=3)
    for c in design:
        bx,by=c['pcb']; xx,yy=60+bx*8,80+by*8
        d.rectangle((xx-12,yy-8,xx+12,yy+8), fill='#242b32', outline='#b5c3c1')
        d.text((xx-14,yy+10), c['ref'],fill='white')
    d.text((300,108),'STUDY TIMER',fill='white')
    d.text((80,536),'NOT A PCB RENDER: no land patterns, copper, or routing yet.',fill='#ffc977')
    image.save(H/'pcb.png')
    print('Generated review files; native KiCad validation still required.')

if __name__ == '__main__':
    build()
