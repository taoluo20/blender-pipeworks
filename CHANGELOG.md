# Changelog

## 0.5.1 - 2026-11-05

- Pass Alt+left/middle/right mouse navigation through to Blender during drawing,
  start selection, bends and port picking. Alt+right mouse no longer cancels the tool.
- Keep 50% length feedback for native Alt navigation and rebase on the initiating
  button's release, including when Alt is released first.

## 0.5.0 - 2026-11-04

- Edit the route length and profile of inserted procedural library fittings.
- Press E while drawing to attach a fitting and extend from its outlet. Library
  families select the exact authored edge-count variant and report missing sizes.
- Keep authored library rings intact in direct and distance connections. Continue
  through two-port plain meshes when uniform scaling matches both profiles.
- Group edge-count variants under one library fitting and copy a complete
  English or Simplified Chinese AI fitting prompt with an editable description.
- Save attached pieces and their joints as a group with one-step Undo and Redo.

## 0.4.1 - 2026-11-03

- Drag the preset edge count left or right and release to apply. The adjacent
  dropdown still selects any preset directly.

## 0.4.0 - 2026-11-03

- Select the reference first. The second pipe or group matches it for docking,
  bridge profiles and curvature.
- Default to 60 edges with ten presets and optional free counts. Check actual
  ring counts and phase. Only retessellate the second pipe if it can be rebuilt safely.
- Generate solid or hollow cylinder and elbow templates, with free or preset walls.
- Mark selected or detected mesh mouths, show them in the viewport, and enable
  each port independently.
- Save fittings to a local library and import or export single fitting .blend files.
  Preserve authored edge rings and show the actual counts each asset provides.

## 0.3.0 - 2026-11-03

- Integrate port connections into Draw / Connect / Groups tabs, retaining the
  stable `line_pipe` ID and the complete English/Chinese switch.
- Pick anchor/moving ports in the viewport; dock the entire moving group with
  opposite port normals, live roll preview, cancellation and native Undo/Redo.
- Generate fixed-end smooth or angular bridge meshes, automatic bends, saved
  endpoint links and explicit updates after endpoints move.
- Match all selected orthogonal groups to the last active group's actual bend
  radius from the sidebar or Object Mode context menu, with atomic fit validation.
- Read compatible legacy ports without importing Pipe Assembly. Recover exposed
  Mesh ends and verified straight/single-90-degree curvature recipes when records
  are absent. Keep parameter editing on native drawings converted to Mesh.
- Validate manifold topology, tiny faces and connector self-intersection; provide
  conservative copied-mesh repair while preserving shared originals and materials.
- Retain B pointer return, Alt+MMB and 50% navigation length feedback.

## 0.2.2 - 2026-11-03

- Orbit, pan and drag zoom provide pipe extension/retraction feedback at 50% of
  normal drawing sensitivity, preserving the selected heading during navigation.
- Releasing navigation restores normal drawing speed with a fresh mouse baseline.
- Native viewport movement and Follow Tip remain independent of length feedback;
  navigation observers and pending callbacks are removed when drawing ends.

## 0.2.1 - 2026-11-03

- Alt+MMB drag reaches Blender's native axis-view gestures during drawing.
- Starting a bend moves the pointer to the current tip's visible guide center,
  recovering a pointer outside the viewport even with Follow Tip or guides off.
- The automatic cursor move preserves length and leaves the bend unselected;
  holding the key does not repeatedly recenter. Release and continue drawing normally.

## 0.2.0 - 2026-10-30

- Ctrl+P opens a left/right world-origin or surface-pick selector in Object Mode;
  disabling the add-on restores native parenting. P and Shift+P are not registered.
- Normal direction arrows default to white; selected arrows default to warm yellow.
  Native RGBA swatches customize each independently, persist globally and reset together.
- Six-axis guides stay at the start and bend guides at the tip after navigation;
  edge-clamped guides retain a visual link to their actual anchor.
- Radius Limit fits smaller tangent circular fillets on short segments, retaining
  a positive inner radius. Exact sweep tangents prevent short-tail intersections.
- Native navigation no longer leaves the draw operator waiting for a consumed MMB release.
- Optional Follow Tip (Ctrl+F) preserves rotation and zoom, with continuous edge wrapping.
- Show Guides switches signed axis/bend labels, current straight length and bend angle.
- Added isolated native-event regressions for navigation, following and startup gestures.

## 0.1.1 - 2026-10-30

First public PipeWorks release, limited to interactive solid pipe drawing.

- P starts at world zero; P with a left-click starts on a mesh surface.
- The first segment follows mouse selection across all six signed world axes.
- Hold/release B previews and confirms smooth 90-degree turns.
- Enter finishes; Backspace retracts a bend; Escape cancels the unfinished pipe.
- Editable centerline, solid caps, diameter/radius/resolution controls, mesh conversion.
- English by default with a one-button Chinese switch.
- Standalone source history, repeatable packaging, and validation tooling.

The internal `line_pipe` ID remains compatible with the local drawing prototype.

---

## 简体中文

### 0.5.1 - 2026-11-05

- 绘制、起点选择、转弯和管口拾取时，Alt+左/中/右键均交给 Blender 原生导航；
  Alt+右键不再误触发取消。
- 原生 Alt 导航保留 50% 管长反馈，按对应鼠标键的释放重建续画基准，也支持先松开 Alt。

### 0.5.0 - 2026-11-04

- 插入程序化库件后可调整管段长度和截面参数。
- 绘制时按 E 接入管件，再从出口继续画；库按实际边数选择版本，缺规格时提示。
- 直接连接与补管均保留库件管口边环；普通双口网格在等比缩放后截面匹配时也能接续。
- 库件可按边数归为同组；一键复制带可编辑描述区的完整中英文 AI 管件提示词。
- 各段和接头一同保存为管道组，支持整次撤销和重做。

### 0.4.1 - 2026-11-03

- 预设边数可按住数字左右拖动换档，松手应用。旁边的下拉箭头可直接选档。

### 0.4.0 - 2026-11-03

- 先选基准，再选要对齐的口或组，适用于直接连接、补管截面与曲率同步。
- 默认 60 边，支持十种预设和自由输入。检查实际口环的边数和相位，仅在第二件可安全重建时自动改边。
- 生成实心或中空的圆柱、弯头，空管支持自由和预设壁厚。
- 手动标记或批量识别网格管口，在视口高亮，可逐口禁用。
- 本地管件库支持单件 .blend 导入和导出，保留自定义边环并显示实际支持的边数。

### 0.3.0 - 2026-11-03

- 将管口连接整合到画管 / 连接 / 管道组页签，保留 `line_pipe` ID 与完整中英切换。
- 视口点选固定口和移动口，整组吸附并使口法线相对，支持滚转实时预览、取消及原生撤销/重做。
- 固定原管生成平滑或折角桥接网格，自动生成拐点、保存端口连接记录，移动端点后可显式更新。
- 面板和对象模式右键菜单可将所选正交组统一为最后活动组的实际弯曲半径，放不下时整次拒绝。
- 无需导入旧 Pipe Assembly 即可读取兼容管口；无记录 Mesh 可恢复外露端口，验证后的直管与
  单个圆形 90 度弯头可恢复曲率配方。原生画管转换为 Mesh 后仍可参数修改。
- 检查流形、极小面与连接段自交；提供副本网格基础修复，保留共享原几何与材质。
- 保留 B 鼠标回位、Alt+中键与导航期间 50% 管长反馈。

### 0.2.2 - 2026-11-03

- 拖动旋转、平移或缩放视角时，管道伸长/缩短反馈为正常绘制灵敏度的 50%，
  导航期间保持已选择的管道方向。
- 结束导航后重建鼠标基准，恢复正常绘制速度。
- 管长反馈不改变原生视角操作；兼容跟随管头，结束绘制时清理导航监听与待执行回调。

### 0.2.1 - 2026-11-03

- 修复绘制过程中 Alt+中键拖动无法触发 Blender 原生轴向视角切换的问题。
- 开始转弯时，鼠标回到当前管头的可见转弯提示中心；鼠标已在视口外、关闭跟随管头
  或隐藏辅助提示时，仍可按转弯键将鼠标收回。
- 自动回位不改变管长、不选择弯头；持续按住按键不会反复回位，松开后正常续画。

### 0.2.0 - 2026-10-30

- Object Mode 中 Ctrl+P 打开世界原点/表面点选的左右选择器；禁用插件恢复原生 Parent，
  不注册 P 或 Shift+P。
- 普通方向箭头默认白色，选中箭头默认暖黄；原生 RGBA 色块可分别调整，
  全局保存并支持一键恢复二者默认值。
- 六轴提示固定于起点、转弯提示固定于管端，导航后仍跟随真实投影；
  边缘夹取时保留到真实锚点的连线。
- 半径上限内适配更小的相切圆弧，内侧半径保持大于零；精确扫掠切向消除极短直线连接处穿插。
- 原生导航消耗中键释放事件后，绘制操作不再锁死。
- 可选跟随管头（Ctrl+F）保留旋转与缩放，支持连续边缘续移。
- 显示辅助提示统一控制带正负号的轴向/弯头标签、当前直线段长度及角度。
- 新增导航、跟随与启动手势的隔离原生事件回归。

### 0.1.1 - 2026-10-30

PipeWorks 首次公开发布，本版仅包含交互式实心画管。

- P 从世界原点起画，P 加左键识别网格表面起点。
- 鼠标在正负六轴之间自动切换首段方向。
- 按住 B 预览平滑 90 度弯头，松开确认。
- Enter 完成，退格撤回弯头，Esc 取消未完成管道。
- 可编辑中心线、实心端盖、直径/半径/精度参数及网格转换。
- 默认英文，单按钮切换中文。
- 独立源码历史、可复现打包与验证工具。

内部 `line_pipe` ID 保持兼容本地画管原型。
