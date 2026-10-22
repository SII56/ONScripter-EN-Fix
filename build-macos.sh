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
for d in libogg-1.3.5 libvorbis-1.3.7; do
    if [ ! -f "$EXT/src/$d/configure" ] || [ "$EXT/src/$d/configure.ac" -nt "$EXT/src/$d/configure" ]; then
        echo "==> autoreconf $d"
        ( cd "$EXT/src/$d" && autoreconf -fi >/dev/null )
    fi
done

# SDL_ttf: 自带的 showfont 示例链接时缺 iconv 符号，configure 时补上 -liconv。
if [ ! -f "$EXT/lib/libSDL_ttf.a" ]; then
    echo "==> 构建 SDL_ttf"
    ( cd "$EXT/src/SDL_ttf-2.0.11" && rm -f Makefile &&
      ./configure --prefix="$EXT" --disable-shared LIBS="-liconv" >/dev/null &&
      make >/dev/null && make install >/dev/null )
fi

# SDL_image: 三个坑
#   1) 源码树里缺 IMG_ImageIO.m，必须 --disable-imageio
#   2) 默认探测不到 extlib 里的 libpng/libjpeg，加载器会被编译成空壳
#   3) IMG_png.c 与 libpng 1.6 的函数指针签名不兼容，要放宽检查
# 另外它的 Makefile 让示例先于静态库链接，所以只构建库本身。
if [ ! -f "$EXT/lib/libSDL_image.a" ]; then
    echo "==> 构建 SDL_image"
    ( cd "$EXT/src/SDL_image-1.2.12" && rm -f Makefile &&
      ./configure --prefix="$EXT" --disable-shared \
          --disable-imageio --disable-tif --disable-webp \
          --enable-png --disable-png-shared --enable-jpg --disable-jpg-shared \
          CPPFLAGS="-I$EXT/include" LDFLAGS="-L$EXT/lib" LIBS="-liconv" \
          CFLAGS="-O2 -Wno-incompatible-function-pointer-types -Wno-error" >/dev/null &&
      make libSDL_image.la >/dev/null &&
      cp .libs/libSDL_image.a "$EXT/lib/" &&
      cp SDL_image.h "$EXT/include/" &&
      cp SDL_image.h "$EXT/include/SDL/" 2>/dev/null || true )
fi

# 让 extlib 的规则认为这些库已经是最新的（否则会重新走一遍示例程序的构建）
touch "$EXT/lib/libSDL_ttf.a" "$EXT/lib/libSDL_image.a"

if [ ! -f Makefile ]; then
    echo "==> configure"
    ./configure
fi

echo "==> make"
make "$@"

echo
echo "完成: $ROOT/onscripter-en"
file "$ROOT/onscripter-en"
