# Features And Logic

## Drawing States

`P` press opens a waiting state. A left-click while held raycasts visible mesh
geometry and uses the hit point plus the configured surface offset. Releasing P
without a hit starts at world zero. Releasing it after a successful click keeps
the selected surface position.

The initial segment has six signed world-axis directions. Mouse displacement
chooses the nearest labeled axis and controls length. A 6-pixel deadzone and small
boundary hysteresis reduce jitter. When axes overlap or point into the view, the
guides spread into an antipodal hexagon so all six choices stay accessible.

Holding the turn key freezes the incoming segment and previews four perpendicular
choices. A 14-pixel deadzone avoids unintended bends. Release commits exactly one
corner; release without a choice leaves the route unchanged. A first bend needs
at least one bend radius of incoming length; adjacent bends need two radii plus
a small clearance. Straight lengths after a bend are clamped to fit its fillet.

Enter completes the recipe and restores rendering. Backspace retracts the latest
bend, returning to six-axis selection when the first bend is removed. Escape,
right-click, losing window focus, scene save/load, and undo cancel an unfinished
preview. Native one-step undo/redo operates on completed drawings.

## Geometry And Persistence

The object is a curve. Its polyline samples include tangent quarter-circle
fillets; a shared, version-marked Geometry Nodes group uses a circular profile
and Curve to Mesh with Fill Caps. There is no inner surface. Body faces are
smooth and the two filled ends remain flat.

The object stores a local-space route recipe in `line_pipe_route_v1`. The
`line_pipe` object property group stores diameter, bend radius, radial segments,
and bend segments. Parameter changes rebuild from the recipe. Invalid dimensions
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
| Bend Radius | Centerline radius, greater than half the diameter |
| Radial Segments | Circular profile sides, 8 to 128 |
| Bend Segments | Samples per quarter-circle fillet, 4 to 64 |
| Start From | Point, surface, coordinates, 3D Cursor, or mesh face index |
| Initial Direction | Mouse six axes, signed axis, face normal, or custom vector |
| Surface Offset | Offset from the hit face along its outward normal |
| Face Index | Zero-based polygon index on the active mesh |
| Turn Key | B, T, F, C, or V |

---

## 简体中文

### 绘制状态

按下 P 进入等待，按住期间左键会射线识别网格表面，以命中点加表面偏移作为起点。
没有命中时松开 P 从世界原点开始；成功点选后松开 P 保留已选起点。

首段有世界坐标正负六轴方向。鼠标位移选择最近的轴标签并决定长度；6 像素死区
和边界防抖减少抖动。轴线投影重叠或正对视线时，指示箭头展开为成对相反的六向
布局，保证全部方向仍可选择。

按住转弯键固定来管，预览四个垂直方向；14 像素死区避免误转。松开只确认一个
弯头，没有选择时松开则保持路线。首个弯头需要至少一个半径的来管长度，连续
弯头之间需两个半径加少量余量；弯头后的直线长度有容纳圆弧的下限。

Enter 保存配方并恢复渲染；退格撤回最新弯头，撤回首弯后恢复六轴定向。Esc、
右键、窗口失焦、场景保存/加载或撤销会取消未完成预览。完成的管道支持原生整条
一步撤销和重做。

### 几何与保存

对象为曲线，多段线采样包含相切的四分之一圆弧。共享且带版本标记的 Geometry
Nodes 组使用圆形轮廓与开启 Fill Caps 的 Curve to Mesh。没有内壁，侧面平滑，
两端填充面保持平整。

对象的 `line_pipe_route_v1` 保存局部空间路线，`line_pipe` 属性组保存直径、
弯曲半径、圆周及弯头分段。尺寸修改按配方重建，无效值回退并显示本地化错误。

两端局部空间元数据为后续适配保留，本版没有自动连接代码读取它们，也不导入
其他管道系统。对外品牌为 PipeWorks，内部扩展 ID、操作符及数据键保持稳定。

语言按钮仅切换插件界面，不改变 Blender 全局语言。安装偏好保存后可跨重启保留；
源码直接注册时由场景属性提供语言回退存储。

### 面板参数

| 参数 | 含义 |
| --- | --- |
| 直径 | 场景单位下的实心圆截面直径 |
| 弯曲半径 | 中心线半径，须大于直径的一半 |
| 圆周分段 | 8 至 128 |
| 弯头分段 | 每个四分之一圆弧 4 至 64 段 |
| 起点方式 | 放置点、表面、坐标、三维游标或网格面编号 |
| 初始方向 | 鼠标六轴、指定轴向、面法线或自定义向量 |
| 表面偏移 | 沿命中面朝外法线的偏移距离 |
| 面编号 | 活动网格上从零开始的面编号 |
| 转弯按键 | B、T、F、C 或 V |
