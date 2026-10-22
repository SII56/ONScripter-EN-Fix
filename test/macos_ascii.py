#!/usr/bin/env python3
"""Verify opt-in ASCII fitting without changing legacy text positions."""
import argparse
import json
import shutil
import struct
import tempfile
from pathlib import Path
from macos_runtime import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--engine', type=Path, default=Path('onscripter-en'))
parser.add_argument('--font', type=Path, default=Path('/System/Library/Fonts/STHeiti Light.ttc'))
parser.add_argument('--output', type=Path)
parser.add_argument('--isolated', action='store_true')
args = parser.parse_args()
engine = args.engine.resolve()
root = (args.output or Path(tempfile.mkdtemp(prefix='ons-ascii-'))).resolve()
if args.output and root.exists() and any(root.iterdir()):
    parser.error('Choose an empty output directory')
root.mkdir(parents=True, exist_ok=True)
source = '''*define
game
*start
bg black,1
setwindow 20,60,12,6,32,32,0,8,0,0,0,#999999,0,0,639,479
中W!w
getscreenshot 640,480
savescreenshot "wide.bmp"
textclear
中W中文il中!w
getscreenshot 640,480
savescreenshot "mixed.bmp"
textclear
中文中文中文中文中文中文中文!w
getscreenshot 640,480
savescreenshot "chinese.bmp"
textclear
lsp 0,":s/32,32,0;#ffffff中WMil中文",20,220
print 1
getscreenshot 640,480
savescreenshot "sprite.bmp"
end
'''
outputs = {}
for codec in ('gbk', 'cp932', 'utf8'):
    for fitted in (False, True):
        name = codec + ('-fit' if fitted else '-default')
        game = root / name
        game.mkdir()
        (game / 'default.ttc').symlink_to(args.font.resolve())
        entry = '0.utf' if codec == 'utf8' else '0.txt'
        (game / entry).write_bytes(source.encode(codec))
        extra = ['--encoding', codec]
        if fitted:
            extra.append('--fit-legacy-ascii')
        run(engine, game, game, root, extra=extra, isolated=args.isolated)
        outputs[name] = game

def pixels(path, x0, y0, x1, y1):
    data = path.read_bytes()
    offset = struct.unpack_from('<I', data, 10)[0]
    width, height = struct.unpack_from('<ii', data, 18)
    bits = struct.unpack_from('<H', data, 28)[0]
    assert bits in (24, 32)
    stride = ((width * bits + 31) // 32) * 4
    result = []
    for y in range(y0, y1):
        row = height - 1 - y if height > 0 else y
        for x in range(x0, x1):
            start = offset + row * stride + x * (bits // 8)
            b, g, r = data[start:start + 3]
            result.append((r, g, b))
    return result

for codec in ('gbk', 'cp932'):
    original = outputs[codec + '-default']
    fitted = outputs[codec + '-fit']
    assert (original / 'chinese.bmp').read_bytes() == (fitted / 'chinese.bmp').read_bytes()
    # The first Chinese cell is [20,52), and the W cell is [52,68).
    assert any(p != (0, 0, 0) for p in pixels(original / 'wide.bmp', 68, 60, 90, 100))
    assert all(p == (0, 0, 0) for p in pixels(fitted / 'wide.bmp', 68, 60, 90, 100))
    assert any(p != (0, 0, 0) for p in pixels(fitted / 'wide.bmp', 52, 60, 68, 100))
    # Chinese after W and narrow i/l retain their original pixel positions.
    assert pixels(original / 'mixed.bmp', 100, 60, 200, 100) == pixels(fitted / 'mixed.bmp', 100, 60, 200, 100)
    assert (original / 'sprite.bmp').read_bytes() != (fitted / 'sprite.bmp').read_bytes()
for shot in ('wide.bmp', 'mixed.bmp', 'chinese.bmp', 'sprite.bmp'):
    assert (outputs['gbk-fit'] / shot).read_bytes() == (outputs['cp932-fit'] / shot).read_bytes()
    assert (outputs['utf8-default'] / shot).read_bytes() == (outputs['utf8-fit'] / shot).read_bytes()

if engine.parents[2].suffix == '.app':
    game = root / 'adjacent-config'
    game.mkdir()
    shutil.copytree(engine.parents[2], game / 'ONScripter-EN.app')
    (game / 'default.ttc').symlink_to(args.font.resolve())
    (game / '0.txt').write_bytes(source.encode('gbk'))
    (game / 'ons.cfg').write_text('encoding=gbk\nfit-legacy-ascii\n')
    run(game / 'ONScripter-EN.app/Contents/MacOS/onscripter-en', game, game,
        root, isolated=args.isolated, auto_root=True)
    assert (game / 'wide.bmp').read_bytes() == (outputs['gbk-fit'] / 'wide.bmp').read_bytes()
results = ['wide ASCII fits its half-cell', 'Chinese wrapping and positions unchanged',
           'narrow letters unchanged', 'text sprites fitted', 'GBK/CP932 pixels match',
           'UTF-8 unchanged']
(root / 'results.json').write_text(json.dumps(results, indent=2))
print(json.dumps({'passed': results, 'output': str(root)}, indent=2))
