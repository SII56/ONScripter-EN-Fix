# macOS 构建说明（个人分支）

本仓库是 [Galladite27/ONScripter-EN](https://github.com/Galladite27/ONScripter-EN) 的个人分支，  
目标只有一个：**让 ONScripter-EN 在 macOS（Apple Silicon / Intel）上能编译、能跑**。

上游明确表示暂不支持 macOS 构建（README「Build Requirements」一节），  
其 `configure` 里的 Darwin 分支是 2000 年代 Xcode 时代的遗留物，已经不可用。  
本分支把这个分支修好，并让它走 insani 分支验证过的「sdl12-compat + 系统库」路线。

许可证保持 **GPL v2** 不变（见 `COPYING`）。

---

## 快速开始

```bash
brew install sdl12-compat smpeg libogg libvorbis mad bzip2 jpeg dylibbundler \
             autoconf automake libtool
./build-macos.sh
```

产物是同目录下的 `onscripter-en`（Mach-O arm64/x86_64）。

## 环境要求

- macOS 11+（本分支在 macOS 27 / arm64 上验证）
- Xcode Command Line Tools（`xcode-select --install`）
- Homebrew（Apple Silicon 默认 `/opt/homebrew`）

## 依赖说明

| 依赖                                           | 来源                      | 说明                                   |
| -------------------------------------------- | ----------------------- | ------------------------------------ |
| SDL 1.2                                      | Homebrew `sdl12-compat` | SDL2 之上的 1.2 ABI 兼容层，提供 `sdl-config` |
| SDL_image / SDL_mixer / SDL_ttf              | 仓库内置 `extlib/src`       | 用系统 `sdl-config` 编译，静态链接             |
| smpeg / freetype / bzip2                     | Homebrew                | 系统库                                  |
| libpng / libjpeg / zlib / libogg / libvorbis | 仓库内置                    | 静态链接                                 |

**注意**：Homebrew 已不再提供 `sdl_image` / `sdl_mixer` / `sdl_ttf` 这三个 SDL1.2 名字的 formula  
（现在只有 `sdl2_image` 等 SDL2 版本）。所以三个扩展库用仓库自带的 1.2 版本编译，  
这比引入 `sdl2_*`（会连带升级 freetype / harfbuzz / glib 等十几个包）干净得多。

---

## 相对上游的改动

只动了 5 个文件，全部是构建系统层面，**没有改任何引擎逻辑**：

### 1. `configure` — 给 Darwin 一个能用的分支

- 删除 `DEFS` 里的 `-DMACOSX`。这个宏会打开源码里 97 处 2006 年的 Cocoa 胶水代码  
  （`#import <Foundation/...>`、`cocoa_alertbox.h`），而 `macosx/*.mm` 从来没被任何 Makefile 编译过，  
  那套东西是死的。不定义它，代码走通用 POSIX 路径，和 insani 分支的做法一致。
- 删除 `-framework QuickTime`。该 framework 在 macOS 10.15 Catalina 已被移除。
- 补上 `-framework AudioToolbox -framework AudioUnit -framework CoreAudio`，  
  SDL_mixer 的 `native_midi_macosx.c` 需要它们（`NewMusicSequence` 等符号）。
- `$LINKz` 补进链接行，否则 libpng 的 `inflate` / `deflate` 找不到。
- 不再把 `X11_messagebox.cpp` 加入目标。该文件无条件 `#include <X11/Xlib.h>`，  
  而 macOS 没有 X11 头（除非装 XQuartz）。
- 让 macOS 也生成 `resources.h`（图标嵌入），否则 `ONScripterLabel.cpp` 的  
  `#include "resources.h"` 会失败。
- 去掉 `-fpascal-strings`。

### 2. `Makefile.extlibs` — BSD sed 兼容

两处 `sed -i` 改成 `perl -pi -e`。macOS 的 BSD sed 对 `-i` 的后缀参数处理与 GNU sed 不同，  
`sed -i -e ...` 会报 `invalid command code`。

### 3. `extlib/src/zlib-1.2.13/zutil.h`

`TARGET_OS_MAC` 在现代 macOS SDK 里恒为真，导致 zlib 把 `fdopen` 定义成 `NULL` 宏，  
和 SDK 的 `_stdio.h` 声明冲突。改为仅在 classic Mac 下生效。

### 4. `extlib/src/libpng-1.6.39/pngpriv.h`

同一类问题：`TARGET_OS_MAC` 为真时它会 `#include <fp.h>`，而 `fp.h` 在 macOS 26+ SDK 已删除。

### 5. `extlib/src/libvorbis-1.3.7/configure.ac`

删掉 `-force_cpusubtype_ALL`。这是 PowerPC 时代给 Xcode 用的链接参数，现代 `ld` 直接报  
`unknown options`。

---

## 已知限制

- **没有做 app bundle**。目前产物是裸二进制，存档默认写在游戏目录。  
  要做 `.app` 可以照抄 insani 分支的 `makedist.MacOSX.sh` + `-DAPPBUNDLE`。
- **没有代码签名 / 公证**。自己本机用 `codesign -s - onscripter-en` 即可；  
  对外分发需要 Apple 开发者账号（$99/年）+ notarytool。
- **MIDI**：走 SDL_mixer 的 native_midi_macosx（AudioToolbox），没有实测过 MIDI 游戏。
- **未跑过实际游戏**。目前只验证了二进制能启动、`--help` / `--version` 正常。
- **arm64 没有 SSE/MMX 加速**。`configure` 的 `ARCH` 检测只认 x86/x86_64/ppc，  
  Apple Silicon 落到 `unknown`，于是 `USE_CPU_GFX=false`，纯 C 路径。功能正常，只是慢一点。

## 与上游的关系

本分支**不打算向上游提 PR**，纯个人使用。上游的 macOS 支持由维护者自己规划，  
届时大概率也会走同样的「搬 insani 构建系统」路线。
