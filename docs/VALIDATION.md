# Validation

## 0.5.0 - 2026-11-04

Windows / Blender 5.2.2 LTS passed 179 integration, 326 compact-bend and 206
connection assertions, plus the profile/variant suite, installed-ZIP connection
restart, actual ZIP installation and preference restart. Native installed-ZIP
viewport checks passed 185 drawing, 41 routing, 83 navigation and 35 connection
assertions.

E selected a saved 37-edge variant from a 24/37 family, adapted its diameter/bore,
resumed at its outlet, and supported Backspace, Escape and whole-chain Undo/Redo.
Missing sizes produced a localized notice without changing the drawing. A plain
authored hollow Mesh continued through consecutive fittings with P1/P2 port keys
and committed three pieces/two joints. Both complete AI prompts copied through
the installed operator, restoring the previous clipboard afterward. Backend
checks covered duplicate variants, missing-size rollback, actual library ring
preservation, uniform scaling, bore refusal and anchored length edits.

Manifest validation, exact source/ZIP parity and repeat-build byte equality
passed. Eight native 2400 x 1210 perspective captures cover drawing, connections,
and English/Chinese fitting libraries. Only disposable scenes and isolated
profiles were used. The normal Blender configuration was not changed.

## 0.4.1 - 2026-11-03

Windows input in Blender 5.2.2 verified successive 60 → 48 → 60 → 72 drags,
direct dropdown selection of 24, and one-step Undo/Redo on a selected pipe.
Fast gestures recover the original press coordinate and any release delivered
with the next event. Package and background regression checks passed.

## 0.4.0 - 2026-11-03

Validated locally with Windows and Blender 5.2.2 LTS.

- The native suites passed 185 interaction, 41 routing, 83 navigation and 21
  connection assertions. The connection suite picks the reference first, checks
  24-to-60 edge matching and roll snapping, verifies Undo/Redo, and completes
  a hollow drawing through viewport events.
- The profile suite reads actual geometry for all ten presets and a 601-edge
  free count, checks both bridge phases and refusal without retessellation,
  measures hollow rims, and saves/imports/inserts a ten-port asset with one
  disabled port and mixed counts.
- Background drawing, compact bend, connection and restart suites passed.
  The installed ZIP reopens the example and retessellates the 24-edge moving
  Mesh to the 60-edge reference without moving that reference.
- The library uses local single-fitting .blend exchange.

## 0.3.0 - 2026-11-03

Validated locally on Windows / Blender 5.2.2 LTS.

| Evidence | Result |
| --- | --- |
| Drawing / compact geometry | 179 / 326 assertions passed |
| Connections backend | 206 assertions passed: all endpoint pairs, whole-group rigid roll, fixed-end smooth/angular routes, rotated curvature groups, legacy compatibility and atomic refusal |
| Installed ZIP native UI | 185 drawing interaction / 41 routing / 83 navigation / 18 connection assertions passed |
| Native connection Undo/Redo | Direct pose/link, distance bridge/occupancy and group curvature restored |
| Windows input | Eyedropper picked anchor End, converted moving Mesh docked, live 45-degree roll confirmed; one link retained |
| Fresh-process restore | Source-authored scene opened by the installed ZIP: links, pointers, port occupancy and native Mesh parameters survived; saved bridge updated |
| Legacy saved examples | 49 pipe meshes across four original examples recovered compatible exposed ports; no manifold/area/volume flags in those files |
| Legacy numerical reproduction | Bend radius approaching outer pipe radius produced edges around 4.8e-12 and 14 tiny triangles; new validation rejects collapsed/tiny/self-crossing results |
| Repair | Shared original Mesh data preserved; cleaned copy passed manifold, area, volume and self-intersection checks |
| Local upgrade | Existing 0.2.2 backed up and upgraded to 0.3.0; installed files match the ZIP and normal user preferences are unchanged |
| Package | 14 extension files; syntax, manifest validation, exact ZIP/source parity and reproducible bytes passed |

The old reported Mesh fault was not precisely identified by the user. The numerical
case above is a reproduced failure class, not proof that the user's earlier scene
had that exact fault. Original legacy examples were inspected without overwriting
them. Missing legacy endpoint records are handled by circular-end recognition;
arbitrary shapes do not receive speculative curvature recipes.

The self-authored connection example also reopened in a fresh installed-ZIP process
with all three links and its Connect tab restored. Runtime is standalone. Historical
old-add-on link graphs are not rewritten. Connector checks do not provide full-scene
obstacle avoidance or boolean welding.

## 0.2.2 - 2026-11-03

Validated locally on Windows / Blender 5.2.2 LTS.

| Evidence | Result |
| --- | --- |
| Main installed-ZIP interactions / source drawing | 185 / 41 assertions passed |
| Dedicated installed-ZIP navigation | 83 assertions passed |
| Navigation gain | Orbit, pan and drag zoom measured exactly 0.5 for extension and retraction |
| Resume | Normal drawing speed restored after release, with a stable input baseline |
| Direction and following | Selected first axis preserved; Follow Tip supports the same 0.5 gain without taking over native camera motion |
| Cleanup | Disabling during a native drag removes feedback references and pending callbacks; removed RNA operator slots are tolerated |
| Geometry / preferences | 179 integration + 326 compact assertions, actual ZIP install and preference restart passed |
| Package | Manifest validation, exact source/archive parity and reproducible ZIP bytes passed |
| Local upgrade | Existing 0.2.1 backed up and upgraded to 0.2.2; normal user preferences unchanged |

Navigation is tested through Blender's native event queue and actual viewport
operators. The dedicated suite covers positive and negative mouse displacement,
Ctrl+MMB drag zoom, normal-speed continuation, automatic first-axis selection,
Follow Tip and add-on disable during a drag. A transient observer receives native
navigation moves without consuming them; length feedback uses the pre-navigation
pixel scale and keeps the chosen heading. The existing B-return, Alt+MMB and
compact-bend regressions remain covered. No new physical-pointer claim is made
for navigation; the separate 0.2.1 Windows-input evidence is retained below.

## 0.2.1 - 2026-11-03

Validated locally on Windows / Blender 5.2.2 LTS.

| Evidence | Result |
| --- | --- |
| Integration / compact geometry | 179 / 326 assertions passed |
| Native event queue | 141 installed-ZIP interaction + 41 source drawing assertions passed |
| Navigation | Repeated Alt+MMB axis gestures with manual and following views; stable length and continued extension |
| Turn pointer | Current-tip return, outside-viewport recovery, hidden guides, repeated turns and held-key stability |
| Quick tap | Key release queued before the cursor move preserves length and commits no unintended bend |
| Windows input | Real OS cursor move matched the requested return with zero-pixel error; a 2-unit pipe stayed 2 units, then extended to 2.881634 |
| Package | Actual ZIP install, saved preferences restart, extension validation, exact source/archive parity and reproducible bytes passed |
| Local upgrade | Existing 0.2.0 installation backed up and upgraded to 0.2.1; normal user preferences unchanged |

The Windows input check used the installed ZIP in an isolated disposable scene,
without native event simulation. It caught a fast-tap event-ordering issue: release
can precede the OS cursor move. Rebasing at the pending destination prevents that
move from extending the pipe or changing its initial axis. The automated native
suite now covers the same ordering. Evidence stays in ignored verification folders.

## Earlier 0.2.0 Validation

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

### 0.5.0 - 2026-11-04

Windows / Blender 5.2.2 LTS 通过集成 179 项、紧凑弯头 326 项、连接 206 项，
以及截面/库件版本、新进程重开连接、真实 ZIP 安装和偏好重启检查。
真实安装包的原生视口验证通过画管 185 项、路径 41 项、导航 83 项和连接 35 项。

E 从 24/37 边版本组选择实际 37 边版本，适配直径与内孔并从出口继续，支持退格、
取消及整组撤销重做。缺规格时保留绘制并显示提示。普通自定义空心网格使用 P1/P2
管口连续接入，提交三件和两个连接。安装后的操作符可复制完整中英文提示词，随后恢复原剪贴板。
后台验证重复规格、缺规格回退、库件边环保留、等比缩放、内孔不匹配拒绝和固定端长度编辑。

清单校验、源码/ZIP 一致和重复构建逐字节一致均通过。八张原生 2400 × 1210 透视截图
覆盖绘制、连接及中英文管件库；使用临时场景与隔离配置，未改常用 Blender 配置。

### 0.4.1 - 2026-11-03

在 Blender 5.2.2 中用 Windows 输入验证 60 → 48 → 60 → 72 连续拖动、下拉直选 24，
以及已选管道的一步撤销和重做。快速手势读取实际按下位置，并处理后续事件记录的松手。
安装包和后台回归通过。

### 0.4.0 - 2026-11-03

环境为 Windows 和 Blender 5.2.2 LTS。

- 原生套件通过绘制交互 185 项、路线 41 项、导航 83 项、连接 21 项。连接套件验证先选基准、
  24 边对齐 60 边、滚转吸附、撤销重做与视口绘制空管。
- 截面套件从实际几何验证十种预设及自由 601 边、补管两端相位、失败时保留原边数、真实内壁，
  以及十口混合边数管件的禁用状态和本地库保存、导入、插入。
- 绘制、紧凑弯、连接和重启后台套件通过。安装 ZIP 重开示例后，24 边移动网格可调整为
  基准的 60 边，基准位置保持原样。
- 管件库通过单件 .blend 文件在本地交换。

### 0.3.0 - 2026-11-03

环境为 Windows / Blender 5.2.2 LTS。

| 凭据 | 结果 |
| --- | --- |
| 绘制 / 紧凑弯几何 | 179 / 326 项断言通过 |
| 连接后台 | 206 项通过，覆盖四种端口配对、整组刚性滚转、固定两端平滑/折角路线、旋转组曲率、旧件及失败原子性 |
| 真实安装 ZIP 原生 UI | 绘制交互 185 / 路线 41 / 导航 83 / 连接 18 项通过 |
| 原生连接撤销/重做 | 吸附位置与记录、桥接与占用、组曲率均恢复 |
| Windows 输入 | 吸管选中固定终点，转换后的移动 Mesh 吸附，实时预览并确认 45 度滚转，保留一条记录 |
| 新进程恢复 | 安装 ZIP 读取源码生成场景，连接、对象指针、占用与原生 Mesh 参数保留，已有桥接可更新 |
| 旧保存示例 | 四个原始示例共 49 条管道恢复兼容的外露管口，未发现流形/面积/体积异常 |
| 旧算法数值复现 | 弯曲半径接近外管半径时出现约 4.8e-12 的边及 14 个极小三角面，新验证拒绝塌缩/极小/自交结果 |
| 修复 | 保留共享原网格，清理副本通过流形、面积、体积与自交检查 |
| 本机更新 | 备份 0.2.2 并升级 0.3.0，安装文件与 ZIP 一致，常用用户偏好不变 |
| 安装包 | 14 个扩展文件，语法、清单、源码/包一致性及可复现字节通过 |

用户未明确旧 Mesh 异常的具体形式。以上数值问题是一类已复现故障，不能断言用户之前看到的
就是同一个问题。旧示例只读检查，未覆盖原件。缺失管口记录可从圆形端口识别恢复，
任意形状不会猜测曲率配方。

自建连接示例也已用新进程安装 ZIP 重开，保留三条连接与连接页签。运行时独立，
不改写旧插件历史连接图。连接段检查不包含全场景绕障或布尔焊接。

### 0.2.2 - 2026-11-03

环境为 Windows / Blender 5.2.2 LTS。

| 检查 | 结果 |
| --- | --- |
| 真实 ZIP 主交互 / 源码绘制 | 185 / 41 项通过 |
| 真实 ZIP 专项导航 | 83 项通过 |
| 导航倍率 | 旋转、平移、拖动缩放的伸长及缩短均测得精确 0.5 倍 |
| 续画 | 松开后恢复正常绘制速度，输入基准稳定 |
| 方向与跟随 | 首段既定轴向保持；跟随管头同样支持 0.5 倍反馈，不接管原生视角运动 |
| 清理 | 拖动中禁用插件，清除反馈引用与待执行回调，并兼容已移除的 RNA 操作符槽 |
| 几何与偏好 | 集成 179 项、紧凑圆弯 326 项，以及真实安装和偏好重启通过 |
| 安装包 | 清单校验、源码/包逐字节一致及可复现构建通过 |
| 本机更新 | 备份现有 0.2.1 并升级到 0.2.2，常用用户偏好文件保持不变 |

通过 Blender 原生事件队列和真实视口操作符验证。专项套件覆盖正负鼠标位移、
Ctrl+中键拖动缩放、恢复正常速度、首段自动轴向、跟随管头及拖动中禁用插件。
临时监听接收原生导航的移动事件但不拦截；管长反馈采用导航前的像素比例，保持
已选方向。B 回位、Alt+中键及紧凑弯头回归继续覆盖。本次导航未新增物理鼠标输入
验证，下面保留独立的 0.2.1 Windows 输入记录。

### 0.2.1 - 2026-11-03

环境为 Windows / Blender 5.2.2 LTS。

| 检查 | 结果 |
| --- | --- |
| 集成 / 紧凑圆弯 | 179 / 326 项通过 |
| 原生事件队列 | 真实安装 ZIP 交互 141 项 + 源码绘制回归 41 项通过 |
| 导航 | 手动及跟随视图多次 Alt+中键切换，管长稳定并可续画 |
| 转弯回位 | 当前管头定位、视口外收回、隐藏提示、连续转弯及持续按键稳定性通过 |
| 快速点按 | 松键先于鼠标回位事件时，管长不变且不会意外确认弯头 |
| Windows 输入 | 真实系统鼠标回位误差为零像素；2 单位管道回位后仍为 2，随后正常延长至 2.881634 |
| 安装包 | 真实 ZIP 安装、偏好重启、扩展校验、源码/包逐字节一致与可复现构建通过 |
| 本机更新 | 备份原 0.2.0 并升级至 0.2.1，常用用户偏好文件保持不变 |

Windows 输入检查使用隔离临时场景中的真实安装 ZIP，未启用原生事件模拟。
该检查发现快速点按时松键可能早于系统鼠标移动；现保留待回位目标作为输入基准，
避免自动移动延长管道或切换首段轴向。自动原生回归覆盖同一事件顺序。
凭据保存在 Git 忽略的验证目录中。

### 既有 0.2.0 验证

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
