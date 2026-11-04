# PipeWorks 0.5.0

Draw pipes, connect their mouths, and continue through library fittings in Blender
5.2+. This release includes local 0.2.1–0.5.0 work since public release 0.2.0.

- **Drawing:** Alt+MMB works while drawing; B returns the pointer to the current
  bend start. Orbit, pan and drag zoom give 50% length feedback.
- **Connections:** pick the reference first, then the moving mouth. Dock the whole
  group with roll preview, or keep both ends fixed and generate a smooth/angular
  bridge. Match curvature between independently rotated orthogonal groups.
- **Profiles:** default 60 edges, ten draggable presets, custom counts, hollow
  walls, manual/automatic port marking, and copied-mesh repair.
- **Library variants:** share single fitting .blend files. Use **Add Selected as
  Variant** to group separately authored edge counts. Library mouths require
  matching actual counts and retain their authored rings.
- **E continuation:** select **E Fitting**, extend a pipe and press E. Built-in
  cylinder/elbow templates generate the current profile. Library families choose
  the exact count; missing sizes report available counts and preserve the drawing.
  Procedural variants adapt diameter and bore. Plain two-port meshes scale
  uniformly when both mouth profiles match.
- **Editing:** procedural library fittings keep editable lengths and profiles.
  Backspace retracts the latest bend/fitting. Enter saves the connected pieces
  as a group with one-step Undo/Redo. Escape cancels the drawing.
- **AI fitting prompt:** **Library > Copy AI Fitting Prompt** copies a complete
  specification. Replace its design-description block before giving it to an AI.
  It defines variants, circular mouth topology, hollow rims, editable generation
  parameters and port-marking steps. The button copies text locally.
- English is the default; the Chinese button switches the complete interface.

Install the attached `pipeworks-0.5.0.zip` through Blender's **Install from Disk**.
Update the existing `line_pipe` extension rather than enabling a second copy.
`SHA256SUMS.txt` verifies the installer. See the repository validation document
for Blender integration and installed-ZIP native viewport results.

Connections retain separate editable objects and link records; they do not weld
meshes or perform full-scene obstacle avoidance. The library uses local files.

---

## 简体中文

在 Blender 5.2+ 中画管、连接管口，并通过库件接续绘制。本次汇总上次公开版 0.2.0
之后的本地 0.2.1–0.5.0 更新。

- **绘制：**修复画管时的 Alt+中键；B 回到当前转弯起点。旋转、平移和拖动缩放时提供 50% 管长反馈。
- **连接：**先选基准口，再选移动口；支持整组吸附与滚转预览，或固定两端生成平滑/折角补管。
  可在分别旋转的正交管道组之间统一曲率。
- **截面：**默认 60 边、十种可拖动预设与自由边数；真实空管内壁、手动/自动标口和副本网格修复。
- **库件版本：**单件 .blend 文件导入导出；用「添加所选为边数版本」把独立制作的规格归为一组。
  库件连接要求实际边数一致，保留作者的管口边环。
- **E 接续：**选择 E 接续管件，延长管道后按 E。内置圆柱/弯头按当前截面生成；库按同边数选择版本，
  缺规格时提示可用边数并保留绘制。程序化版本适配直径与内孔；普通双口网格等比缩放后截面匹配也能接续。
- **编辑：**程序化库件可改长度和截面。Backspace 撤回最新弯头或管件；Enter 保存各件、连接和分组，
  整次绘制支持一步撤销重做；Esc 取消。
- **AI 管件提示词：**在「管件库」点「复制 AI 管件提示词」，替换中间的设计描述后交给 AI。
  模板说明边数版本、圆口拓扑、空管端面、可调生成参数与标口流程。按钮在本地复制文本。
- 默认英文，一键切换完整简体中文。

在 Blender「从磁盘安装」中选择附件 `pipeworks-0.5.0.zip`，更新既有 `line_pipe` 扩展。
可用 `SHA256SUMS.txt` 校验安装包。Blender 集成与真实安装包的原生界面检查结果见仓库验证文档。

连接保留独立可编辑物体及记录，不做网格焊接或全场景避障。管件库使用本地文件。
