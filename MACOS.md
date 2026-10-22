# Building on macOS (personal fork)

[中文说明](MACOS.zh-CN.md)

This is a personal fork of [Galladite27/ONScripter-EN](https://github.com/Galladite27/ONScripter-EN)
with exactly one goal: **make ONScripter-EN compile and run on macOS** (Apple Silicon and Intel).

Upstream does not support macOS builds (see its README, "Build Requirements"), and the
Darwin branch in its `configure` is a leftover from the 2000s Xcode port that no longer
works. This branch repairs that path and follows the route already proven by the sister
project `onscripter-insani`: `sdl12-compat` plus system libraries.

The license stays **GPL v2** (see `COPYING`).

---

## Quick start

```bash
brew install sdl12-compat smpeg libogg libvorbis mad bzip2 jpeg dylibbundler \
             autoconf automake libtool
./build-macos.sh
```

The result is `onscripter-en` in the same directory (Mach-O arm64 or x86_64).

## Requirements

- macOS 11 or later (this branch was verified on macOS 27 / arm64)
- Xcode Command Line Tools (`xcode-select --install`)
- Homebrew (on Apple Silicon this lives in `/opt/homebrew`)

## Dependencies

| Dependency | Source | Notes |
|---|---|---|
| SDL 1.2 | Homebrew `sdl12-compat` | 1.2 ABI shim on top of SDL2; provides `sdl-config` |
| SDL_image / SDL_mixer / SDL_ttf | vendored in `extlib/src` | built against the system `sdl-config`, linked statically |
| smpeg / freetype / bzip2 | Homebrew | system libraries |
| libpng / libjpeg / zlib / libogg / libvorbis | vendored | linked statically |

Note: Homebrew no longer ships `sdl_image` / `sdl_mixer` / `sdl_ttf` (the SDL 1.2-era
formula names); only the SDL2 variants such as `sdl2_image` remain. Building the vendored
1.2 versions is also much cleaner than pulling in `sdl2_*`, which drags in upgrades of
freetype, harfbuzz, glib and a dozen other packages.

---

## Changes relative to upstream

Everything below is build-system level. **No engine logic was touched.**

### 1. `configure` - give Darwin a working branch

- Drop `-DMACOSX` from `DEFS`. That macro enables ~97 blocks of 2006-era Cocoa glue
  (`#import <Foundation/...>`, `cocoa_alertbox.h`), and the `.mm` files under `macosx/`
  have never been compiled by any makefile, so the whole thing is dead. Without the
  macro the code takes the generic POSIX path, the same way `onscripter-insani` does.
- Drop `-framework QuickTime`; that framework was removed in macOS 10.15 Catalina.
- Add `-framework AudioToolbox -framework AudioUnit -framework CoreAudio`, needed by
  SDL_mixer's `native_midi_macosx.c` (`NewMusicSequence` and friends).
- Add `$LINKz` to the link line, otherwise libpng's `inflate` / `deflate` are unresolved.
- Delete `X11_messagebox.cpp` and its hook in `configure`. That file includes
  `<X11/Xlib.h>` unconditionally, and macOS has no X11 headers unless XQuartz is installed.
- Generate `resources.h` on macOS too, otherwise `ONScripterLabel.cpp` fails on
  `#include "resources.h"`.
- Drop `-fpascal-strings`.

### 2. `Makefile.extlibs` - BSD sed compatibility

Two `sed -i` calls became `perl -pi -e`. BSD sed on macOS handles the `-i` suffix argument
differently from GNU sed, so `sed -i -e ...` fails with `invalid command code`.

### 3. `extlib/src/zlib-1.2.13/zutil.h`

`TARGET_OS_MAC` is always true on modern macOS SDKs, which makes zlib define `fdopen` as a
macro and collide with the declaration in the SDK's `_stdio.h`. Restrict it to classic Mac.

### 4. `extlib/src/libpng-1.6.39/pngpriv.h`

Same root cause: with `TARGET_OS_MAC` true it includes `<fp.h>`, which was removed from
recent SDKs.

### 5. `extlib/src/libvorbis-1.3.7/configure.ac`

Drop `-force_cpusubtype_ALL`. It is a PowerPC-era linker flag for Xcode and modern `ld`
rejects it with `unknown options`.

---

## Running a game

As with upstream, the game directory **must** contain a font file
(`default.ttf` / `.ttc` / `.otf` / `.otc`).

Note that ONScripter-EN has **no** macOS system font fallback (only `onscripter-insani`
does, using Hiragino Maru Gothic). Without a font it exits with
`no font file detected; exiting`. For a quick test:

```bash
cp "/System/Library/Fonts/Supplemental/AppleGothic.ttf" <game dir>/default.ttf
```

For Japanese games, prefer a monospaced CJK font (Genjyuu Gothic X Monospace, Migu 2M,
Sazanami Gothic).

## What has been verified

- `--help` and `--version` work
- a minimal script (`*define` / `game` / one line of text) parses, runs and exits cleanly
- SDL video init (via `sdl12-compat`), font loading and script parsing all work
- **no full game has been played yet**; audio, video, save/load and the system menu are untested

## Known limitations

- **No app bundle.** The output is a bare binary and saves go into the game directory.
  For a `.app`, copy `makedist.MacOSX.sh` and `-DAPPBUNDLE` from `onscripter-insani`.
- **No code signing or notarization.** `codesign -s - onscripter-en` is enough for local
  use; distributing to others needs an Apple Developer account ($99/year) plus `notarytool`.
- **MIDI** goes through SDL_mixer's `native_midi_macosx` (AudioToolbox) and has not been
  tested with a MIDI-heavy game.
- **No SSE/MMX acceleration on arm64.** `configure`'s `ARCH` detection only knows
  x86/x86_64/ppc, so Apple Silicon falls through to `unknown`, which sets
  `USE_CPU_GFX=false` and takes the plain C path. Correct, just slower.

## Relationship to upstream

This branch is personal and **will not be sent upstream as a PR**. macOS support is on the
maintainers' own roadmap, and they will most likely take the same route of porting
`onscripter-insani`'s build system.
