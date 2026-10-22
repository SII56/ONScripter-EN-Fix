# ONScripter-EN on macOS

[中文说明](MACOS.zh-CN.md)

This personal fork ports ONScripter-EN to modern macOS. It retains the original
license in `COPYING` and is not intended as an upstream pull request.

## Use the standalone app

Unzip the packaged app and place `ONScripter-EN.app` beside the game's entry script
(such as `nscript.dat`, `0.txt` or `0.utf`). Double-click the app to start that game.
If no supported script is found beside the app, it opens a game-folder chooser.
An explicit `--root` always takes priority.
The target machine needs no Homebrew, Python, Xcode, or separately installed SDL
libraries. Game scripts and assets are still required.

The app contains its non-system dynamic libraries, including SDL2 and, where
needed, SDL3, which compatibility libraries load dynamically. The package checks
library paths and applies an ad-hoc signature after relocation.

Packages are architecture-specific. The package built locally on 2026-10-22 is
**arm64 and requires macOS 27.0 or later**, because of the deployment requirements
of its libraries. `Contents/Info.plist` records the actual minimum OS, calculated
from the executable and all bundled libraries. Do not assume macOS 11 support.
Building with an older compatible SDK and dependencies may lower this requirement;
that has not been verified. Intel builds have not been verified here.

The app is not notarized. macOS may require the normal user approval for an
unnotarized application obtained from another machine.

## Fonts and saved games

Game-provided `default.ttf`, `.ttc`, `.otf`, or `.otc` files take priority. If none
is present, the engine uses the installed Hiragino Sans font through CoreText (STHeiti for GBK scripts).
No system fonts are copied into the package. Use a game-appropriate monospaced CJK
font when its script depends on fixed character widths.

The default save location is:

```text
~/Library/Application Support/ONScripter-EN/<game identifier>/
```

An explicit `--save PATH` overrides this location. A script's `savedir` is relative
to it. Save-slot existence and timestamps use the same directory as the writer.
Existing saves in a game directory are not migrated automatically: use `--save`
with that directory to continue using them, or copy the saves to the new location.

The command-line executable remains usable:

```bash
"ONScripter-EN.app/Contents/MacOS/onscripter-en" --root "/path/to/game"
```

## Legacy Chinese ports

The engine reads GBK scripts directly, including XOR-packed `nscript.dat`. It does
not transcode or rewrite the game's files. GBK uses the same fixed character-cell
layout as CP932; UTF-8 retains the engine's separate pixel-based layout.
Automatic detection chooses GBK only when the whole script is valid GBK and
invalid CP932. Ambiguous scripts retain CP932. Explicit `.utf` scripts remain UTF-8.
For an ambiguous game, use `--encoding gbk` or put this in `ons.cfg` beside the app:

```ini
encoding=gbk
```

Game-local `ons.cfg` is loaded when an adjacent game is detected, or after choosing
a game folder. Command-line options override adjacent-game defaults.

Some ports use ordinary, opaque RGB PNGs under `transmode alpha`. The traditional
interpretation treats the right half as a mask, cropping such images to half width.
For these games, add this separate, opt-in compatibility setting to `ons.cfg`:

```ini
png-rgb-opaque
```

RGBA PNGs continue to use their alpha channels. Defaults for other games remain
unchanged, and a later `--force-png-nscmask` overrides this setting. Do not enable
it for games that intentionally store right-half masks in RGB PNGs.

## Optional legacy English glyph fitting

GBK and CP932 scripts reserve half a character cell for each ASCII letter. Some
game fonts have wider proportional letters such as W and M, which can overlap.
Use `--fit-legacy-ascii`, or add `fit-legacy-ascii` to the game's `ons.cfg`, to
horizontally fit overflowing printable ASCII glyphs inside their existing cells.
This is an engine setting; scripts, font files and archives need no conversion.

This opt-in mode preserves character positions, wrapping, menu/button geometry,
Chinese glyphs and narrow ASCII glyphs. Wide letters become narrower; this is
cell fitting rather than proportional English typesetting. Horizontal legacy text
and text sprites are supported; UTF-8 and vertical text keep their existing behavior.
Fitted antialiased glyph masks are cached by font, character and available width.

Verify it with `python3 test/macos_ascii.py`; `--engine`, `--isolated`, `--font`
and `--output` work as in the other runtime checks.

## Build and package

Building requires Xcode Command Line Tools and Homebrew. These are developer
requirements only. The script checks and installs its Homebrew dependencies.

```bash
./build-macos.sh -j4
make -j4 tools
make check
./package-macos.sh
```

The package is written to `dist/ONScripter-EN.app`. To preserve existing output,
packaging refuses to overwrite an existing app; pass another output path if needed:

```bash
./package-macos.sh "$PWD/dist/ONScripter-EN-next.app"
```

The bare executable produced by `build-macos.sh` still references Homebrew.
Distribute the complete packaged app, not that bare executable.

## Verification

```bash
python3 test/macos_runtime.py
python3 test/macos_encoding.py --engine dist/ONScripter-EN.app/Contents/MacOS/onscripter-en --isolated
python3 test/macos_runtime.py --engine dist/ONScripter-EN.app/Contents/MacOS/onscripter-en --isolated
python3 test/macos_runtime.py --engine dist/ONScripter-EN.app/Contents/MacOS/onscripter-en --isolated --dialogs
```

The first two commands run without manual input. `--dialogs` requires choosing
No, Yes, Cancel, OK, then dismissing a multilingual message. `--output PATH` keeps
evidence in a specified empty directory; otherwise a temporary directory is used.

Verified locally:

- All resource tools compile; 38 unit tests pass.
- GBK/CP932 text and packed scripts produce identical fixed-cell glyph pixels;
  both preserve strings and variables through save/load without changing script files.
- Opaque RGB PNG compatibility, legacy-mask override and adjacent-game config precedence.
- Pixel checks for RGBA alpha, color key, opaque copy, traditional right-half masks,
  and centered standing sprites.
- Save/load restores integer and string variables, background and sprite state.
- Save-slot presence and actual month/day, including a `savedir` override, from a
  working directory different from the game and save directories.
- System-font fallback and paths containing spaces and Japanese characters.
- App placed beside game scripts starts without `--root`, from an unrelated working directory.
- Native Yes/No and OK/Cancel return values, plus Chinese/Japanese message text.
- Packaged runtime passes with Homebrew removed from PATH; loader diagnostics
  confirm bundled libraries are used and no Homebrew library is loaded.

The CI workflow builds tools, runs unit tests, packages the app, runs the bundled
runtime regression and uploads a ZIP containing the app. Interactive dialog checks
are manual. Local success does not imply a remote CI run has already completed.

## Implementation and remaining limits

The obsolete `MACOSX` macro remains disabled. A small independent Objective-C++
bridge (`MacOSSupport.mm`) provides current native dialogs, game-folder selection,
user save directories, URL opening and font lookup without reviving the old Xcode
project. Save-file queries explicitly recognize modern macOS. The macOS tool link
line includes zlib as well as libpng.

The earlier build fixes remain: modern Darwin framework linkage, vendored
SDL_image/SDL_ttf configure flags, BSD-compatible text substitutions, and small
zlib/libpng/libvorbis SDK compatibility changes. `build-macos.sh` refreshes its
Makefile when `configure` changes.

Use an explicit `:a;` tag for RGBA sprites, `:l;` for top-left color key and `:c;`
for opaque images. A PNG-alpha option does not change a sprite's transparency tag.
`csp` clears sprites, `vsp` controls visibility, and `msp` moves by an offset.

A full commercial game, audible audio, video, MIDI looping and prolonged interactive
save/load-menu use have not been verified. arm64 uses the generic C graphics path;
recognizing the architecture alone would not add NEON acceleration.

The current SMPEG video path does not decode MP4 opening movies. A warning and a
skipped opening movie are separate from text or PNG compatibility.
