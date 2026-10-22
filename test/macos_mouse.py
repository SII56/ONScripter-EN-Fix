#!/usr/bin/env python3
"""Native-display regression for Retina mouse warps, including clipped edges.

Unlike dummy-driver tests, this moves the real pointer briefly. Run on a macOS
desktop; a headless CI runner does not establish Retina coverage.
"""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--engine', type=Path, required=True)
p.add_argument('--window-width', type=int)
args = p.parse_args()
engine = args.engine.resolve()
root = Path(tempfile.mkdtemp(prefix='ons-mouse-'))
points = [(156, 161), (156, 206), (156, 251), (156, 296), (156, 341),
          (156, 386), (780, 580), (799, 599), (1, 1), (401, 301), (156, 161)]
lines = [';mode800', '*define', 'caption "Mouse coordinate regression"',
         'game', '*start', 'bg black,1', 'wait 200']
for i, (x, y) in enumerate(points):
    lines += [f'movemousecursor {x},{y}', 'wait 50', 'getmousepos %0,%1',
              f'if %0<{x-2} goto *fail', f'if %0>{x+2} goto *fail',
              f'if %1<{y-2} goto *fail', f'if %1>{y+2} goto *fail']
lines += ['getscreenshot 800,600', 'savescreenshot "passed.bmp"', 'end',
          '*fail', 'getscreenshot 800,600', 'savescreenshot "failed.bmp"', 'end']
(root / '0.txt').write_text('\n'.join(lines) + '\n')
env = {k: v for k, v in os.environ.items() if k != 'SDL_VIDEODRIVER'}
env['SDL_AUDIODRIVER'] = 'dummy'
env['ONS_TRACE_BUTTON_NAV'] = '1'
command = [str(engine), '--root', str(root), '--save', str(root)]
if args.window_width:
    command += ['--window-width', str(args.window_width)]
result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=30)
(root / 'engine.log').write_bytes(result.stdout + result.stderr)
assert result.returncode == 0, str(root / 'engine.log')
assert (root / 'passed.bmp').exists() and not (root / 'failed.bmp').exists(), str(root)
report = {'passed': points, 'window_width': args.window_width, 'output': str(root)}
(root / 'results.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
