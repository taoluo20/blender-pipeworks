# Validation

Version **0.2.0**, validated on **2026-10-30**, Windows / **Blender 5.2.2 LTS**.
Only Blender 5.2+ is declared supported.

| Evidence | Result |
| --- | --- |
| Existing integration and color preferences | 179 assertions passed |
| Compact-bend integration | 326 assertions passed |
| Native event queue | 102 installed-ZIP interaction + 41 source drawing assertions passed |
| Actual release ZIP | Installed, enabled, and source bytes matched |
| Saved state | Recipe, radius limit and parameter edits survived save/reopen |
| Global preferences | Language and independent RGBA colors restored in a new process, then reset |
| Native color picker | Wheel, Hex and Alpha edited through Windows UI input; reset persisted across restart |
| Extension validation | Blender manifest/archive validation passed |
| Reproducibility | Two builds produced identical ZIP bytes |
| Public previews | Five native 2400 x 1280 non-isometric perspective viewport captures |
| Local diagnostic screenshots | White/yellow defaults, custom RGBA, native picker, anchored guides, compact bends in both languages, hidden guides and following |

Ctrl+P is tested on selected mesh geometry through Blender's native event queue,
using the installed `bl_ext.user_default.line_pipe` extension. It opens the
selector, supports left-origin and right-surface gestures, and does not execute
parenting. Plain P and Shift+P do not invoke PipeWorks. Three disable/enable
cycles register exactly one shortcut each. The default Object Mode keymap stays
unchanged; after disabling, native Ctrl+P and Enter successfully parent two
disposable meshes. The test also captures the restored Parent popup.

Draw-call receipts and inspected screenshots verify white normal arrows and a
warm yellow selected direction for initial six-axis and four-way bend guides.
Custom colors and Alpha update during drawing, with identical RGBA shared by
screen/world overlays and no per-axis color exceptions. Reset restores both
defaults immediately. In manual mode, the six-axis display stays projected at
the start after navigation, and bend directions stay at the tip despite a distant
pointer. Edge-clamped bend guides retain their line to the real projected tip.
Signed axis labels remain visible. Show Guides still controls the overlays;
English and Chinese controls, notices, bend angles, lengths and local radii are
exercised. A successful turn clears an earlier too-short notice.

The installed `bl_ext.user_default.line_pipe` native picker was also operated
through Windows UI input in a separate isolated profile. Entering `309B9680`
displayed `#309B9680`, Alpha 0.502 and stored `(48, 155, 150, 128) / 255` without
extra color conversion. The selected color changed independently through the
wheel and Alpha control; Chinese labels and the restore icon were inspected.
The restore action saved opaque white/warm yellow automatically, confirmed in
a new Blender process. Source-import tests cover editable fallback storage when
no enabled `AddonPreferences` entry exists. Background installed-ZIP tests cover
missing new preference fields, separate color/opacity persistence, cross-scene
storage and reset after restart. Evidence is in ignored `verification/line-pipe/`,
`verification/interaction-ui/` and `verification/manual-interaction/`.

The compact suite checks single, S, U and spatial bends, signed directions,
rotated routes, translated geometry, a small scene scale, low bend resolution,
large radius limits and exact modal guard boundaries. At diameter 0.2 / limit
0.4, single legs of 0.10001 and shared segments of 0.20002 fit circular fillets.
Legs of 0.1 and shared segments of 0.2 are refused because their inner radius
would collapse. The float32 guard is about 0.00000305 at this diameter; it does
not increase with Radius Limit.

Evaluated solids are checked for closed consistently oriented manifold edges,
nonzero face area, no nonadjacent triangle intersections in these local test
shapes, positive volume matching a filled circular sweep, and exactly two flat
caps at the route endpoints. Cap normals and profile diameters are measured.
These checks caught and corrected native sweep tangent estimation overlaps at
very short straight tails. Further checks cover matching preview/commit shapes,
compact undo, invalid dimension rollback, save/rebuild and legacy group upgrade.
The native viewport suite also previews, commits, retracts and finishes compact
single and adjacent bends.

Regression coverage retains all six initial axes, four bend choices, custom turn
keys, native undo/redo, transformed surface starts and procedural mesh conversion.
Repeated orbit/pan/zoom rebases without changing length and then resumes drawing.
Following checks preserve rotation and zoom, maintain input scale, cover three
edge wraps without a length jump, and finish correctly. Stale bend choices,
focus-loss cancellation and active-add-on disable clean up previews, handlers,
timers and warp state.

Native event simulation suppresses OS pointer moves, so requested warp
destinations are fed back through the event queue. These are automated native
events, not exhaustive human hardware tests. The installed-ZIP hardware harness
is available in `tests/manual_interaction.py`. The Windows UI checks above cover
the color picker and preferences; routing coverage uses the native event queue.

All configuration directories are created before launching isolated Blender.
The actual configuration path is asserted before preferences are saved. Tests
use disposable scenes and do not alter regular profiles. Installers, screenshots,
receipts, logs, recovery files and test scenes stay in ignored `dist/` and
`verification/`. Public presentation images retain the separate wide `PERSP`
workflow; local orthographic/interaction diagnostics are not release assets.

This is local bend and drawing validation. It does not establish global
self-intersection prevention, obstacle avoidance, fittings compliance, port
snapping or automatic pipe-network behavior. Some Blender exits report small
unfreed-memory diagnostics; assertions and process exit codes are recorded.

---

## 简体中文

**0.2.0** 验证日期 **2026-10-30**，环境为 Windows / **Blender 5.2.2 LTS**。
只声明支持 Blender 5.2+。

| 检查 | 结果 |
| --- | --- |
| 既有集成与颜色偏好 | 179 项通过 |
| 紧凑圆弯集成 | 326 项通过 |
| 原生事件队列 | 真实 ZIP 交互 102 项 + 源码绘制回归 41 项通过 |
| 真实发布 ZIP | 安装启用、源码逐字节一致 |
| 场景保存重开 | 配方、半径上限和参数编辑保留 |
| 全局偏好 | 新进程恢复语言及独立 RGBA 颜色，然后恢复默认 |
| 原生拾色器 | 通过 Windows UI 输入操作色盘、Hex 和 Alpha，重启保留恢复结果 |
| 扩展校验 | Blender 清单与安装包验证通过 |
| 可复现构建 | 两次 ZIP 逐字节一致 |
| 公开说明图 | 五张原生 2400 x 1280 宽幅非等距透视视口截图 |
| 本地诊断图 | 白/黄默认箭头、自选 RGBA、原生拾色器、锚定提示、中英文紧凑弯、隐藏辅助与跟随 |

Ctrl+P 通过 Blender 原生事件队列，在真实安装的
`bl_ext.user_default.line_pipe` 扩展及选中网格上验证。能进入选择器，左摆原点、
右摆点选表面，且不执行 Parent。单独 P 和 Shift+P 不启动插件。三轮禁用/启用均
只注册一个快捷键，默认 Object Mode 键位条目保持不变；禁用后原生 Ctrl+P 加
Enter 成功将两个临时网格建立父子关系，并记录恢复后的 Parent 弹窗。

绘制调用凭据与截图检查确认：首段六轴和四向弯头普通箭头默认白色，选中默认
暖黄色，带正负号的轴标签保留。绘制中编辑颜色与 Alpha 可即时更新，屏幕/世界
辅助共享同一组 RGBA，没有轴向颜色例外；恢复立即重置两种默认值。手动模式中，
六轴提示导航后仍投影于起点，鼠标远离时转弯提示仍固定于管端；边缘夹取保留
到真实管端投影的连线。显示辅助开关仍有效，覆盖中英文控件、提示、
转弯角度、长度和局部半径；成功进入转弯会清除之前的过短提示。

真实安装的 `bl_ext.user_default.line_pipe` 原生拾色器还在独立隔离配置中通过
Windows UI 输入操作。输入 `309B9680` 后显示 `#309B9680`、Alpha 0.502，实际
保存 `(48, 155, 150, 128) / 255`，没有额外颜色转换。选中色通过色盘及 Alpha
独立修改，并检查中文标签和恢复图标；恢复操作自动保存不透明白/暖黄，新进程
确认重启保留。源码导入检查覆盖没有启用偏好条目时的可编辑回退；后台真实 ZIP
检查覆盖旧偏好缺少新字段、独立颜色/透明度跨场景与重启保存及恢复默认。凭据仅在
忽略的 `verification/line-pipe/`、`verification/interaction-ui/` 和
`verification/manual-interaction/` 中。

紧凑测试覆盖单弯、S/U 弯、空间弯、正反方向、旋转路线、平移几何、小场景比例、
低弯头分段、大半径上限及模态精度保护边界。直径 0.2、上限 0.4 时，0.10001 的
单弯腿长和 0.20002 的共用段可生成圆弯；0.1 的单弯腿长和 0.2 的共用段因内侧
半径塌缩而拒绝。此直径的 float32 保护量约为 0.00000305，不随半径上限增大。

对求值实体检查定向闭合流形、非零面积、这些局部测试形状中无非相邻三角面相交、
正体积符合实心圆截面扫掠，以及恰好两个位于端点的平端盖；同时测量端盖法线和
截面直径。这些检查发现并修复了极短直线尾段处原生扫掠估算切向造成的穿插。
另覆盖预览/确认一致、紧凑撤回、无效尺寸回退、保存重建及旧节点组升级。原生视口
也验证紧凑单弯与连续弯的预览、确认、撤回和完成。

回归保留首段六轴、四向弯头、自定义转弯键、原生撤销/重做、变换后的表面起点及
程序化实体转网格。多次旋转/平移/缩放后等长度重建输入基准并续画；跟随保留旋转、
缩放与输入比例，覆盖三次边缘回卷无长度跳变及完成。旧弯头候选、失焦取消和绘制
中禁用插件均能清理预览、绘制句柄、计时器和回卷状态。

原生事件模拟屏蔽操作系统光标移动，因此将回卷目标重新送入队列。上述为自动原生
事件测试，不代表穷尽人工硬件测试；保留 `tests/manual_interaction.py` 真实 ZIP
硬件输入检查入口。上述 Windows UI 实操覆盖拾色器和偏好，画管覆盖使用原生事件队列。

隔离配置目录均在启动 Blender 前创建，保存偏好前核实实际配置路径。只使用临时
场景，不改动常用配置。安装包、截图、凭据、日志、恢复文件和测试场景仅保存在
忽略的 `dist/` 与 `verification/`；公开说明图继续使用独立的宽幅 `PERSP` 流程，
本地正交或交互诊断图不作为发布附件。

这些结论仅针对局部圆弯和画管，不证明全局自交预防、绕障、工业管件合规、管口
吸附或自动管网行为。部分 Blender 退出会输出少量未释放内存诊断，断言和退出码
均有记录。
