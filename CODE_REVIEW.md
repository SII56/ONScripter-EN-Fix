# Engine review: 2026-10-22

This review covers the engine's startup, encoding, text and menus, resource loading,
save queries, macOS integration, build and distribution paths. It includes focused
source inspection and executable regression tests; it is not an exhaustive audit
of every engine command or the vendored third-party libraries.

## Changes included

- Modern macOS native services and relocatable application packaging, including
  the SDL libraries loaded indirectly at runtime.
- Save queries use the writer's actual directory and timestamps on macOS.
  Save-path results now own their strings, removing an allocation leaked by every
  successful query and by repeated save/load-menu visits.
- Native GBK decoding, conservative detection and explicit per-game selection;
  legacy character-cell positioning, numbers, captions and native dialogs.
- Built-in Japanese menu prompts are transcoded for both GBK and UTF-8 scripts.
- Inline temporary string assignments inspect the current character's byte count,
  including GBK characters whose second byte equals a backslash. Truncated strings
  report an error rather than reading across the line boundary.
- Character-width counting stops at a terminating NUL even for incomplete input;
  token skipping also stops at end of script.
- Every existing CLI option requiring a value now checks for a missing value;
  a positional game directory no longer skips the following option.
- Captions use a dynamically sized conversion result instead of manually sized
  intermediate buffers. Invalid caption text falls back to the engine name.
- RGB PNG compatibility remains an explicit game option; traditional half-image
  masks are covered by regression tests and remain the default.

## Verification

`make check` runs 38 unit tests. `test/macos_runtime.py` covers sprite transparency,
placement, state restoration, save existence/timestamps, per-user saves and app
startup beside a game. `test/macos_encoding.py` compares CP932 and GBK pixels for
plain and packed scripts, checks inline string assignments and save/load, verifies
RGB PNG modes and config precedence, and checks missing CLI/config values.
Packaged tests use loader diagnostics to reject Homebrew library dependencies.

The GitHub workflow performs the noninteractive build, unit tests, packaging and
isolated runtime tests. Native dialog interaction remains a manual check.

## Recommended follow-up work

1. **Archive and script robustness.** Add malformed/truncated archive fixtures and
   fuzzing before changing the old parsers. In particular, `SarReader::readArchive`
   has filename loops without explicit destination bounds or EOF checks. This
   needs a dedicated change covering SAR, NSA and NS2 and callers' error handling.
2. **Resource filenames.** Carry the selected script encoding into resource path
   normalization and filesystem lookup. `DirectReader` still contains CP932-specific
   byte handling. GBK text support does not establish full support for Chinese
   resource filenames, either inside archives or on the filesystem.
3. **Text layout.** Unify byte traversal and separate character decoding from
   measurement. UTF-8 currently has different layout rules and some older wrapping
   code still needs dedicated ruby, punctuation and variable-width font fixtures.
4. **Video.** Replace or supplement SMPEG for MP4 games. This requires a decoder,
   licensing and packaging decisions, and audio/video synchronization testing.
5. **Build portability.** Validate a clean build on older macOS and Intel. Local
   libraries currently require macOS 27; changing a deployment flag alone does not
   lower library requirements. Test other platforms before claiming GBK portability.
6. **Graphics performance.** Profile representative scenes before adding ARM SIMD.
   Prioritize measured resize/blend bottlenecks and compare exact output pixels;
   architecture recognition alone does not implement NEON acceleration.

Keep game assets, system fonts, generated app bundles and test output outside the
source commit. Synthetic regression fixtures are generated at test time.
