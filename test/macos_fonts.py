#!/usr/bin/env python3
"""Verify bundled font fallback, game font priority and explicit overrides."""
import argparse
import json
import tempfile
from pathlib import Path
from macos_runtime import run

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--engine', type=Path, required=True)
p.add_argument('--isolated', action='store_true')
args = p.parse_args()
engine = args.engine.resolve()
font = engine.parents[1] / 'Resources/Fonts/NotoSansMonoCJKsc-Regular.otf'
assert font.is_file(), font
root = Path(tempfile.mkdtemp(prefix='ons-fonts-'))
source = '''*define
game
*start
bg black,1
setwindow 20,100,20,4,24,24,0,2,0,0,0,#999999,0,0,639,479
中文繁體、日本語。WMil!w
getscreenshot 640,480
savescreenshot "text.bmp"
end
'''
images = {}
for name, supplied, explicit in (
        ('fallback', None, None),
        ('game-noto', font, None),
        ('game-own', Path('/System/Library/Fonts/STHeiti Light.ttc'), None),
        ('override', Path('/System/Library/Fonts/STHeiti Light.ttc'), font)):
    game = root / name
    game.mkdir()
    (game / '0.utf').write_text(source)
    if supplied:
        (game / 'default.otf').symlink_to(supplied)
    extra = ('--font', str(explicit)) if explicit else ()
    run(engine, game, game, root, extra=extra, isolated=args.isolated)
    log = (game / 'engine.log').read_text(errors='replace')
    assert ('Using the bundled fallback font:' in log) == (name == 'fallback')
    images[name] = (game / 'text.bmp').read_bytes()
assert images['fallback'] == images['game-noto'] == images['override']
assert images['fallback'] != images['game-own']
result = {'passed': ['bundled font without game font', 'game font takes priority',
                     'explicit font overrides game font'], 'output': str(root)}
(root / 'results.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
