# Development

Python 3.11+ is sufficient for packaging; Blender supplies its own Python for
integration. Runtime requires Blender 5.2+. No pip packages are needed.

```sh
python tools/quick_check.py
python tools/build.py --blender /path/to/blender
python tests/run_checks.py --blender /path/to/blender
python tests/run_gui_checks.py --blender /path/to/blender
```

On Windows, pass the full path to `blender.exe` as a quoted argument. The build
produces `dist/pipeworks-0.5.1.zip` and `dist/SHA256SUMS.txt`. ZIP timestamps,
permissions, order, and compression are fixed; repeated builds with the same
Python/zlib toolchain compare byte for byte. Compression bytes can differ between
toolchain versions. Release 0.2.0 uses Blender's bundled Python 3.13.13.
The portable CI checks syntax, manifest/product metadata, standalone scope,
source/archive parity, and reproducibility. CI does not launch a Blender GUI.

The integration runner uses local ignored profiles under `verification/line-pipe/`.
It creates CONFIG, SCRIPTS, and EXTENSIONS before launching, validates the actual
config path in the install test, installs the real archive, and starts a second
process to check saved language and independent RGBA preferences, then restores
English and default white/yellow colors. It does not edit the user's regular
Blender settings.

The GUI runner starts five separate disposable windows with pre-created isolated
profiles and a 180-second process timeout. It installs the release ZIP for the
interaction suite and checks the Ctrl+P selector and native Parent restoration, six
axes, repeated native orbit/pan/zoom/Alt+MMB and continuation, bend guides, follow toggle,
stable scaling, edge wrapping, compact single/adjacent bends, cancellation and the
existing drawing regression. Idle/active arrow draw calls and screenshots verify
white/yellow defaults, live custom RGBA shared across screen/world guides, reset,
and manual-mode start/tip anchoring. Three enable/disable cycles check keymap cleanup.
A dedicated installed-ZIP navigation suite measures exact 50% extension/retraction during native orbit, pan and drag zoom, restores normal speed after release, retains the first axis, and disables the add-on during a drag to check cleanup.
The Alt navigation suite covers left/middle/right native navigation under custom
Blender bindings and Industry Compatible, Follow Tip, releasing Alt before the
mouse, waiting for a start, bends, port picking and unmodified right-mouse cancel.
Use `--only alt-navigation` or `--only navigation alt-navigation` on the GUI runner
to select those suites.
Turn-pointer checks cover outside-viewport recovery, hidden guides, repeated key presses, current-tip targeting and continued extension without a length jump.
Native event simulation suppresses OS pointer events, so the test feeds the
requested cursor-warp destination back through Blender's event queue explicitly.
Use `tests/manual_interaction.py` without `--enable-event-simulate` to inspect the
actual installed ZIP with hardware input. Create its CONFIG/SCRIPTS/EXTENSIONS
folders under `verification/manual-interaction/` before launch. It uses only a
disposable scene and writes a local state receipt for manual inspection.

`tests/check_compact_bends.py` is part of the background runner. It checks single,
S, U, spatial, signed and rotated bends near the pipe-radius boundary; cap centers,
normals and diameters; positive solid volume; oriented manifold edges; zero-area
faces; nonadjacent triangle intersections; radius fitting, rollback and save/rebuild.
Its generated geometry and receipts stay under ignored `verification/line-pipe/`.

`tests/check_connections.py` checks whole-group docking, all four endpoint pairs,
roll, smooth/angular and spatial bridges, copied-Mesh repair, old ports, missing
Mesh records, rotated group curvature, atomic failure and save/reopen. A fresh
installed-ZIP process then opens its source-authored scene and checks link/object
pointers, occupancy, native Mesh parameters and bridge updates. The GUI connection
suite covers port picking, roll preview/cancel/confirm, native Undo/Redo for all
three operations, the context menu, language and modal cleanup. Use
`tests/gui_connections.py -- --manual` without event simulation for Windows input.

`tests/check_profiles.py` verifies real ring counts, ordered profile matching,
edge-phase alignment, hollow thickness, ten authored ports and single-fitting
export/import, variant selection and missing-size rollback. Native connection
checks cover authored P1/P2 mouths, consecutive fittings and bilingual prompt
copying with clipboard restoration. They use disposable isolated libraries.

For a native event-queue regression test, launch `tests/gui_line_pipe.py` with
Blender's `--enable-event-simulate` and pass `-- --six-axis`. First create the
three profile folders under `verification/line-pipe/six-axis-ui/` and point
`BLENDER_USER_CONFIG`, `BLENDER_USER_SCRIPTS`, and `BLENDER_USER_EXTENSIONS` to them.
That test starts with a self-authored disposable scene. Its orthographic diagnostic
images are not public presentation images. Use `tools/capture_preview.py` for the
wide perspective release visuals.

Generate an example in an isolated factory-startup process with
`--python tools/build_example.py`. It writes `examples/pipeworks-example.blend`.
`--python tools/build_connection_example.py` generates the self-authored
`examples/pipeworks-connections-0.4.0.blend`: direct roll, smooth/angular bridges,
rotated matched groups and a free trial pair. Inspect a fresh installed-ZIP restart
before supplying that scene.
Examples, verification output, profiles, installers, and publishing receipts are
ignored. Only this repository's 16-file `line_pipe/` extension is packaged.

## Release Procedure

1. Check the current source and supported Blender version.
2. Run package, integration, actual-install, and needed interactive checks.
3. Build and inspect wide non-isometric perspective images from self-authored geometry.
4. Commit the deliberate public file list; confirm no local profiles or other pipe code.
5. Push `main` and the version tag; check both CI runs.
6. Publish the ZIP, SHA256 file, and latest-release screenshots; verify public downloads.
7. Update local publishing receipts and catalog. Retire images from older release
   pages while preserving source tags and installer downloads.

---

## 简体中文

打包需要 Python 3.11+；集成检查使用 Blender 自带 Python。运行需要 Blender 5.2+，
无需 pip 依赖。上方命令运行便携检查、可选 Blender 清单验证、完整集成及原生交互。
Windows 中以引号包裹 `blender.exe` 的完整路径。

构建输出 `dist/pipeworks-0.5.1.zip` 和 `SHA256SUMS.txt`。ZIP 的时间戳、权限、
文件顺序和压缩固定，相同 Python/zlib 工具链下重复构建逐字节相同；不同工具链
版本的压缩字节可能不同。0.2.0 发布包使用 Blender 自带 Python 3.13.13。
CI 检查语法、产品元数据、独立范围、
源码/包一致性和可复现性，不运行 Blender 图形界面。

集成运行器使用 Git 忽略的隔离配置，先创建 CONFIG/SCRIPTS/EXTENSIONS，安装
检查确认实际配置路径后才保存偏好；真实安装 ZIP 后另启进程检查语言及独立 RGBA
颜色记忆，然后恢复英文和白/黄默认色。
不会修改用户常用 Blender 配置。

新增 GUI 运行器使用预先创建的隔离配置，先后启动四个临时窗口，每个进程限制
180 秒。交互套件安装真实发布 ZIP，覆盖 Ctrl+P 选择器及原生 Parent 恢复、六轴、
多次原生旋转/平移/缩放及 Alt+中键后的续画、弯头辅助、跟随切换、稳定输入比例、边缘回卷、
紧凑单弯/连续弯、取消与原有绘制回归。绘制调用和截图验证白/黄默认箭头、
屏幕/世界辅助共用自选 RGBA、恢复默认及手动模式起点/管端锚定，
三次启用/禁用检查快捷键清理。独立的真实安装 ZIP 导航套件测量旋转、平移和拖动缩放时精确 50% 的伸缩反馈、松开恢复原速、首段轴向保持，以及拖动中禁用插件的清理。鼠标回位覆盖视口外收回、隐藏辅助提示、连续按键、当前管头定位及回位后无管长跳变的续画。原生事件模拟屏蔽操作系统
鼠标事件，因此测试显式将回卷目标坐标重新送入 Blender 事件队列。真实硬件输入
检查使用 `tests/manual_interaction.py`，不加 `--enable-event-simulate`；运行前在
`verification/manual-interaction/` 创建并指定三类配置目录。该脚本安装真实 ZIP，
使用临时场景，输出仅本地使用的状态记录。

后台运行器包含 `tests/check_compact_bends.py`，覆盖管半径边界附近的单弯、S/U 弯、
空间弯、正反向及旋转路线；端盖位置、法线与直径、正体积、定向闭合流形、零面积面、
非相邻三角面相交、半径适配、参数回退及保存重建。生成几何与凭据仅保存在忽略的
`verification/line-pipe/`。

`tests/check_connections.py` 覆盖整组吸附、四种端口配对、滚转、平滑/折角及空间桥接、
副本网格修复、旧管口、Mesh 缺失记录、旋转组曲率、失败原子性与保存重开。另启安装 ZIP
的新进程，读取源码生成的场景，检查连接对象指针、端口占用、原生 Mesh 参数和桥接更新。
GUI 连接套件覆盖管口点选、滚转预览/取消/确认、三种操作的原生撤销/重做、右键、语言和清理。
真实 Windows 输入使用 `tests/gui_connections.py -- --manual`，不加事件模拟。

`tests/check_profiles.py` 在隔离配置的临时库中验证实际边数、按顺序匹配、边环相位、壁厚、
十个自定义管口以及单件导出导入。
同时验证版本选择、缺规格回退；原生连接检查覆盖自定义 P1/P2 管口、连续库件接续，
以及中英文提示词复制和原剪贴板恢复。库均位于临时隔离配置。

原生事件队列测试使用 `--enable-event-simulate --python tests/gui_line_pipe.py
-- --six-axis`，运行前创建并通过环境变量指定 `verification/line-pipe/six-axis-ui/`
下三类配置目录。测试使用自建临时场景，正交诊断图不用于公开展示；公开宽幅透视
图使用 `tools/capture_preview.py`。

隔离启动并执行 `tools/build_example.py` 可生成自建画管示例。
`tools/build_connection_example.py` 生成 `examples/pipeworks-connections-0.4.0.blend`，
包含滚转吸附、平滑/折角桥接、旋转组曲率匹配和一对可试接管道；交付前以新进程安装 ZIP 重开验证。示例、验证输出、配置、
安装包及发布凭据均不入 Git；安装包仅含 `line_pipe/` 下 16 个扩展文件。

发布前验证源码、安装包和交互，检查宽幅非等距透视图，核对公开文件清单后提交。
推送 main 和版本标签，确认两次 CI 成功，再发布安装包、SHA256 与最新版本截图，
核对匿名下载并更新本地记录。新版本上线后撤下旧发布页图片，保留历史源码与安装包。
