# PipeWorks 0.6.0

Organize pipes in a staged group list and edit the exact selection through one
live parameter editor, including automatic distance bridges.

- Drag list grips to regroup or reorder. Rename pipes and groups with presets or
  custom templates such as `{group}_{index:03d}`. Draft names and grouping stay
  inside the addon until **Apply to Blender**.
- Apply as one actual Mesh per group by default, or choose Collections to retain
  separate procedural pipes. Materials and external pipe-port links are preserved.
- Select a group to edit every member, or select any number of individual pipes.
  Dragging a value immediately sets every selected pipe to the same displayed
  absolute number and keeps updating while the mouse is held. One Undo restores
  the individual starting values.
- Box select across list names with Set, Add and Remove modes, or use Blender's
  viewport box selection. Both selections stay synchronized.
- Repeated connection commands now use the currently chosen Anchor, Moving Pipe
  and Start/End ports. Automatic bridges share the selected-pipe controls.

Install `pipeworks-0.6.0.zip` through Blender's **Install from Disk**, updating the
existing `line_pipe` extension. Requires Blender 5.2+.

Merged Mesh groups are baked geometry; use Collections to retain per-pipe
procedural editing. Connected profile edits require the affected pipes and
bridges selected together. Mesh merging joins objects without a boolean union.

Validation on Blender 5.2.2 includes 61 group and 42 selection-edit backend checks,
15 group UI, 24 live-selection UI and 79 endpoint-selection UI checks, plus
drawing, navigation, connection, actual-ZIP installation and restart regressions.
The installer is checked against committed source, reproducible builds and the
Blender extension manifest. Physical Windows input checks list rectangle release
and subsequent selection; simulator-specific behavior is recorded in the
validation documentation.

---

## 简体中文

新增暂存组列表，所选管道与自动距离连接段共用一套实时参数编辑器。

- 拖动列表拖柄即可归组或排序。管道和组可直接改名，并提供命名预设及
  `{group}_{index:03d}` 等自定义模板。名称与分组先保留在插件内，点击
  **应用到 Blender** 后再同步。
- 默认每组真正合成一个 Mesh；也可选择 Collection 保留独立的程序化管道。
  保留材质和外部管口连接。
- 选组修改组内全部成员，多选修改选中的任意数量管道。拖动数值的当下，
  所有选中管道立即统一为控件显示的绝对数值，按住鼠标期间持续同步。
  一次撤销恢复各自原值。
- 在列表名称上拖动框选，支持替换、加选、减选；也支持 Blender 视口框选，
  两处选择同步。
- 连续连接时正确使用当前 Anchor、移动管道和首末口，不再被旧的 Start-Start
  缓存覆盖。自动连接段也能通过所选管道控件修改。

在 Blender **从磁盘安装**中选择 `pipeworks-0.6.0.zip`，更新既有 `line_pipe`
扩展。需要 Blender 5.2+。

合成后的 Mesh 为烘焙几何；需要逐根程序化编辑时请选择 Collection。
修改相连截面时须一起选中相关管道和补管。Mesh 合成仅合并对象，不进行布尔并集。

Blender 5.2.2 验证包含 61 项分组后端、42 项批量编辑后端、15 项分组界面、
24 项实时选择界面及 79 项端口选择界面检查，以及绘制、导航、连接、真实 ZIP
安装和重启回归。安装包核对提交源码、可复现构建及 Blender 扩展清单。
Windows 实际鼠标另行验证列表框选松手及后续选择；模拟器的特定行为记录在验证文档中。
