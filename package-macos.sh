#!/bin/bash
# Build a relocatable app. Homebrew is needed here, never on the target machine.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
OUTPUT="${1:-$PWD/dist/ONScripter-EN.app}"
if [ -e "$OUTPUT" ]; then
    echo "Output already exists: $OUTPUT (choose a new output path)" >&2
    exit 1
fi
if [ ! -x onscripter-en ]; then
    echo "Run ./build-macos.sh first." >&2
    exit 1
fi
STAGING=$(mktemp -d "${TMPDIR:-/tmp}/ons-package.XXXXXX")
trap 'rm -rf "$STAGING"' EXIT
APP="$STAGING/ONScripter-EN.app"
CONTENTS="$APP/Contents"
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Frameworks" "$CONTENTS/Resources/Licenses"
cp onscripter-en "$CONTENTS/MacOS/onscripter-en"
cp macosx/ons-en.icns "$CONTENTS/Resources/ons-en.icns"
cp COPYING MACOS.md MACOS.zh-CN.md "$CONTENTS/Resources/"
mkdir -p "$CONTENTS/Resources/Fonts" "$CONTENTS/Resources/Licenses/NotoSansMonoCJK"
cp fonts/NotoSansMonoCJKsc-Regular.otf "$CONTENTS/Resources/Fonts/"
cp fonts/OFL.txt fonts/README.md "$CONTENTS/Resources/Licenses/NotoSansMonoCJK/"

# sdl12-compat loads SDL2 with dlopen; ordinary dependency scanners miss it.
cp "$(brew --prefix sdl2)/lib/libSDL2-2.0.0.dylib" "$CONTENTS/Frameworks/"
install_name_tool -id '@executable_path/../Frameworks/libSDL2-2.0.0.dylib' \
    "$CONTENTS/Frameworks/libSDL2-2.0.0.dylib"
BUNDLE_ARGS=(-b -cd -of -ns -x "$CONTENTS/MacOS/onscripter-en"
    -x "$CONTENTS/Frameworks/libSDL2-2.0.0.dylib"
    -d "$CONTENTS/Frameworks" -p '@executable_path/../Frameworks/')
LICENSE_FORMULAS=(sdl12-compat sdl2 smpeg freetype libpng)
# Some SDL2 installations are sdl2-compat and dlopen SDL3 in turn.
if strings "$CONTENTS/Frameworks/libSDL2-2.0.0.dylib" | grep 'SDL2COMPAT_NO_UNLOAD' >/dev/null; then
    cp "$(brew --prefix sdl3)/lib/libSDL3.dylib" "$CONTENTS/Frameworks/"
    install_name_tool -id '@executable_path/../Frameworks/libSDL3.dylib' \
        "$CONTENTS/Frameworks/libSDL3.dylib"
    BUNDLE_ARGS+=(-x "$CONTENTS/Frameworks/libSDL3.dylib")
    LICENSE_FORMULAS+=(sdl3)
fi
dylibbundler "${BUNDLE_ARGS[@]}"

for formula in "${LICENSE_FORMULAS[@]}"; do
    formula_path=$(brew --prefix "$formula")
    mkdir -p "$CONTENTS/Resources/Licenses/$formula"
    for name in LICENSE LICENSE.txt LICENSE.TXT COPYING; do
        if [ -f "$formula_path/$name" ]; then
            cp "$formula_path/$name" "$CONTENTS/Resources/Licenses/$formula/"
        fi
    done
    cp "$formula_path/INSTALL_RECEIPT.json" "$CONTENTS/Resources/Licenses/$formula/"
done
for source in SDL_image-1.2.12 SDL_mixer-1.2.12 SDL_ttf-2.0.11 libogg-1.3.5 libvorbis-1.3.7 zlib-1.2.13 jpeg-9f; do
    mkdir -p "$CONTENTS/Resources/Licenses/$source"
    for name in COPYING LICENSE README; do
        if [ -f "extlib/src/$source/$name" ]; then
            cp "extlib/src/$source/$name" "$CONTENTS/Resources/Licenses/$source/"
        fi
    done
done

# Derive the minimum OS from the actual binary and every bundled library.
python3 - "$CONTENTS" <<'PY'
import plistlib
from pathlib import Path
import re
import subprocess
import sys
contents = Path(sys.argv[1])
minimum = (11, 0)
files = [contents / 'MacOS/onscripter-en', *sorted((contents / 'Frameworks').glob('*.dylib'))]
for path in files:
    commands = subprocess.check_output(['otool', '-l', str(path)], text=True)
    # Only minos and LC_VERSION_MIN_MACOSX describe deployment requirements.
    for block in commands.split('Load command '):
        if 'LC_BUILD_VERSION' in block:
            match = re.search(r'minos\s+(\d+(?:\.\d+)+)', block)
        elif 'LC_VERSION_MIN_MACOSX' in block:
            match = re.search(r'version\s+(\d+(?:\.\d+)+)', block)
        else:
            continue
        if match:
            minimum = max(minimum, tuple(map(int, match.group(1).split('.'))))
    deps = subprocess.check_output(['otool', '-L', str(path)], text=True).splitlines()[1:]
    for dep in deps:
        name = dep.strip().split(' (compatibility version')[0]
        assert name.startswith(('/usr/lib/', '/System/Library/', '@executable_path/../Frameworks/')), (path, name)
        if name.startswith('@executable_path/'):
            assert (contents / 'MacOS' / name[len('@executable_path/'):]).exists(), (path, name)
info = dict(CFBundleExecutable='onscripter-en', CFBundleIdentifier='org.onscripter.en.macos',
            CFBundleName='ONScripter-EN', CFBundleDisplayName='ONScripter-EN',
            CFBundlePackageType='APPL', CFBundleIconFile='ons-en.icns',
            CFBundleVersion='1', CFBundleShortVersionString='0.1.0',
            NSHighResolutionCapable=True, LSMinimumSystemVersion='.'.join(map(str, minimum)))
with (contents / 'Info.plist').open('wb') as out:
    plistlib.dump(info, out)
print('Minimum macOS:', info['LSMinimumSystemVersion'])
print('Verified bundled dependencies:', len(files))
PY
for library in "$CONTENTS/Frameworks/"*.dylib; do
    codesign --force --sign - "$library"
done
codesign --force --sign - "$APP"
codesign --verify --deep --strict "$APP"
mkdir -p "$(dirname "$OUTPUT")"
ditto "$APP" "$OUTPUT"
echo "App ready: $OUTPUT"
