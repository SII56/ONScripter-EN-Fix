#!/bin/bash
# build-macos.sh - 在 macOS 上构建 ONScripter-EN
# 用法: ./build-macos.sh [make 的额外参数]
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$PWD"
EXT="$ROOT/extlib"

# 用干净的 PATH。某些环境（IDE / 打包器）会在 PATH 前面塞带空格的 shim 目录，
# 那会让 autoconf 的 sed / ld 探测直接炸掉。
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PATH="/opt/homebrew/opt/libtool/libexec/gnubin:$PATH"

need=(sdl12-compat smpeg libogg libvorbis mad bzip2 jpeg dylibbundler autoconf automake libtool)
missing=()
for f in "${need[@]}"; do
    brew list --formula "$f" >/dev/null 2>&1 || missing+=("$f")
done
if [ ${#missing[@]} -gt 0 ]; then
    echo "==> 安装依赖: ${missing[*]}"
    brew install "${missing[@]}"
fi

# tarball 里带的 aclocal.m4 是按老 automake 生成的，和本机版本对不上会触发
# "aclocal-1.16: command not found"，所以先重新生成。
# 注意：新 clone 出来的树里 configure 和 configure.ac 时间戳相同，不能用 -nt 判断，
# 否则会跳过这一步然后在 make 阶段炸掉，这里无条件重跑（几秒钟的事）。
for d in libogg-1.3.5 libvorbis-1.3.7; do
    echo "==> autoreconf $d"
    ( cd "$EXT/src/$d" && autoreconf -fi >/dev/null )
done

# SDL_ttf / SDL_image 的特殊 configure 参数放在 Makefile.extlibs 里
# （见那边的 ifeq ($(SYS),MacOSX)），这里不再手工预构建，交给 make 的依赖顺序走。

if [ ! -f Makefile ]; then
    echo "==> configure"
    ./configure
fi

echo "==> make"
make "$@"

echo
echo "完成: $ROOT/onscripter-en"
file "$ROOT/onscripter-en"
