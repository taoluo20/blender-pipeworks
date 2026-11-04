# Features And Logic

## Drawing States

`Ctrl+P` opens a two-way start selector. Moving at least 32 pixels horizontally
confirms world zero on the left or surface picking on the right. Releasing the
shortcut does not choose a start. Surface picking raycasts visible mesh geometry
and uses the hit point plus the configured surface offset; a miss keeps picking
active. Confirmation captures a fresh mouse origin, so the selector gesture does
not create pipe length. Plain P and Shift+P are not registered by PipeWorks.
The binding is first in the add-on Object Mode keymap, ahead of native Parent;
default keymap entries are not edited. Disable removes the add-on binding, so
Ctrl+P performs native parenting again. Re-registering does not duplicate entries.

The initial segment has six signed world-axis directions. Mouse displacement
chooses the nearest labeled axis and controls length. A 6-pixel deadzone and small
boundary hysteresis reduce jitter. When axes overlap or point into the view, the
guides spread into an antipodal hexagon so all six choices stay accessible.

Holding the turn key freezes the incoming segment and previews four perpendicular
choices. On each new turn, the pointer moves to the current tip's visible guide
center, including when the pointer has left the viewport or guides are hidden.
Offscreen guides clamp inside the drawing area; an unprojectable tip uses the
viewport center. The automatic move adds no length and selects no direction.
Holding the key does not repeatedly move the pointer. A 14-pixel deadzone avoids unintended bends. Release commits exactly one
corner; release without a choice leaves the route unchanged. Radius Limit is the
maximum centerline radius. Each corner initially fits the minimum of that limit
and its adjacent lengths. If neighboring fillets exceed their shared segment,
their available inner radii are reduced proportionally. Later constraints may
leave unused straight length; fitting is deterministic, not a global optimization.

For pipe radius `a`, each local radius `r` must exceed `a`, and a shared segment
must hold `r1 + r2`. A single 90-degree circular fillet consumes `r` on each leg.
The ideal lower bounds are therefore greater than `a` for a single-bend leg and
greater than `2a` (the diameter) between two bends, independent of Radius Limit.
Only a float32 guard `diameter * 2^-16` is added to the local radius floor; there
is no 2%-diameter clearance or blanket `2 * Radius Limit` requirement. The guard
does not grow when the user raises Radius Limit. At diameter 0.2 it is about
0.00000305 units. Impossible or numerically collapsed bends are refused with
localized feedback. Preview and release use the same outgoing length and fitting.

Enter completes the recipe and restores rendering. Backspace retracts the latest
bend, returning to six-axis selection when the first bend is removed. Escape,
right-click, losing window focus, scene save/load, and undo cancel an unfinished
preview. Native one-step undo/redo operates on completed drawings.

## Navigation And Guides

Orbit, pan, zoom, Alt+MMB axis-view gestures, trackpad and NDOF events pass through
to Blender. Alt modifier and mouse-move events reach the native gesture keymap. The tool
detects changes to rotation, view location, distance and projection. The next
mouse movement captures a fresh input origin without changing route length.
While dragging orbit, pan or zoom, pipe length follows the mouse at **50%** of
normal drawing sensitivity using the pixel scale captured before navigation.
The chosen heading stays fixed, including during automatic first-axis selection.
The native view keeps its usual movement. Follow Tip does not pull the camera
while this feedback is active. On release the observer ends, input rebases, and
normal drawing speed resumes. Drawing cleanup also removes pending callbacks.
Navigating during a bend keeps the incoming length frozen and clears its stale choice;
the next movement establishes a new four-direction frame.

**Follow Tip** is off by default and can be toggled with **Ctrl+F** during drawing.
Following translates the view, preserving rotation, zoom and projection. Manual
navigation establishes a new follow offset. Input scales are captured at rebase
and stay fixed while following, avoiding feedback from the moving viewport.
Near a viewport edge the pointer wraps inward; the input origin shifts by the
same displacement, so the warp event adds no pipe length. Fast moves that cross
an edge are wrapped too. The toolbar and sidebar are excluded from the drawing
area; toggle following off with Ctrl+F to reach sidebar controls while drawing.

**Show Guides** is on by default and switches the centerline, initial six-axis
guides, four bend directions, current straight length, bend angle and actual local
radius together. Normal arrows default to opaque white and selected arrows to
opaque warm yellow. All six initial axes and four bend choices, screen arrows,
world guides and the start selector read the same live global color preferences.
World-axis bend labels use signed X/Y/Z; non-axis headings use vector components.
The supported bend is 90 degrees; a deadzone shows an unset angle. Length uses
scene units and scene scale, or raw Blender units when no unit system is selected.
The start selector remains visible even when drawing guides are hidden.

The initial six-axis display projects the route start; the four-way bend display
projects the current pipe tip. These visual anchors are independent of the mouse
origin used for gesture selection, in manual and following modes. Guides clamp
inside viewport edges for readability and draw a line back to the real projection.

Native RGBA swatches in the sidebar and add-on preferences provide a color wheel,
Hex entry and Alpha. Display-space `COLOR_GAMMA` properties go directly to overlay
shaders, with no extra conversion. The restore icon resets both colors and their
opacity. Installed colors use `AddonPreferences`, including defaults for older
preferences without these fields. Automatic preference saving is debounced after
editing; when disabled, use Blender's Save Preferences command. Direct source
registration uses an editable session fallback on WindowManager, not scene data.

## Geometry And Persistence

The object is a curve. Bezier knots sample quarter-circle fillets and retain exact
analytic tangents, including where straight tails have zero length. Evaluation
uses the sampled knots. A shared, version-marked Geometry Nodes group uses a
circular profile and Curve to Mesh with Fill Caps, then rotates each ring from
Blender's estimated knot tangent to its analytic tangent. This prevents an
extremely short tail from overlapping its cap or neighboring arc. Solid pipes have
no inner surface; hollow Mesh pipes use inner walls and annular rims. Body faces are smooth and the two filled ends remain flat and
perpendicular to the endpoint headings. Sampling is performed in object space.

The object stores a local-space route recipe in `line_pipe_route_v1`. The
`line_pipe` object property group stores diameter, bend radius, radial segments,
and bend segments. The existing `bend_radius` key now holds Radius Limit. Routes
that previously fit the full radius retain that radius. Legacy sweep groups are
upgraded on rebuild without editing their shared node groups in place. Parameter
changes rebuild from the recipe. Invalid dimensions
restore the last accepted values and show a localized error.

Two object-local endpoint metadata entries are retained and read by the
connection adapter. Legacy port metadata is adapted locally;
the extension does not import or require another pipe system. Visible branding is PipeWorks;
extension ID `line_pipe`, operator names, and saved property keys remain stable.

The language button switches all local UI strings without changing Blender's
global language. Installed preference storage survives restart when saved; a
scene property provides fallback storage for direct source registration.

## Port Connections And Groups

Library families retain separately authored edge-count variants. E selects the
exact count; missing sizes leave the drawing intact. Plain two-port Mesh fittings
can continue a drawing after uniform scaling when both profiles match. Library
connections never silently retessellate authored mouth rings. The library's
Copy AI Fitting Prompt supplies localized topology and parameter requirements
with a replaceable design description. Procedural library pieces retain editable
length and profile recipes; arbitrary authored meshes retain their actual geometry.

Connect and Groups share the drawing panel and language preference. A finished
drawing becomes the moving End. The port picker projects each available circular
end into the viewport and picks the nearby ring; it also works on converted native
Meshes. Navigation passes through; Escape, save/load, undo and disable remove the
picker overlay.

Port adapters read native local endpoint metadata, this extension's recovered
ports and compatible Pipe Assembly component records. Object transforms produce
world positions and inverse-transpose normals. Circular cross sections must remain
circular after scaling; active deforming modifiers are refused. Saved links reserve
occupied endpoints. Missing old records may be recovered from external circular
cap/annular planes; verified straight or single circular right-angle meshes also
recover a rebuildable recipe. Other Mesh shapes can have ports without a curvature
recipe.

Direct docking computes one rigid transform for the entire moving group. The
moving outward normal becomes opposite the anchor normal; roll rotates the group
about that joined axis. Preview is reversible, committing adds a saved direct link,
and native Undo/Redo restores transforms and records. A single straight pipe disables
roll. Parent configurations that cannot preserve the rigid transform are refused.

Distance bridging leaves originals fixed. It tests automatic lead-outs, orthogonal
routes and detours, preferring the source group's rotated axes when compatible;
skew endpoints can use a spatial Bezier fallback. Smooth routes use tangent circular
fillets where orthogonal, and angular routes use mitered cross sections. Radius,
range, available length, self-proximity, triangle area, solid volume, manifold edges
and nonadjacent face crossings are checked. This checks connector geometry, not a
global scene collision route. Outer diameters must match. Two hollow ends require
matching bores; a mixed solid/hollow pair uses a solid bridge.

Connection records retain endpoints, mode, roll, bridge object and rebuild options.
Connecting merges groups; explicit grouping merges existing member sets. Moving
objects does not silently reroute: Update Connections rebuilds affected bridges,
and Apply Settings to Bridge changes the selected bridge from the current Connect
options. Disconnect removes relevant new records and their owned bridges. Old
add-on occupancy stays reserved; old historical link graphs are not migrated.

Curvature matching takes the first selected group as reference. The second, active group is edited. Each selected
group independently needs a parallel/perpendicular direction frame, irrespective
of world rotation. Uniform scaling is supported; shear/nonuniform scaling is
refused. The reference radius is the smallest actual fillet radius in its group,
or the active straight pipe's radius setting. Every bend in the second group is
staged with that exact world radius; if any cannot fit, nothing is applied.
Transforms, endpoints and material slots remain. Native Curve remains Curve and
native converted Mesh remains Mesh. Arbitrary or skew Mesh recipes cannot be matched.

Repair Mesh works on a data copy: near-duplicate merge, degenerate-edge dissolve,
normal recalculation, then topology/area/intersection validation. Unresolved defects
retain the original data. This is a conservative cleanup, not an arbitrary remesher.

## Panel Inputs

| Input | Meaning |
| --- | --- |
| Diameter | Solid circular diameter in scene units |
| Radius Limit | Maximum centerline radius; local circular fillets fit available length, remaining above the pipe radius |
| Radial Segments | Circular profile edge count, 60 by default |
| Bend Segments | Samples per quarter-circle fillet, 4 to 64 |
| Start From | Point, surface, coordinates, 3D Cursor, or mesh face index |
| Initial Direction | Mouse six axes, signed axis, face normal, or custom vector |
| Surface Offset | Offset from the hit face along its outward normal |
| Face Index | Zero-based polygon index on the active mesh |
| Turn Key | B, T, F, C, or V |
| Follow Tip | Follow translation and edge wrapping; Ctrl+F toggles during drawing |
| Show Guides | Direction, length, bend angle and local radius overlays |
| Normal / Selected | Independent global arrow RGBA colors, default white / warm yellow |
| Restore Default Arrow Colors | Restore both colors and full opacity |

---

## 简体中文

### 绘制状态

按下 Ctrl+P 打开左右起点选择器。水平摆动至少 32 像素后确认：左侧为世界原点，
右侧为表面点选。松开快捷键不会选择起点。点选通过射线识别可见网格，以命中点
加表面偏移作为起点；没有命中时继续等待。确认后重建鼠标基准，摆动位移不产生
管长。PipeWorks 不注册单独 P 或 Shift+P。绑定排在插件 Object Mode 键位最前，
优先于原生 Parent；不修改默认键位条目。禁用即移除插件绑定，Ctrl+P 恢复原生
Parent，重复注册不会产生多份快捷键。

首段有世界坐标正负六轴方向。鼠标位移选择最近的轴标签并决定长度；6 像素死区
和边界防抖减少抖动。轴线投影重叠或正对视线时，指示箭头展开为成对相反的六向
布局，保证全部方向仍可选择。

按住转弯键固定来管，预览四个垂直方向。每次开始转弯，鼠标移回当前管头的可见提示
中心；鼠标已经跑出视口、隐藏提示时也能回位。管头在屏幕外时提示夹取到绘制区域内；
无法投影时鼠标回到视口中心。自动移动不增加管长、不选择方向，持续按住不会反复回位。
14 像素死区避免误转。松开只确认一个
弯头，没有选择时松开则保持路线。弯曲半径上限是中心线半径的最大值。局部圆角
先取上限与相邻段长的最小值；相邻圆角超出共用段时，按比例压缩可用内侧半径。
后续约束可能留下未用直线段；这是确定性局部适配，不是全局最优分配。

设管半径为 `a`，局部半径 `r` 须大于 `a`；共用段须容纳 `r1 + r2`。单个 90 度
圆角各消耗来管与出管 `r` 的长度。因此，理想单弯腿长下限为大于 `a`，两弯之间为
大于 `2a`（即直径），与用户半径上限无关。局部半径下限仅增加
`直径 * 2^-16` 的 float32 精度保护，不再使用管径 2% 的余量或一律两倍半径上限。
保护量不会随半径上限增大；直径 0.2 时约为 0.00000305 单位。确实放不下或
数值塌缩时给出本地化提示。预览与松开确认采用相同的出管长度和圆角适配。

Enter 保存配方并恢复渲染；退格撤回最新弯头，撤回首弯后恢复六轴定向。Esc、
右键、窗口失焦、场景保存/加载或撤销会取消未完成预览。完成的管道支持原生整条
一步撤销和重做。

### 导航与辅助

旋转、平移、缩放、Alt+中键轴向视角切换、触控板及 NDOF 事件交给 Blender，
Alt 修饰键和鼠标移动事件也交给原生手势键位处理。插件检测视图旋转、位置、距离
及投影变化，导航后的首次鼠标移动重建基准且不改变管长。拖动旋转、平移或缩放时，
管长按导航前捕获的像素比例，以正常绘制灵敏度的 **50%** 跟随鼠标；包括首段自动
轴向选择在内，均保持已经选择的管道方向。原生视角移动速度保持原样，反馈期间跟随
管头不牵动摄像机。松开后结束监听、重建基准并恢复正常绘制速度；结束绘制也会清理
待执行回调。弯头预览中导航保持来管长度，清除旧候选，
后续移动建立新的四向选择基准。

**跟随管头**默认关闭，绘制时可按 **Ctrl+F** 切换。跟随只平移视图，保留旋转、
缩放与投影；手动导航建立新的跟随偏移。输入比例在重建基准时固定，避免移动视图
反馈改变输入。鼠标接近视口边缘时回卷至内部，输入基准同步移动，因此回卷事件
不增加管长。快速越过边缘的移动同样会回卷。工具栏和侧栏不计入绘制区域；绘制中
按 Ctrl+F 关闭跟随后可进入侧栏切换其他开关。

**显示辅助提示**默认开启，统一控制中心线、首段六轴、弯头四向、当前直线段长度、
弯头角度及实际局部半径。普通箭头默认不透明白色，选中方向默认不透明暖黄色。
首段六轴、弯头四向、屏幕/世界辅助和起点选择器实时读取同一组全局颜色偏好。世界轴方向
使用带正负号的 X/Y/Z，其他方向显示向量分量。当前仅支持
90 度弯头，选择死区显示未确定角度。长度遵循场景单位及缩放；无单位系统时显示
原始 Blender 单位。关闭画管辅助不会隐藏起点选择器。

首段六轴显示投影到路线起点，四向转弯显示投影到当前管端。视觉锚点与鼠标手势
选择使用的输入原点分开，手动模式和跟随模式均保持锚定；为保证边缘可读而夹取
提示时，绘制一条连接线到真实投影。

侧栏及插件偏好中的原生 RGBA 色块支持色盘、Hex 和 Alpha。`COLOR_GAMMA`
显示空间数值直接送到叠加层着色器，不再额外转换。恢复图标同时恢复两色和不透明度。
安装版使用 `AddonPreferences`，旧偏好缺少新字段时使用默认值。自动保存开启时，
颜色编辑停止后延迟保存；关闭时使用 Blender「保存偏好设置」。源码直接注册时使用
WindowManager 上可编辑的本次会话回退值，不向场景写入颜色。

### 几何与保存

对象为曲线，Bezier 控制点采样四分之一圆弧并保存精确解析切向，直线尾段为零时
仍保留端部朝向；求值使用采样点。共享且带版本标记的 Geometry Nodes 组使用圆形
轮廓与开启 Fill Caps 的 Curve to Mesh，再将每圈截面从 Blender 估算切向旋转至
解析切向，避免极短尾段与端盖或圆弧穿插。实心模式没有内壁；空管网格带内壁和环形端面。
侧面平滑，实心两端平整封口并
垂直于端点朝向；采样在对象局部空间完成。

对象的 `line_pipe_route_v1` 保存局部空间路线，`line_pipe` 属性组保存直径、
弯曲半径、圆周及弯头分段。既有 `bend_radius` 键现在表示半径上限；原本容纳完整
半径的路线仍使用原半径。旧扫掠节点组在重建时升级，不原地改动其共享节点。
尺寸修改按配方重建，无效值回退并显示本地化错误。

连接适配现在读取两端局部空间元数据，并在本地兼容旧件记录，无需导入或启用
其他管道系统。对外品牌为 PipeWorks，内部扩展 ID、操作符及数据键保持稳定。

语言按钮仅切换插件界面，不改变 Blender 全局语言。安装偏好保存后可跨重启保留；
源码直接注册时由场景属性提供语言回退存储。

### 管口连接与管道组

管件库按边数保存独立制作的版本，E 接续选用完全同边数的版本，缺规格时保留当前绘制。
普通双口网格等比缩放后两端截面匹配时也能接续；连接不会悄悄改变库件的管口边环。
「复制 AI 管件提示词」包含本地化的拓扑、参数要求及可替换的设计描述区。
程序化库件保留长度和截面配方，普通自定义网格保留实际几何。

连接、管道组与绘制共用面板及语言偏好，画完自动设为移动终点。管口选择器把可用圆口
投影到视口，点击附近圆环选定，也支持转换后的原生 Mesh。导航事件交给 Blender；
Esc、保存/加载、撤销与禁用都会清理点选叠加层。

端口适配读取原生局部管口、识别后的端口及兼容 Pipe Assembly 组件记录。对象变换产生
世界位置，法线按逆转置变换；缩放后截面必须仍为圆，活动形变修改器会拒绝。
保存的连接占用对应端口。旧记录丢失时，可从外露的圆形端盖/环形平面恢复；验证后的
直管或单个圆形直角弯也恢复重建配方。其他 Mesh 可有管口但没有曲率配方。

直接连接计算移动整组的同一个刚性变换，使移动口朝外法线与固定口相反。
滚转绕连接轴旋转整组。预览可取消恢复，提交后保存直接连接，原生撤销/重做恢复位置与记录。
单根直管禁用滚转；无法保持刚性变换的父级配置拒绝处理。

距离连接固定原管，测试引出段、正交路线与绕行候选，兼容时优先使用源组旋转后的坐标轴；
异面端口可采用空间 Bezier 过渡。正交平滑路线使用相切圆弧，折角路线使用斜接截面。
检查半径、距离、可用长度、自靠近、三角面积、实体体积、流形边及非相邻面穿插。
检查范围为连接段自身，不对全场景绕障。外径需一致，两端中空时内径需一致，
实心/中空混接生成实心桥接。

连接记录保存两端、模式、滚转、桥接对象及重建选项。连接自动合组，手动成组也合并既有成员。
移动对象不会悄悄重算路线，使用更新连接管；将设置应用到连接管会按连接页参数重建所选桥接。
断开连接删除相关新记录及其桥接。旧插件记录的占用仍保留，不迁移其历史连接图。

曲率同步以先选的组为标准，只调整第二个活动组。各组内部方向需平行或垂直，组可以任意旋转。
支持统一缩放，拒绝剪切/非均匀缩放。参考半径为组内最小实际圆角半径，纯直管时取活动管的
半径设置。先以相同世界半径预建第二组的弯头，任一放不下则不应用任何修改。
保留对象变换、端点及材质槽，原生 Curve 保持 Curve，转换后的原生 Mesh 保持 Mesh。
不支持任意网格中心线或异面曲线的曲率匹配。

修复网格在数据副本上合并极近重复点、消除退化边、重算法线，再验证拓扑/面积/相交。
无法解决的缺陷保留原数据。这是保守清理，不是任意形状的重建拓扑工具。

### 面板参数

| 参数 | 含义 |
| --- | --- |
| 直径 | 场景单位下的实心圆截面直径 |
| 弯曲半径上限 | 中心线半径最大值；圆角适配可用段长，局部半径保持大于管半径 |
| 圆周分段 | 圆形截面边数，默认 60 |
| 弯头分段 | 每个四分之一圆弧 4 至 64 段 |
| 起点方式 | 放置点、表面、坐标、三维游标或网格面编号 |
| 初始方向 | 鼠标六轴、指定轴向、面法线或自定义向量 |
| 表面偏移 | 沿命中面朝外法线的偏移距离 |
| 面编号 | 活动网格上从零开始的面编号 |
| 转弯按键 | B、T、F、C 或 V |
| 跟随管头 | 视图跟随平移与边缘续移，绘制时按 Ctrl+F 切换 |
| 显示辅助提示 | 方向、长度、弯头角度与局部半径叠加显示开关 |
| 普通箭头 / 选中箭头 | 独立的全局 RGBA 颜色，默认白色 / 暖黄色 |
| 恢复默认箭头颜色 | 同时恢复两色及完全不透明 |
