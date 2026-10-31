# PipeWorks 0.2.0

Draw solid procedural pipes in Blender with mouse-driven six-axis starts and
hold-to-turn rounded bends. This release updates drawing interaction and arrow colors.

- Press Ctrl+P, move left for world origin, or move right and click a surface.
  It takes priority over Parent in Object Mode; disabling restores native parenting.
- White normal arrows and warm yellow selected arrows retain signed axis labels.
  Native color swatches support independent RGBA/Hex editing, global preferences
  and one-click default restoration; guides stay anchored to the start or tip.
- Radius Limit is a maximum: short segments fit smaller circular fillets with a
  positive inner radius, shown in the overlay. Short-tail sweep tangents are exact.
- Orbit, pan and zoom during drawing, then continue with a freshly rebased input.
- Toggle Follow Tip with Ctrl+F for view translation and continuous edge wrapping.
- Toggle Show Guides for axis/bend labels, current straight length and bend angle.
- Move to choose +X/-X/+Y/-Y/+Z/-Z before the first bend.
- Hold B, move, release to turn; Enter finishes the pipe.
- Set diameter and radius limit in the PipeWorks sidebar; keep an editable
  centerline or convert the result to a solid mesh.
- English by default, with a one-button Simplified Chinese switch.

Requires Blender 5.2+. Tested on Windows / Blender 5.2.2 LTS. See the repository's
validation notes for the checks and practical limits. Automatic linking, pipe
assemblies, snapping, and fittings are not part of this release.

Install `pipeworks-0.2.0.zip` through Preferences > Get Extensions > Install from
Disk. The internal extension ID remains `line_pipe`; upgrade an existing local
Line Pipe installation rather than enabling two copies. Verify the download with
`SHA256SUMS.txt`. License: GPL-3.0-or-later.

Validation passed: 179 integration assertions, 326 compact-bend assertions,
102 installed-extension interaction assertions and 41 drawing regressions.
Actual ZIP installation, preference restart, native color-picker input, extension
validation and reproducible packaging also passed. Blender tests run locally;
GitHub CI checks portable source and package integrity.

---

## 简体中文

**PipeWorks 0.2.0** 可在 Blender 中用鼠标选择六轴起始方向、延长实心管道，
并通过按住/松开按键完成圆滑转弯。本版更新画管交互及箭头颜色设置。

- 按 Ctrl+P 后左摆从世界原点起画，右摆后点击表面起画；Object Mode 中优先于
  Parent，禁用插件后恢复原生行为。
- 普通箭头默认白色，选中默认暖黄，保留带正负号的轴标签。原生颜色控件支持
  分别调整 RGBA/Hex、全局保存和一键恢复默认，提示固定于起点或管端。
- 弯曲半径上限内适配更小圆弧，内侧半径保持大于零，并显示实际局部半径；
  精确扫掠切向消除极短直线连接处穿插。
- 绘制中旋转、平移、缩放后，重建输入基准并继续画管。
- Ctrl+F 切换跟随管头，视图平移并支持边缘连续续移。
- 显示辅助提示开关控制轴向/弯头标签、当前直线段长度与角度。
- 首弯之前移动鼠标选择 +X/-X/+Y/-Y/+Z/-Z。
- 按住 B 并移动预览，松开确认转弯，Enter 完成。
- 在 PipeWorks 侧栏设定直径和半径上限，保留可编辑中心线或转为实心网格。
- 默认英文，一键切换简体中文。

需要 Blender 5.2+，已在 Windows / Blender 5.2.2 LTS 验证。检查范围和实际边界
见仓库验证说明。本版不包含自动连接、组装、吸附或管件库。

通过「偏好设置 > 获取扩展 > 从磁盘安装」选择 `pipeworks-0.2.0.zip`。内部扩展
ID 保留 `line_pipe`，已有本地 Line Pipe 安装请直接升级，避免同时启用两份。
`SHA256SUMS.txt` 用于校验下载。许可为 GPL-3.0-or-later。

验证通过：179 项集成、326 项紧凑弯头、102 项真实安装交互及 41 项绘制回归。
真实 ZIP 安装、偏好重启、原生拾色器输入、扩展校验与可复现打包均通过。
Blender 检查在本地运行，GitHub CI 检查便携源码和安装包完整性。
