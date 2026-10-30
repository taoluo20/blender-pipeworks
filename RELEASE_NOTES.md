# PipeWorks 0.1.1

Draw solid procedural pipes in Blender with mouse-driven six-axis starts and
hold-to-turn rounded bends. This initial release contains the drawing workflow.

- Tap P for world origin, or hold P and left-click a surface.
- Move to choose +X/-X/+Y/-Y/+Z/-Z before the first bend.
- Hold B, move, release to turn; Enter finishes the pipe.
- Set diameter and bend radius in the PipeWorks sidebar; keep an editable
  centerline or convert the result to a solid mesh.
- English by default, with a one-button Simplified Chinese switch.

Requires Blender 5.2+. Tested on Windows / Blender 5.2.2 LTS. See the repository's
validation notes for the checks and practical limits. Automatic linking, pipe
assemblies, snapping, and fittings are not part of this release.

Install `pipeworks-0.1.1.zip` through Preferences > Get Extensions > Install from
Disk. The internal extension ID remains `line_pipe`; upgrade an existing local
Line Pipe installation rather than enabling two copies. Verify the download with
`SHA256SUMS.txt`. License: GPL-3.0-or-later.

---

## 简体中文

**PipeWorks 0.1.1** 可在 Blender 中用鼠标选择六轴起始方向、延长实心管道，并通过
按住/松开按键完成圆滑转弯。首个公开版本仅包含画管流程。

- 单按 P 从世界原点起画，按住 P 加左键从表面起画。
- 首弯之前移动鼠标选择 +X/-X/+Y/-Y/+Z/-Z。
- 按住 B 并移动预览，松开确认转弯，Enter 完成。
- 在 PipeWorks 侧栏设定直径和半径，保留可编辑中心线或转为实心网格。
- 默认英文，一键切换简体中文。

需要 Blender 5.2+，已在 Windows / Blender 5.2.2 LTS 验证。检查范围和实际边界
见仓库验证说明。本版不包含自动连接、组装、吸附或管件库。

通过「偏好设置 > 获取扩展 > 从磁盘安装」选择 `pipeworks-0.1.1.zip`。内部扩展
ID 保留 `line_pipe`，已有本地 Line Pipe 安装请直接升级，避免同时启用两份。
`SHA256SUMS.txt` 用于校验下载。许可为 GPL-3.0-or-later。
