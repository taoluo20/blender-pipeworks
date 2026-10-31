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
choices. A 14-pixel deadzone avoids unintended bends. Release commits exactly one
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

Orbit, pan, zoom, trackpad and NDOF events pass through to Blender. The tool
detects changes to rotation, view location, distance and projection. The next
mouse movement captures a fresh input origin without changing route length.
There is no persistent middle-button lock: Blender's native navigation operator
can consume its release event. Navigating during a bend clears its stale choice;
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
extremely short tail from overlapping its cap or neighboring arc. There is no
inner surface. Body faces are smooth and the two filled ends remain flat and
perpendicular to the endpoint headings. Sampling is performed in object space.

The object stores a local-space route recipe in `line_pipe_route_v1`. The
`line_pipe` object property group stores diameter, bend radius, radial segments,
and bend segments. The existing `bend_radius` key now holds Radius Limit. Routes
that previously fit the full radius retain that radius. Legacy sweep groups are
upgraded on rebuild without editing their shared node groups in place. Parameter
changes rebuild from the recipe. Invalid dimensions
restore the last accepted values and show a localized error.

Two object-local endpoint metadata entries are retained for future adapters.
No automatic connection code reads them in this release. Neither the extension
nor the repository imports another pipe system. Visible branding is PipeWorks;
extension ID `line_pipe`, operator names, and saved property keys remain stable.

The language button switches all local UI strings without changing Blender's
global language. Installed preference storage survives restart when saved; a
scene property provides fallback storage for direct source registration.

## Panel Inputs

| Input | Meaning |
| --- | --- |
| Diameter | Solid circular diameter in scene units |
| Radius Limit | Maximum centerline radius; local circular fillets fit available length, remaining above the pipe radius |
| Radial Segments | Circular profile sides, 8 to 128 |
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

按住转弯键固定来管，预览四个垂直方向；14 像素死区避免误转。松开只确认一个
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

旋转、平移、缩放、触控板及 NDOF 事件交给 Blender。插件检测视图旋转、位置、距离
及投影变化，导航后的首次鼠标移动重建基准且不改变管长。不使用持续的中键锁定，
因为 Blender 的原生导航操作可能消耗释放事件。弯头预览中导航会清除旧候选，
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
解析切向，避免极短尾段与端盖或圆弧穿插。没有内壁，侧面平滑，两端平整封口并
垂直于端点朝向；采样在对象局部空间完成。

对象的 `line_pipe_route_v1` 保存局部空间路线，`line_pipe` 属性组保存直径、
弯曲半径、圆周及弯头分段。既有 `bend_radius` 键现在表示半径上限；原本容纳完整
半径的路线仍使用原半径。旧扫掠节点组在重建时升级，不原地改动其共享节点。
尺寸修改按配方重建，无效值回退并显示本地化错误。

两端局部空间元数据为后续适配保留，本版没有自动连接代码读取它们，也不导入
其他管道系统。对外品牌为 PipeWorks，内部扩展 ID、操作符及数据键保持稳定。

语言按钮仅切换插件界面，不改变 Blender 全局语言。安装偏好保存后可跨重启保留；
源码直接注册时由场景属性提供语言回退存储。

### 面板参数

| 参数 | 含义 |
| --- | --- |
| 直径 | 场景单位下的实心圆截面直径 |
| 弯曲半径上限 | 中心线半径最大值；圆角适配可用段长，局部半径保持大于管半径 |
| 圆周分段 | 8 至 128 |
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
