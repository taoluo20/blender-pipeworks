# PipeWorks

Draw and connect procedural pipes directly in Blender's viewport. Choose a starting
point, extend with the mouse, hold a key to turn, and press Enter to finish.

**English** · [简体中文](#简体中文)

**0.5.0** adds **E** fitting continuation, edge-count variants in the library,
editable procedural fitting lengths, and a copyable AI fitting specification.

[Published releases](https://github.com/taoluo20/blender-pipeworks/releases/latest)
· [Controls and behavior](docs/FEATURES_AND_LOGIC.md)
· [Build and test](docs/DEVELOPMENT.md)
· [Validation](docs/VALIDATION.md)

## Install

1. Use the supplied `pipeworks-0.5.0.zip`, or build it from this source.
2. In Blender, open **Edit > Preferences > Get Extensions > menu > Install from Disk**.
3. Select the ZIP, enable **PipeWorks**, and open **N > PipeWorks** in the 3D Viewport.

The interface defaults to English. Click **中文** to switch the panel, options,
hover descriptions, and modal feedback to Simplified Chinese. Click **English**
to switch back. The extension saves the language preference when automatic
preference saving is enabled; otherwise save Blender preferences manually.

The internal extension ID remains `line_pipe` for existing scenes. Update an
existing Line Pipe installation rather than enabling two copies.

## Connect Pipes

Open **Connect > Pick Reference, Then Moving**. Click the reference mouth first,
then the mouth that should match it. Both can also be entered in their labeled
fields. Completing a drawing fills the moving field with that pipe's End.

- **Direct Connection** moves the entire moving group to the anchor. The two
  outward normals become opposite. Change **Roll** in the live preview and click
  **OK**; **Cancel/Esc** restores the original placement. A single straight pipe
  does not need roll. The anchor group stays fixed.
- **Distance Connection** keeps both originals fixed and generates a connecting
  Mesh, including automatic bends. Set **Maximum Distance**, **Bend Radius**,
  and **Smooth Bends** first. Disable Smooth Bends for angular
  joins. Infeasible routes are refused before adding geometry.

Both modes accept editable drawings, drawings converted to Mesh, and compatible
old Pipe Assembly ports without requiring that add-on. Outer diameters must match;
if both ends are hollow, their bores must also match. A bridge is hollow only when
both ends have matching bores; a solid/hollow pair produces a solid bridge.
Connections are modeling joins between separate editable objects, with saved link
records. They are not boolean welds or a fluid simulation.

Successful connections merge the two PipeWorks groups. For manual grouping, select
pipes and use **Groups > Group Selected**. Grouping includes each selected pipe's
existing group. Use **Select Entire Group** to select its members. Disconnect new links
before separating a connected group. **Disconnect Active Pipe** releases links involving the
active pipe and removes their generated bridges. It does not move directly docked
pipes back. Historical links owned by the old add-on are not rewritten.

After moving an endpoint, use **Update Distance Connections** to rebuild existing bridges.
To change an existing bridge's radius/smoothing, select it, set the options in
Connect, then use **Groups > Apply Settings to This Bridge**.

## Match Curvature And Recover Mesh Ports

Select the reference group first, then **Shift-select** the group to change. In **Groups** or the Object Mode right-click menu, choose
**Match Group Curvature**. Every group must contain only parallel/perpendicular
straight directions internally; the groups themselves may have any world rotation.
The reference uses its smallest actual fitted bend radius, ensuring compact bends
also become uniform. A straight-only reference uses its radius setting. Endpoints,
object transforms and materials are preserved. Unsupported shapes, nonuniform scale
or insufficient straight length reject the operation before any group is changed.

For an old Mesh with missing records, select it and use **Detect Mesh Ports** in
Connect, Groups or the right-click menu. Exposed circular caps and annular ends are
recognized. Marked meshes retain their authored geometry and actual edge counts.
**Register Mesh Cylinder** is available for a simple cylinder along its local X/Y/Z
axis. **Repair Pipe Mesh** welds very close duplicate vertices, dissolves degenerate
edges and recalculates normals on a copy. Unresolved self-intersections or collapsed
faces are refused, retaining the original geometry. New joins validate their mesh
before use.

## Edge Counts, Custom Ports And Fittings

- New pipes default to 60 edges. Presets are 6, 12, 24, 36, 48, 60, 72, 144,
  288 and 576. Hold the number and drag horizontally to step through presets,
  or click the adjacent arrow to choose directly. Release to apply. Turn on
  **Custom Edge Count** to enter another count.
- Equal edge counts can connect. With two differing presets, only the second
  pipe is retessellated, provided its recipe is safe to rebuild and its other
  ports are free. Library fittings always require matching actual counts;
  their authored rings are preserved. Other count mismatches report both counts. Direct roll snaps
  to the nearest vertex-aligned angle. Bridge ends match both edge rings.
- **Ports** generates a cylinder with the current profile. In Edit Mode, select
  complete mouth loops and choose **Mark Selected Loops**. In Object Mode,
  **Find and Mark All Ports** detects caps, annular rims and open loops.
  Registered mouths are highlighted and can be enabled individually.
- **Library** generates cylinders and elbows from the current parameters.
  **Add Selected** saves a fitting with its actual per-mouth counts. Export
  and import share individual fitting .blend files with other installations.
  Use **Add Selected as Variant** to group another edge count under the same
  fitting. Each variant must use one count across its enabled ports; duplicate
  counts are refused. **Copy AI Fitting Prompt** copies a specification with a
  replaceable design description, ring topology rules, and generation parameters.
- **Hollow Pipe** uses a true inner wall and annular rims. Wall thickness defaults
  to free input. Presets use 5%, 10% or 15% of the outer diameter. Generated
  template meshes can switch between solid and hollow in the Draw panel.
  Convert a generated Curve to Mesh before editing its hollow setting.

## Continue With A Library Fitting

In **Draw** or **Library**, choose an **E Fitting**. The menu includes the built-in
straight cylinder, 90-degree elbow, and saved fittings with two enabled ports of
the same edge count. Extend a pipe, then press **E** to attach the selected fitting.
Built-in templates generate the current profile. Library fittings select an
authored variant with the exact drawing edge count; a missing size reports the
available counts and leaves the drawing intact. Procedural variants adapt diameter
and bore while scaling centerline proportions. Plain authored meshes scale
uniformly, so both mouths must match the required diameter and bore after scaling.
Move the mouse to draw from the
outlet. Press **E** again to connect another fitting directly to that outlet.

**Backspace** retracts the latest bend or fitting. **Enter** saves the pieces as
individual editable objects with their joints and a shared group. **Esc** cancels
the unfinished drawing. Blender Undo and Redo treat the completed chain as one
drawing.

Inserted procedural fittings retain their recipe. Select one and open
**Selected Pipe** in Draw or Library to edit diameter, **Route Length**, bend
radius, edge count or wall thickness. Route Length measures the straight length
or the sum of the legs before rounding. With one end connected, changing length
anchors that end. Free a joint to change the length of a fitting attached at both
ends, and free the profile joints before changing the diameter or bore.

## Draw A Pipe

| Input | Result |
| --- | --- |
| **Ctrl+P**, then move left | Confirm world `(0, 0, 0)` as the start |
| **Ctrl+P**, then move right and click a mesh | Start at the picked surface point |
| Move the mouse before the first bend | Choose **+X / -X / +Y / -Y / +Z / -Z** and extend |
| Hold **B**, move toward a guide arrow, release **B** | Return the pointer to the bend start, then preview and commit a rounded 90-degree bend |
| **E** | Attach the selected fitting with matching rings and continue at its outlet |
| Continue moving | Extend the new straight segment |
| **Enter** | Complete the whole pipe |
| **Backspace** or **Ctrl+Z** while drawing | Retract the latest bend or fitting |
| **Esc** or right-click | Cancel the whole unfinished pipe |
| **Ctrl+F** while drawing | Toggle **Follow Tip**, including continuous edge wrapping |
| **Show Guides** | Toggle directions, length, bend angle and actual local radius |

Set **Diameter** and **Radius Limit** in the panel first. Drawing does not require
holding the mouse button. All six initial directions stay available until the
first bend; **Ctrl+P** always uses automatic six-axis selection, even in older scenes
with a fixed heading. The first segment is not an arbitrary-angle freehand stroke.

The turn key can be changed to B, T, F, C, or V. Pressing it returns the pointer
to the current tip's visible guide center, even from outside the viewport with
following or guides off. The automatic move does not add length or select a bend.
Orbit, pan, zoom, and Alt+MMB axis-view gestures are available during drawing.
Alt+left/middle/right mouse navigation follows your Blender keymap, including
custom bindings and Industry Compatible. Alt+right mouse does not cancel drawing
or port picking; unmodified right mouse still cancels.
Dragging orbit, pan or zoom keeps the current pipe direction and gives **50%**
length feedback. Release navigation to resume normal drawing speed.
The first movement after navigation rebases the input without
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
Converted drawings retain their recipe and can still be edited through these controls.

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

Drawing supports solid and hollow pipes. Bridges preserve compatible bores. Finished
drawings retain their saved centerline for parameter editing. Drawing itself uses right-angle bends; connectors may use a
smooth spatial fallback for skew endpoints. Connection validation checks the
connector itself, not collisions against all other scene objects.

Direct edits to generated curve samples are replaced when the stored recipe is
rebuilt from the panel. Object scaling also scales the visible pipe diameter.
Keep the modifier enabled to see the solid surface.

Public release images use a wide, non-isometric perspective viewport. Screenshots
and installer downloads are attached to the latest release. See the
[changelog](CHANGELOG.md) and [GPL-3.0-or-later license](LICENSE).

---

## 简体中文

**PipeWorks** 是 Blender 视口内的程序化画管与连接工具：确定起点，移动鼠标延长，
按住按键转弯，按 Enter 完成。

**0.5.0** 增加 **E** 接续管件、库件边数版本、程序化管件长度编辑，以及一键复制 AI 管件提示词。

[已发布版本](https://github.com/taoluo20/blender-pipeworks/releases/latest)
· [功能与逻辑](docs/FEATURES_AND_LOGIC.md#简体中文)
· [构建与测试](docs/DEVELOPMENT.md#简体中文)
· [验证记录](docs/VALIDATION.md#简体中文)

### 安装

1. 使用随附的 `pipeworks-0.5.0.zip`，或从本仓库源码构建。
2. 打开 Blender 的 **编辑 > 偏好设置 > 获取扩展 > 菜单 > 从磁盘安装**。
3. 选择 ZIP，启用 **PipeWorks**，在三维视图打开 **N > PipeWorks**。

界面默认英文。点击 **中文** 切换完整中文面板、下拉选项、悬停提示及操作反馈；
点击 **English** 切回英文。启用自动保存偏好时会记忆语言；否则手动保存 Blender
偏好设置。内部扩展 ID 保留 `line_pipe`，兼容已有场景；已有 Line Pipe 安装应直接
升级，避免同时启用两份。

### 连接管道

打开**连接 > 先选基准口，再选移动口**，在视口中依次点击两口。也可在带序号的栏位里分别选取。
画完后，该管道的末口会预填为移动口。

- **直接连接**：将移动管道的整组刚性移动到固定口，使两个朝外法线相对。
  在实时预览中修改**滚转角度**，点**确定**提交；**取消/Esc**恢复原位。
  单根直管不需要滚转，固定组保持原位。
- **距离连接**：两条原管保持原位，自动生成带拐点的连接网格。先设定**最大连接距离**、
  **弯曲半径**、**圆周分段**和**平滑弯头**；关闭平滑弯头生成折角。无法放下的路线
  会在添加几何前拒绝。

支持可编辑画管、已转换的 Mesh 以及兼容的旧 Pipe Assembly 管口，使用时无需启用旧插件。
外径必须一致；两端都有内孔时，内径也必须一致。仅两端都有匹配内孔时生成中空桥接；
实心与中空混接生成实心连接段。这是保留独立可编辑对象和连接记录的建模连接，
不进行布尔焊接或流体模拟。

连接成功会合并两个 PipeWorks 组。手动分组使用**分组 > 选中管道编组**，
会包含每条所选管道原组的全部成员；用**选择整个管道组**选择成员。相连组需先断开连接才能拆组。
**断开当前管道**释放与活动管道有关的新连接，并删除对应桥接段；直接吸附后的管道仍留在当前位置。
旧插件自己保存的历史连接不自动改写。

移动端点后，使用**更新距离连接**重建已有桥接段。修改现有桥接段的半径/平滑方式时，
选中桥接段，在连接页调整参数，再用**分组 > 将参数应用到当前补管**。

### 统一曲率与恢复网格管口

先选基准组中的一根管道，再 **Shift 点选要对齐的组**中的一根管道。
在**分组**面板或对象模式右键菜单点击**统一管道组曲率**。每个组内部的直线方向必须
互相平行或垂直，两个组本身可任意旋转。参考值使用参考组中最小的实际圆弯半径，
使紧凑弯也能统一；纯直管参考组使用其半径设置。保留端点、对象变换和材质。
形状不支持、非均匀缩放或直线长度不足时，整次操作会在修改前拒绝。

旧 Mesh 缺少管口记录时，选中它，在连接页、管道组页或右键菜单使用**识别网格端口**。
可识别外露的圆形端盖与环形口；已标记的网格保留自定义形状和实际边数。**注册网格圆柱端口**用于沿自身 X/Y/Z 轴的简单圆柱。
**修复管道网格**在副本上合并极近重复点、消除退化边并重算法线；仍存在自交或塌缩面时
拒绝并保留原几何。新连接在使用前也会检查网格。

### 边数、自定义管口与管件库

- 新管道默认 60 边。预设为 6、12、24、36、48、60、72、144、288、576。按住数字左右拖动换档，松手应用，也可点旁边的箭头直选。开启**自由边数**可输入其他边数。
- 两口边数相同可连接。不同且都在预设中时，仅在第二件可安全重建且其他口未占用的情况下改第二件。
  库件始终要求实际边数一致，保留作者的管口边环。其他不匹配会报出两口的边数。
  直连滚转吸附到顶点对齐角度，补管两端分别匹配实际边环。
- **管口**页可按当前规格生成圆柱。在编辑模式选择完整口环后点**标记所选边环**。
  对象模式下用**识别并标记全部管口**，可识别圆盖、环形口与开放边环。已标记的口高亮并可分别开关。
- **管件库**按当前参数生成圆柱和弯头。**添加所选管件**会保存实际的逐口规格。
  **导出分享**和**导入管件库**使用单件 .blend 文件，便于在不同 Blender 安装间分享。
  用**添加所选为边数版本**把另一规格归到同一管件下；同一版本的启用管口须同边数，重复规格会拒绝。
  **复制 AI 管件提示词**提供可替换的设计描述区、管口拓扑规则与参数要求，可直接交给 AI 生成脚本。
- **空管**有真实内壁和环形端面。壁厚默认自由输入，也有外径 5%、10% 和 15% 预设。
  生成的模板网格可在画管页切换实心和空管。生成的曲线可先转网格，再编辑空管设置。

### 用库件接续绘制

在**画管**或**管件库**选择 **E 接续管件**。可选内置直圆管、90° 弯头，以及正好两个同边数
启用管口的库件。先延长一段管，按 **E** 接到管头。内置模板按当前截面生成；库件查找
完全同边数的版本，缺规格时列出可用边数，保留正在画的管道。程序化版本适配直径和内孔，
按当前直径缩放中心线；普通自定义网格只等比缩放，缩放后两端外径与内孔都须匹配。
继续移动鼠标即可从出口画，或者再按 **E**
直接连上另一件。

**Backspace** 撤回最新的弯头或管件。**Enter** 将各段作为独立可编辑物体保存，同时记录
连接并编成一组。**Esc** 取消未完成的整条管道。Blender 撤销和重做按整次绘制处理。

插入的程序化管件会保留配方。选中后，在画管页或管件库的**所选管道**修改直径、
**管段长度**、弯曲半径、边数和壁厚。直管按实长，弯管的长度按圆角前各中心线段的总长计算。
一端已接时改长度会固定那一端。两端都接时，先断开一端才能改长度。改直径或内孔前要释放相关连接。

### 绘制

| 输入 | 结果 |
| --- | --- |
| 按 **Ctrl+P** 后向左摆 | 确认世界坐标 `(0, 0, 0)` 为起点 |
| 按 **Ctrl+P** 后向右摆，再点击网格 | 从识别到的表面位置起画 |
| 首个弯头前移动鼠标 | 自动切换 **+X / -X / +Y / -Y / +Z / -Z** 并延长 |
| 按住 **B**，向指示箭头移动，再松开 **B** | 鼠标回到转弯起点，再预览并确认圆滑的 90 度弯头 |
| **E** | 接入管口边数匹配的管件，并从出口继续 |
| 继续移动 | 延长新方向的直线段 |
| **Enter** | 完成整条管道 |
| 绘制中按 **Backspace** 或 **Ctrl+Z** | 撤回最新弯头或管件 |
| **Esc** 或右键 | 取消整条未完成管道 |
| 绘制中按 **Ctrl+F** | 切换**跟随管头**，包含边缘连续续移 |
| **显示辅助提示** | 开关方向、长度、转弯角度与实际局部半径 |

先在面板设定**直径**与**弯曲半径上限**。无需持续按住鼠标键。首个弯头之前可在六个
轴向间切换；即使旧场景保存了固定朝向，**Ctrl+P** 仍始终使用鼠标六轴定向。
首段选择的是六个轴向，并非任意角度自由画线。

转弯键可选 B、T、F、C 或 V。每次开始转弯，鼠标回到当前管头的可见提示中心；
鼠标已跑出视口、关闭跟随或隐藏提示时也能回位，自动移动不增加管长或选择弯头。
绘制中可以旋转、平移、缩放视图，以及 Alt+中键切换轴向视角。Alt+左/中/右键沿用你的
Blender 键位，支持自定义键位及 Industry Compatible；Alt+右键不取消绘制或管口拾取，
单独右键仍可取消。拖动视角时保持当前
管道方向，伸长/缩短反馈为正常速度的 **50%**，松开导航后恢复原速。导航后的首次移动
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
转换后的画管仍保存配方，可继续使用这些参数调整。

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

绘制支持实心和空管，桥接可保留兼容旧件的内孔。绘制仍使用直角弯；连接器可对异面端口使用平滑空间过渡。连接检查覆盖连接段自身，
不检查与整个场景中其他对象的碰撞。

直接修改生成曲线采样点后，再用面板按保存配方重建会覆盖这些手工修改。对象缩放
也会改变显示直径；需保留修改器启用才能显示实体。

公开说明图使用宽幅非等距透视视口；截图和安装包作为最新版发布附件提供。
参见[版本记录](CHANGELOG.md#简体中文)与 [GPL-3.0-or-later 许可证](LICENSE)。
