#!/usr/bin/env python3
"""Check native GBK decoding without rewriting packed game files."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from macos_runtime import run, png

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--engine', type=Path, default=Path('onscripter-en'))
parser.add_argument('--font', type=Path, default=Path('/System/Library/Fonts/STHeiti Light.ttc'))
parser.add_argument('--output', type=Path)
parser.add_argument('--isolated', action='store_true')
args = parser.parse_args()
engine = args.engine.resolve()
root = (args.output or Path(tempfile.mkdtemp(prefix='ons-encoding-'))).resolve()
if args.output and root.exists() and any(root.iterdir()):
    parser.error('Choose an empty output directory')
root.mkdir(parents=True, exist_ok=True)
# All visible characters below exist in both CP932 and GBK. Their decoded pixels
# must match exactly, including fixed-cell positioning and automatic wrapping.
source = '''*define
caption "Encoding regression"
game
*start
bg #000000,1
setwindow 20,300,12,4,24,24,0,2,0,1,1,#999999,0,280,639,479
保存中文、月日時分。保存中文、月日時分。!w
getscreenshot 640,480
savescreenshot "text.bmp"
保存{$1,乗中文}!w
if $1!="乗中文" goto *fail
mov $0,"保存中文"
mov %10,42
saveon
savegame 1
fileexist %20,"mutated.bmp"
if %20=1 goto *verify
mov $0,"changed"
mov %10,0
getscreenshot 640,480
savescreenshot "mutated.bmp"
loadgame 1
*verify
if $0!="保存中文" goto *fail
if %10!=42 goto *fail
savefileexist %1,1
if %1!=1 goto *fail
getscreenshot 640,480
savescreenshot "roundtrip.bmp"
end
*fail
getscreenshot 640,480
savescreenshot "failed.bmp"
end
'''
cases = [
    ('cp932-text', 'cp932', '0.txt', '', ()),
    ('cp932-packed', 'cp932', 'nscript.dat', '', ()),
    ('gbk-auto-text', 'gbk', '0.txt', ';快进\n', ()),
    ('gbk-auto-packed', 'gbk', 'nscript.dat', ';快进\n', ()),
    ('gbk-explicit-text', 'gbk', '0.txt', '', ('--encoding', 'gbk')),
    ('gbk-explicit-packed', 'gbk', 'nscript.dat', '', ('--encoding', 'gbk')),
]
reference = None
results = []
for name, codec, entry, comment, extra in cases:
    game = root / name
    saves = root / (name + '-saves')
    game.mkdir(); saves.mkdir()
    (game / 'default.ttc').symlink_to(args.font.resolve())
    payload = (comment + source).encode(codec)
    if entry == 'nscript.dat':
        payload = bytes(byte ^ 0x84 for byte in payload)
    script = game / entry
    script.write_bytes(payload)
    before = hashlib.sha256(payload).hexdigest()
    run(engine, game, saves, root, extra=extra, isolated=args.isolated)
    assert before == hashlib.sha256(script.read_bytes()).hexdigest()
    assert not (saves / 'failed.bmp').exists(), str(saves / 'engine.log')
    assert (saves / 'roundtrip.bmp').exists(), str(saves / 'engine.log')
    bitmap = (saves / 'text.bmp').read_bytes()
    if reference is None:
        reference = bitmap
    assert bitmap == reference, ('Changed glyphs or fixed-cell layout', name)
    log = (saves / 'engine.log').read_text(errors='replace')
    expected = 'GBK' if codec == 'gbk' else 'CP932'
    assert 'Script encoding: ' + expected in log
    results.append(name)
# Opaque RGB PNG compatibility must not change the default mask interpretation.
game = root / 'rgb-png'
game.mkdir()
(game / 'default.ttc').symlink_to(args.font.resolve())
png(game / 'rgb.png', 64, 32, lambda x, y: (255, 0, 0) if x < 32 else (0, 255, 0), channels=3)
reference = None
masked = None
for name, tag, flags in (
    ('opaque-reference', 'c', ()),
    ('opaque-option', 'a', ('--png-rgb-opaque',)),
    ('legacy-default', 'a', ()),
    ('legacy-override', 'a', ('--png-rgb-opaque', '--force-png-nscmask'))):
    saves = root / name
    saves.mkdir()
    text = ';快进\n*define\ngame\n*start\nbg black,1\nlsp 0,":' + tag + ';rgb.png",20,30\nprint 1\ngetscreenshot 640,480\nsavescreenshot "rgb.bmp"\nend\n'
    (game / 'nscript.dat').write_bytes(bytes(byte ^ 0x84 for byte in text.encode('gbk')))
    run(engine, game, saves, root, extra=flags, isolated=args.isolated)
    bitmap = (saves / 'rgb.bmp').read_bytes()
    if name == 'opaque-reference':
        reference = bitmap
    elif name == 'opaque-option':
        assert bitmap == reference
    elif name == 'legacy-default':
        assert bitmap != reference
        masked = bitmap
    else:
        assert bitmap == masked
results.append('opaque RGB PNG option and explicit legacy-mask override')
# A positional game path must not swallow the option immediately following it.
saves = root / 'positional-root'
saves.mkdir()
run(engine, game, saves, root,
    extra=(str(game), '--png-rgb-opaque', '--encoding', 'gbk'),
    isolated=args.isolated, auto_root=True)
assert (saves / 'rgb.bmp').read_bytes() == reference
results.append('positional game path preserves following CLI options')
# Check errors before SDL starts, including options originating in ons.cfg.
option_values = ('--root', '--save', '--font', '--encoding', '--gameid',
                 '--registry', '--dll', '--cdnumber', '--audiobuffer',
                 '--audiodriver', '--fileversion', '--window-width',
                 '--nsa-offset', '--automode-time', '--key-exe')
for option in option_values:
    result = subprocess.run([str(engine), option], cwd=root, capture_output=True)
    assert result.returncode == 2, (option, result.returncode, result.stderr)
    assert b'requires a value' in result.stderr, (option, result.stderr)
config_error = root / 'config-error'
config_error.mkdir()
(config_error / 'ons.cfg').write_text('encoding\n')
result = subprocess.run([str(engine), '--version'], cwd=config_error, capture_output=True)
assert result.returncode == 2 and b'requires a value' in result.stderr
results.append('missing option values report errors for CLI and ons.cfg')
if engine.parents[2].suffix == '.app':
    app = game / 'ONScripter-EN.app'
    shutil.copytree(engine.parents[2], app)
    adjacent_engine = app / 'Contents/MacOS/onscripter-en'
    (game / 'ons.cfg').write_text('encoding=gbk\npng-rgb-opaque\n')
    for name, flags, expected in (
            ('adjacent-game-config', (), reference),
            ('command-line-override', ('--force-png-nscmask',), masked)):
        saves = root / name
        saves.mkdir()
        run(adjacent_engine, game, saves, root, extra=flags,
            isolated=args.isolated, auto_root=True)
        assert (saves / 'rgb.bmp').read_bytes() == expected
    results.append('adjacent ons.cfg is loaded; explicit CLI mask option takes priority')
(root / 'results.json').write_text(json.dumps(results, indent=2))
print(json.dumps({'passed': results, 'output': str(root)}, indent=2))
