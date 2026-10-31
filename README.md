# PipeWorks

Draw solid procedural pipes directly in Blender's viewport. Choose a starting
point, extend with the mouse, hold a key to turn, and press Enter to finish.

**English** · [简体中文](#简体中文)

**0.2.0** adds a Ctrl+P start selector, compact round bends, reliable continuation after
viewport navigation, optional tip following with edge wrapping, and switchable
direction/length/angle guides with customizable white/yellow arrow colors.
The drawing tool includes mouse-driven six-axis
initial direction, smooth 90-degree bends, a configurable diameter, and closed
solid ends. Automatic connections and component assembly are outside this release.

[Download the latest release](https://github.com/taoluo20/blender-pipeworks/releases/latest)
· [Controls and behavior](docs/FEATURES_AND_LOGIC.md)
· [Build and test](docs/DEVELOPMENT.md)
· [Validation](docs/VALIDATION.md)

## Install

1. Download `pipeworks-0.2.0.zip` from the latest release.
2. In Blender, open **Edit > Preferences > Get Extensions > menu > Install from Disk**.
3. Select the ZIP, enable **PipeWorks**, and open **N > PipeWorks** in the 3D Viewport.

The interface defaults to English. Click **中文** to switch the panel, options,
hover descriptions, and modal feedback to Simplified Chinese. Click **English**
to switch back. The extension saves the language preference when automatic
preference saving is enabled; otherwise save Blender preferences manually.

The internal extension ID remains `line_pipe` for existing scenes. Update an
existing Line Pipe installation rather than enabling two copies.

## Draw A Pipe

| Input | Result |
| --- | --- |
| **Ctrl+P**, then move left | Confirm world `(0, 0, 0)` as the start |
| **Ctrl+P**, then move right and click a mesh | Start at the picked surface point |
| Move the mouse before the first bend | Choose **+X / -X / +Y / -Y / +Z / -Z** and extend |
| Hold **B**, move toward a guide arrow, release **B** | Preview and commit one rounded 90-degree bend |
| Continue moving | Extend the new straight segment |
| **Enter** | Complete the whole pipe |
| **Backspace** or **Ctrl+Z** while drawing | Retract the latest bend |
| **Esc** or right-click | Cancel the whole unfinished pipe |
| **Ctrl+F** while drawing | Toggle **Follow Tip**, including continuous edge wrapping |
| **Show Guides** | Toggle directions, length, bend angle and actual local radius |

Set **Diameter** and **Radius Limit** in the panel first. Drawing does not require
holding the mouse button. All six initial directions stay available until the
first bend; **Ctrl+P** always uses automatic six-axis selection, even in older scenes
with a fixed heading. The first segment is not an arbitrary-angle freehand stroke.

The turn key can be changed to B, T, F, C, or V. Orbit, pan, and zoom are available
during drawing. The first movement after navigation rebases the input without
changing pipe length. Enable **Follow Tip** to keep the tip in view; the pointer
wraps inside the viewport at its edges while accumulated length stays continuous.
The start selector confirms on a horizontal gesture, with no mouse button or
held shortcut required. That gesture does not contribute to pipe length.
Ctrl+P takes priority over Blender's Parent popup in Object Mode while PipeWorks
is enabled. Disabling PipeWorks removes its binding and restores native parenting.
Plain P and Shift+P are not registered. Normal arrows default to white and the
selected direction to warm yellow, with signed axis labels retained. Six-axis
guides stay at the starting point; bend guides stay at the pipe tip, including
after manual navigation. Edge-clamped guides keep a line to their actual anchor.

Use the native **Normal** and **Selected** swatches under **Arrow Colors** to edit
the two colors independently, including the color wheel, Hex value and Alpha.
The same colors update all screen and world arrows immediately. The reset icon
beside **Arrow Colors** restores opaque white and warm yellow. Colors are global
tool preferences, shared by scenes and saved across Blender restarts. With
automatic preference saving enabled they save shortly after editing; otherwise
use **Preferences > Save Preferences**. This changes no scene colors or Blender theme.

**Radius Limit** is a maximum centerline radius. Short segments use smaller
tangent circular fillets without changing diameter or route corners. Each local
radius must remain greater than half the diameter; a shared segment must fit the
sum of its two actual fillet radii. A tiny floating-point guard prevents collapsed
inner faces. The overlay shows the actual local radius. Impossible bends are
refused with localized feedback.
After completion, use the selected pipe's diameter, radius, and
resolution controls to rebuild it, or **Convert to Mesh** to bake the solid mesh.

The panel also supports a placed point, clicked surface, explicit coordinates,
3D Cursor, or a zero-based face index on the active mesh. Explicit surface-normal
and custom-vector headings are available through the panel; the Ctrl+P shortcut uses
the six world axes.

## What Is Included

- One editable centerline with a native Geometry Nodes solid sweep.
- Circular cross sections, flat closed caps, and tangent quarter-circle bends.
- A live four-direction bend preview with confirmation on key release.
- Compact circular fillets bounded by Radius Limit, with a positive inner radius.
- One-step undo/redo for completed drawings, plus cancellation cleanup.
- English and Simplified Chinese with a single language button.
- Persistent, independent normal/selected arrow colors with native RGBA controls.
- A self-authored example generator, repeatable packaging, and portable CI checks.

## Compatibility And Limits

Requires **Blender 5.2+**; tested on **Windows / Blender 5.2.2 LTS**. This version
uses the Blender 5.2 Geometry Nodes modifier interface. Older versions are not
supported. No external Python packages or network service are required at runtime.

This is a solid modeling tool. It has no hollow bore, wall thickness, R-drag
resizing, port snapping, automatic linking, fittings library, assembly graph,
collision avoidance, or arbitrary-angle bends. Self-crossing routes can intersect
geometrically. A finished drawing cannot be resumed interactively in this version.

Direct edits to generated curve samples are replaced when the stored recipe is
rebuilt from the panel. Object scaling also scales the visible pipe diameter.
Keep the modifier enabled to see the solid surface.

Public release images use a wide, non-isometric perspective viewport. Screenshots
and installer downloads are attached to the latest release. See the
[changelog](CHANGELOG.md) and [GPL-3.0-or-later license](LICENSE).

---

## 简体中文

**PipeWorks** 是 Blender 视口内的程序化实心画管工具：确定起点，移动鼠标延长，
按住按键转弯，按 Enter 完成。

**0.2.0** 新增 Ctrl+P 起点选择器、紧凑圆弯、导航后可靠续画、可选管头跟随与边缘续移，
以及可关闭的方向、长度与角度辅助。默认白/黄箭头支持自选颜色。工具包含鼠标六轴初始定向、平滑的 90 度弯头、可调直径
和实心封口。本版范围仅为画管，自动连接与组件组装不在其中。

[下载最新版](https://github.com/taoluo20/blender-pipeworks/releases/latest)
· [功能与逻辑](docs/FEATURES_AND_LOGIC.md#简体中文)
· [构建与测试](docs/DEVELOPMENT.md#简体中文)
· [验证记录](docs/VALIDATION.md#简体中文)

### 安装

1. 从最新版发布页下载 `pipeworks-0.2.0.zip`。
2. 打开 Blender 的 **编辑 > 偏好设置 > 获取扩展 > 菜单 > 从磁盘安装**。
3. 选择 ZIP，启用 **PipeWorks**，在三维视图打开 **N > PipeWorks**。

界面默认英文。点击 **中文** 切换完整中文面板、下拉选项、悬停提示及操作反馈；
点击 **English** 切回英文。启用自动保存偏好时会记忆语言；否则手动保存 Blender
偏好设置。内部扩展 ID 保留 `line_pipe`，兼容已有场景；已有 Line Pipe 安装应直接
升级，避免同时启用两份。

### 绘制

| 输入 | 结果 |
| --- | --- |
| 按 **Ctrl+P** 后向左摆 | 确认世界坐标 `(0, 0, 0)` 为起点 |
| 按 **Ctrl+P** 后向右摆，再点击网格 | 从识别到的表面位置起画 |
| 首个弯头前移动鼠标 | 自动切换 **+X / -X / +Y / -Y / +Z / -Z** 并延长 |
| 按住 **B**，向指示箭头移动，再松开 **B** | 预览并确认一个圆滑的 90 度弯头 |
| 继续移动 | 延长新方向的直线段 |
| **Enter** | 完成整条管道 |
| 绘制中按 **Backspace** 或 **Ctrl+Z** | 撤回最新弯头 |
| **Esc** 或右键 | 取消整条未完成管道 |
| 绘制中按 **Ctrl+F** | 切换**跟随管头**，包含边缘连续续移 |
| **显示辅助提示** | 开关方向、长度、转弯角度与实际局部半径 |

先在面板设定**直径**与**弯曲半径上限**。无需持续按住鼠标键。首个弯头之前可在六个
轴向间切换；即使旧场景保存了固定朝向，**Ctrl+P** 仍始终使用鼠标六轴定向。
首段选择的是六个轴向，并非任意角度自由画线。

转弯键可选 B、T、F、C 或 V。绘制中可以旋转、平移、缩放视图，导航后的首次移动
重建输入基准且不改变管长。启用**跟随管头**后视图随管头平移，鼠标在视口边缘回卷，
累计长度连续。起点选择器通过水平摆动确认，不需持续按键或鼠标键，摆动位移不计入管长。
插件启用时，Object Mode 中 Ctrl+P 优先启动 PipeWorks；禁用插件即移除该绑定，
恢复 Blender 原生 Parent。单独 P 和 Shift+P 不再注册。普通箭头默认白色，选中
方向默认暖黄色，并保留带正负号的轴标签。六轴提示固定于起点，转弯提示固定于
管端，手动导航后仍保持锚定；边缘夹取时保留到真实锚点的连接线。

在**箭头颜色**下点击**普通箭头**或**选中箭头**的 Blender 原生色块，分别调整
色盘、Hex 与 Alpha。所有屏幕/世界方向箭头即时共用这组颜色；标题旁的恢复图标
将两色恢复为不透明白色与暖黄色。颜色保存在全局工具偏好，跨场景及重启保留。
启用自动保存偏好时，编辑后稍候即可保存；关闭时使用**偏好设置 > 保存偏好设置**。
不会改变场景颜色或 Blender 主题。

**弯曲半径上限**表示中心线半径的最大值。短段使用更小的相切圆弧，直径与路线拐点
不变。局部半径必须大于直径的一半；共用段需容纳相邻两个实际圆角半径之和。
仅保留防止内侧面塌缩的极小浮点余量，辅助显示实际局部半径；确实放不下时给出
本地化提示并拒绝该弯头。
完成后通过
所选管道的直径、半径、分段控件重建，或用**转换为网格**烘焙实心网格。

面板还支持放置点、点击表面、输入坐标、三维游标或活动网格的面编号，编号从零
开始。面法线、自定义向量可通过面板指定；Ctrl+P 快捷方式始终选择世界六轴。

### 包含内容

- 可编辑中心线与 Blender 原生 Geometry Nodes 实心扫掠。
- 圆形截面、平整封闭的端盖和相切的四分之一圆弯头。
- 按住预览、松开确认的四向转弯。
- 半径上限内自动适配紧凑圆弧，内侧半径保持大于零。
- 完成后的整条撤销和重做，以及取消时的预览清理。
- 默认英文、单按钮切换简体中文。
- 普通/选中箭头颜色独立保存，使用原生 RGBA 控件。
- 自建示例生成器、可复现安装包和便携 CI 检查。

### 兼容与边界

需要 **Blender 5.2+**，已在 **Windows / Blender 5.2.2 LTS** 测试，使用其 Geometry
Nodes 修改器接口，不支持更早版本。运行时无需额外 Python 依赖或联网服务。

本版为实心建模工具，没有内孔、壁厚、R 拖动缩放、管口吸附、自动连接、管件库、
组装连接图、碰撞绕障或任意角度弯头。自交路线可能产生几何穿插，已完成路线不能
重新进入交互续画。

直接修改生成曲线采样点后，再用面板按保存配方重建会覆盖这些手工修改。对象缩放
也会改变显示直径；需保留修改器启用才能显示实体。

公开说明图使用宽幅非等距透视视口；截图和安装包作为最新版发布附件提供。
参见[版本记录](CHANGELOG.md#简体中文)与 [GPL-3.0-or-later 许可证](LICENSE)。
