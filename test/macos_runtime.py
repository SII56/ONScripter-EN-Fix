#!/usr/bin/env python3
"""Exercise the real engine: transparency, sprite placement and save/load state."""
import argparse
import json
import os
import shutil
import uuid
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib


def png(path, width, height, pixel, channels=4):
    def chunk(tag, payload):
        return (struct.pack('>I', len(payload)) + tag + payload
                + struct.pack('>I', zlib.crc32(tag + payload) & 0xffffffff))
    raw = b''.join(b'\0' + b''.join(bytes(pixel(x, y)) for x in range(width))
                   for y in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack(
        '>IIBBBBB', width, height, 8, 6 if channels == 4 else 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def bmp_pixel(path, x, y):
    data = path.read_bytes()
    offset = struct.unpack_from('<I', data, 10)[0]
    width, height = struct.unpack_from('<ii', data, 18)
    bits = struct.unpack_from('<H', data, 28)[0]
    assert bits in (24, 32), (path, bits)
    stride = ((width * bits + 31) // 32) * 4
    row = height - 1 - y if height > 0 else y
    start = offset + row * stride + x * (bits // 8)
    b, g, r = data[start:start + 3]
    return r, g, b


def run(engine, game, saves, cwd, extra=(), isolated=False, timeout=30, default_save=False, auto_root=False):
    env = os.environ.copy()
    if isolated:
        env = {k: v for k, v in env.items() if not k.startswith(('DYLD_', 'SDL_'))}
        env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin', DYLD_PRINT_LIBRARIES='1')
    env.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
               SDL12COMPAT_OPENGL_SCALING='0')
    try:
        options = [] if default_save else ['--save', str(saves)]
        roots = [] if auto_root else ['--root', str(game)]
        result = subprocess.run([str(engine), *roots, *options,
                                 *extra], cwd=cwd, env=env, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        (saves / 'engine.log').write_bytes((error.stdout or b'') + (error.stderr or b''))
        raise
    (saves / 'engine.log').write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, (result.returncode, str(saves / 'engine.log'))
    if isolated:
        loaded = result.stderr.decode('utf-8', errors='replace')
        assert 'Frameworks/libSDL2' in loaded, 'Bundled SDL2 was not loaded'
        assert not any('/opt/homebrew/' in line or '/usr/local/' in line
                       for line in loaded.splitlines() if line.startswith('dyld[')), loaded


def dialogs(engine, root, isolated):
    game = root / 'dialogs'
    game.mkdir(exist_ok=True)
    (game / '0.utf').write_text('''*define
game
*start
yesnobox %0,"Please choose No. 中文测试","Dialog 1 of 5"
if %0!=0 goto *fail
yesnobox %0,"Please choose Yes.","Dialog 2 of 5"
if %0!=1 goto *fail
okcancelbox %0,"Please choose Cancel.","Dialog 3 of 5"
if %0!=0 goto *fail
okcancelbox %0,"Please choose OK.","Dialog 4 of 5"
if %0!=1 goto *fail
mesbox "中文测试・日本語テスト","Dialog 5 of 5"
getscreenshot 640,480
savescreenshot "dialog-pass.bmp"
end
*fail
getscreenshot 640,480
savescreenshot "dialog-fail.bmp"
end
''', encoding='utf-8')
    run(engine, game, game, root, isolated=isolated, timeout=180)
    assert (game / 'dialog-pass.bmp').exists(), str(game / 'engine.log')
    assert not (game / 'dialog-fail.bmp').exists()
    print('PASS: Yes, No, OK, Cancel and multilingual message box')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, default=Path('onscripter-en'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--isolated', action='store_true', help='Reject Homebrew library loads')
    parser.add_argument('--dialogs', action='store_true', help='Interactive native dialogs')
    args = parser.parse_args()
    engine = args.engine.resolve()
    root = args.output or Path(tempfile.mkdtemp(prefix='ons-runtime-'))
    root = root.resolve()
    if args.output and root.exists() and any(root.iterdir()):
        parser.error('Choose an empty output directory to avoid reusing test results')
    root.mkdir(parents=True, exist_ok=True)
    if args.dialogs:
        dialogs(engine, root, args.isolated)
        return
    game = root / 'game with spaces 日本語'
    game.mkdir(exist_ok=True)
    png(game / 'alpha.png', 32, 32,
        lambda x, y: (255, 0, 0, 255 if 8 <= x < 24 and 8 <= y < 24 else 0))
    png(game / 'key.png', 32, 32,
        lambda x, y: (255, 255, 0, 255) if 8 <= x < 24 and 8 <= y < 24
        else (255, 0, 255, 255))
    png(game / 'copy.png', 32, 32, lambda x, y: (0, 0, 255, 255))
    png(game / 'mask.png', 64, 32,
        lambda x, y: (0, 255, 0) if x < 32 else
        ((0, 0, 0) if 40 <= x < 56 and 8 <= y < 24 else (255, 255, 255)), channels=3)
    saves = root / 'sprites'
    saves.mkdir(exist_ok=True)
    (game / '0.txt').write_text('''*define
game
*start
bg #000000,1
lsp 0,":a;alpha.png",100,80
lsp 1,":l;key.png",200,80
lsp 2,":c;copy.png",300,80
lsp 3,":a;mask.png",400,80
print 1
getscreenshot 640,480
savescreenshot "sprites.bmp"
csp -1
ld c,":a;alpha.png",1
getscreenshot 640,480
savescreenshot "standing.bmp"
end
''')
    run(engine, game, saves, root, isolated=args.isolated)
    checks = [(100, 80, (0, 0, 0)), (108, 88, (255, 0, 0)),
              (200, 80, (0, 0, 0)), (208, 88, (255, 255, 0)),
              (300, 80, (0, 0, 255)), (400, 80, (0, 0, 0)),
              (408, 88, (0, 255, 0))]
    for x, y, expected in checks:
        actual = bmp_pixel(saves / 'sprites.bmp', x, y)
        assert actual == expected, ('sprite', x, y, actual, expected)
    assert bmp_pixel(saves / 'standing.bmp', 312, 456) == (255, 0, 0)
    assert bmp_pixel(saves / 'standing.bmp', 304, 448) == (0, 0, 0)
    results = ['RGBA alpha, color key, opaque copy, legacy mask, centered standing sprite']
    for nested in (False, True):
        saves = root / ('save-subdir' if nested else 'save-root')
        saves.mkdir(exist_ok=True)
        define = 'savedir "slots"\n' if nested else ''
        script = '''*define
DEFINEgame
*start
bg #112233,1
lsp 0,":a;alpha.png",100,80
print 1
mov %10,42
mov $10,"restored"
saveon
savegame 1
fileexist %20,"mutated.bmp"
if %20=1 goto *verify
mov %10,0
mov $10,"changed"
bg #000000,1
csp -1
print 1
getscreenshot 640,480
savescreenshot "mutated.bmp"
loadgame 1
*verify
if %10!=42 goto *fail
if $10!="restored" goto *fail
savefileexist %21,1
if %21!=1 goto *fail
savefileexist %21,2
if %21!=0 goto *fail
savegame 2
savefileexist %21,2
if %21!=1 goto *fail
savefileremove 2
savefileexist %21,2
if %21!=0 goto *fail
savefileremove 2
savetime 1,%22,%23,%24,%25
date %30,%31,%32
if %22!=%31 goto *fail
if %23!=%32 goto *fail
getscreenshot 640,480
savescreenshot "restored.bmp"
end
*fail
getscreenshot 640,480
savescreenshot "failed.bmp"
end
'''.replace('DEFINE', define)
        (game / '0.txt').write_text(script)
        run(engine, game, saves, root, isolated=args.isolated)
        assert not (saves / 'failed.bmp').exists(), str(saves / 'engine.log')
        target = saves / 'slots' if nested else saves
        assert (target / 'save1.dat').stat().st_size > 1000
        assert bmp_pixel(saves / 'restored.bmp', 108, 88) == (255, 0, 0)
        assert bmp_pixel(saves / 'restored.bmp', 0, 0) == (17, 34, 51)
        assert bmp_pixel(saves / 'mutated.bmp', 108, 88) == (0, 0, 0)
        results.append('save/load integer, string, background, sprite, existence and date: '
                       + ('savedir override' if nested else 'explicit save path'))
    # A new game must save outside its assets without requiring a --save option.
    gameid = 'ONSRuntime-' + uuid.uuid4().hex
    default_dir = Path.home() / 'Library/Application Support/ONScripter-EN' / gameid
    assert not default_dir.exists()
    (game / '0.txt').write_text('''*define
game
*start
savegame 1
savefileexist %0,1
if %0!=1 goto *fail
getscreenshot 640,480
savescreenshot "default-save-pass.bmp"
end
*fail
end
''')
    try:
        run(engine, game, default_dir, root, extra=('--gameid', gameid),
            isolated=args.isolated, default_save=True)
        assert (default_dir / 'save1.dat').stat().st_size > 1000
        assert (default_dir / 'default-save-pass.bmp').exists()
        shutil.copytree(default_dir, root / 'default-save-evidence')
    finally:
        # Only remove this run's UUID-named test directory.
        if default_dir.exists():
            shutil.rmtree(default_dir)
    results.append('default per-user save directory, no --save argument')
    if engine.parents[2].suffix == '.app':
        app = game / 'ONScripter-EN.app'
        shutil.copytree(engine.parents[2], app)
        adjacent_engine = app / 'Contents/MacOS/onscripter-en'
        plain_script = (game / '0.txt').read_bytes()
        (game / '0.txt').unlink()
        for entry in ('0.txt', '0.utf', 'nscript.dat'):
            payload = bytes(byte ^ 0x84 for byte in plain_script) if entry == 'nscript.dat' else plain_script
            (game / entry).write_bytes(payload)
            auto_saves = root / ('adjacent-' + entry)
            auto_saves.mkdir()
            # No --root, and cwd is deliberately outside the game folder.
            run(adjacent_engine, game, auto_saves, root, isolated=args.isolated, auto_root=True)
            assert (auto_saves / 'default-save-pass.bmp').exists()
            assert (auto_saves / 'save1.dat').exists()
            (game / entry).unlink()
        results.append('app beside 0.txt, 0.utf or nscript.dat starts without --root or a folder chooser')
    (root / 'results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps({'passed': results, 'output': str(root)}, indent=2))


if __name__ == '__main__':
    main()
