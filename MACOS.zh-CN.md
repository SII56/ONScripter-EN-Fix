# 在 macOS 上使用 ONScripter-EN

[English](MACOS.md)

这是 ONScripter-EN 的个人 macOS 移植，保留 `COPYING` 中的许可证，不向上游提交 PR。

## 使用独立应用包

解压后，把 `ONScripter-EN.app` 放到游戏入口脚本（如 `nscript.dat`、`0.txt` 或 `0.utf`）
所在的目录，双击应用即可直接启动该游戏。应用旁边找不到支持的脚本时，才弹出游戏文件夹选择框。
显式传入的 `--root` 始终优先。目标机器不需要安装
Homebrew、Python、Xcode 或 SDL 等运行库；游戏脚本和素材仍需自行提供。

应用包包含所有非系统动态库，包括兼容库动态加载的 SDL2，以及需要时的 SDL3。
打包过程会重写依赖路径、检查是否仍引用外部库，并在完成后进行临时签名。

不同架构需要分别构建。本机在 2026-10-22 生成的包是 **arm64，要求 macOS 27.0
或以上**，这是所用动态库的最低系统要求决定的。打包脚本会综合主程序和所有库，
将实际要求写入 `Contents/Info.plist`，不能直接宣称支持 macOS 11。
使用旧版 SDK 和兼容依赖重新构建可能降低要求，但尚未验证；本次也未验证 Intel。

应用没有公证。从其他机器获取后，macOS 可能要求用户按系统正常流程批准打开。

## 字体和存档

优先使用游戏自带的 `default.ttf`、`.ttc`、`.otf` 或 `.otc`。没有时通过 CoreText
寻找系统安装的 Hiragino Sans 字体（GBK 脚本优先使用系统华文黑体），不在应用包中复制或分发系统字体。
对于依赖固定字宽的脚本，仍建议使用适合该游戏的等宽 CJK 字体。

默认存档位置：

```text
~/Library/Application Support/ONScripter-EN/<游戏标识>/
```

`--save PATH` 可以指定其他位置，脚本中的 `savedir` 相对于该目录。
存档查询、时间显示和实际写入使用相同的路径。
原来游戏目录里的存档不会自动迁移：可以通过 `--save` 继续指定原目录，或自行复制到新位置。

也可以在终端运行：

```bash
"ONScripter-EN.app/Contents/MacOS/onscripter-en" --root "/path/to/game"
```

## 老中文移植版的兼容设置

引擎可直接读取 GBK 脚本，包括异或封装的 `nscript.dat`，不需要改写游戏文件。
GBK 使用与 CP932 相同的固定字宽排版；UTF-8 仍采用引擎原有的另一套像素排版。
只有整个脚本是有效 GBK、同时是无效 CP932 时才自动选 GBK；有歧义时保留 CP932。
显式 `.utf` 文件继续使用 UTF-8。

有歧义的游戏可以用 `--encoding gbk`，也可以在应用旁的 `ons.cfg` 中填写：

```ini
encoding=gbk
```

应用会读取自动发现的相邻游戏或手动选择的游戏目录中的 `ons.cfg`。
命令行显式参数优先于相邻游戏的配置。

部分移植版在 `transmode alpha` 下使用普通 RGB PNG。传统读取方式会把右半边
当作遮罩，导致图片被裁掉一半。对于这类游戏，在 `ons.cfg` 另加一行：

```ini
png-rgb-opaque
```

该选项按不透明整图读取 RGB PNG；RGBA PNG 仍使用自身透明通道。
它默认关闭，不影响其他游戏的传统遮罩行为。后指定的 `--force-png-nscmask`
可以覆盖它。真正使用右半遮罩的游戏不应开启此选项。

## 构建与打包

只有构建机器需要 Xcode Command Line Tools 和 Homebrew；脚本会检查并安装所需依赖。

```bash
./build-macos.sh -j4
make -j4 tools
make check
./package-macos.sh
```

产物位于 `dist/ONScripter-EN.app`。打包脚本拒绝覆盖已有应用，可传入其他输出位置：

```bash
./package-macos.sh "$PWD/dist/ONScripter-EN-next.app"
```

`build-macos.sh` 单独生成的裸程序仍依赖 Homebrew。复制或分发时应使用完整应用包。

## 验证方式与结果

```bash
python3 test/macos_runtime.py
python3 test/macos_encoding.py --engine dist/ONScripter-EN.app/Contents/MacOS/onscripter-en --isolated
python3 test/macos_runtime.py --engine dist/ONScripter-EN.app/Contents/MacOS/onscripter-en --isolated
python3 test/macos_runtime.py --engine dist/ONScripter-EN.app/Contents/MacOS/onscripter-en --isolated --dialogs
```

前两项无需手动输入；最后一项依次选择 No、Yes、Cancel、OK，再关闭中日文消息框。
`--output PATH` 可将日志与截图保留在指定空目录，否则使用临时目录。

本机已验证：

- 资源工具全部编译成功，现有 38 项单元测试通过。
- GBK／CP932 明文与封装脚本的字形和固定字宽像素一致，字符串与变量能存读档恢复，脚本文件保持不变。
- RGB PNG 整图兼容、传统遮罩覆盖选项，以及游戏旁配置与命令行优先级。
- 通过像素比对验证 RGBA 透明、颜色抠透明、不透明图片、传统右半遮罩和居中立绘。
- 存读档往返恢复整数、字符串、背景和精灵。
- 从不同工作目录启动时，存档存在性和真实月日查询正确；也覆盖了 `savedir` 子目录。
- 系统字体回退，以及含空格和日文的游戏路径。
- 应用放在游戏脚本旁时，无需 `--root`，从其他工作目录启动也能自动识别。
- 原生确认框的肯定、否定返回值，以及中日文消息显示。
- 从 PATH 中移除 Homebrew 后，应用包仍通过运行测试；加载日志确认使用包内库，没有加载 Homebrew 库。

CI 已加入工具构建、单元测试、应用打包和包内运行验证，上传产物为包含应用的 ZIP。
原生对话框需要手动验证。本地通过不代表已经运行了远程 CI。

## 实现说明与剩余限制

旧 `MACOSX` 宏继续关闭。新的 `MacOSSupport.mm` 独立提供现代系统对话框、游戏目录选择、
用户存档目录、打开网址和字体查找，不重新启用旧 Xcode 工程。
存档查询显式识别现代 macOS，工具链接也补上了 zlib。

此前的 Darwin 链接、内置 SDL_image/SDL_ttf 配置、BSD 文本处理兼容，以及
zlib/libpng/libvorbis 的 SDK 修补保留。`configure` 更新后，构建脚本会重新生成 Makefile。

RGBA 精灵应显式使用 `:a;` 标签；`:l;` 表示左上角颜色抠透明，`:c;` 表示不透明。
PNG alpha 命令行选项不会替代图片标签。`csp` 是清除精灵，`vsp` 是控制显隐，
`msp` 的位移参数是增量。

尚未验证完整商业游戏、实际音频听感、视频、MIDI 循环和长时间交互存读档菜单。
arm64 仍使用通用 C 图形路径；仅增加架构识别不会自动获得 NEON 加速。

当前 SMPEG 视频路径不支持 MP4 开场动画；出现提示并跳过开场动画，与文字乱码或 PNG 兼容问题无关。
