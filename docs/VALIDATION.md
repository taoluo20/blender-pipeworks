# Validation

Validated on **2026-10-30**, Windows, **Blender 5.2.2 LTS**. Only Blender 5.2+
is declared supported; no older-version compatibility is claimed.

| Evidence | Result |
| --- | --- |
| Standalone integration | 162 assertions passed |
| Native event queue | 41 interaction assertions passed |
| Actual release ZIP | Installed, enabled, and source bytes matched |
| Saved state | Route and parameter edits survived save/reopen |
| Language preference | Chinese restored in a new process, then switched back to English |
| Blender extension validation | Manifest and archive validation passed |
| Reproducibility | Two builds produced identical ZIP bytes |
| Public visuals | Four actual wide perspective viewport captures, English and Chinese |

Integration covers signed six-axis selection in front, top, angled, and edge-on
views; re-aiming before the first bend; locking after a bend; retracting to initial
selection; eight axis/rotated bend cases; manifold edges and positive solid volume;
two flat caps; parameter rebuild and invalid-value rollback; mesh conversion;
transformed face normals; localized control aliases; and registration lifecycle.

The interactive suite sends separate P/B press, mouse-move, and release events
through Blender's native window event queue. It exercises all six starting axes,
surface starts, four turn directions, extension after release, Enter completion,
Backspace, cancellation cleanup, configurable hold keys, and native undo/redo.
These are automated native events, not a claim of exhaustive human hardware testing.

The actual installer is tested in its `bl_ext.user_default.line_pipe` namespace.
Every profile folder is created before launch, and the install test verifies the
actual Blender configuration path before saving preferences. Regular user profiles
and existing user scenes are not modified by this public repository's checks.

Public screenshots use `PERSP`, a near-eye-level modest horizontal turn, and at
least 16:9 framing. Self-authored pipes and a wall are generated for the captures.
Diagnostic orthographic UI screenshots remain local. Raw logs, configuration,
recovery files, and generated artifacts remain ignored; portable scripts are
included so checks can be repeated.

This is a scoped modeling validation. It does not establish obstacle avoidance,
self-intersection prevention, industrial fittings compliance, flow simulation,
port snapping, or automatic network behavior. Some Blender exits report small
unfreed-memory diagnostics; the assertions and process exit codes are recorded.

---

## 简体中文

验证日期 **2026-10-30**，环境为 Windows / **Blender 5.2.2 LTS**。仅声明支持
Blender 5.2+，不承诺更早版本兼容。

| 检查 | 结果 |
| --- | --- |
| 独立集成检查 | 162 项通过 |
| 原生事件队列交互 | 41 项通过 |
| 真实发布 ZIP | 安装启用并逐字节核对源码通过 |
| 场景保存重开 | 路线与参数编辑保留 |
| 语言偏好 | 新进程恢复中文并切回英文 |
| Blender 扩展校验 | 清单与安装包通过 |
| 可复现构建 | 两次 ZIP 逐字节一致 |
| 公开图 | 四张实际宽幅透视视口图，包含中英文 |

集成覆盖前视、顶视、斜视、侧对视角中的六轴选择，首弯前重新定向、首弯后锁定、
撤回后恢复六轴，八种轴向或旋转弯头，闭合流形和正体积、平端盖、参数重建与无效
值回退、网格转换、变换后的面法线、双语属性及注册生命周期。

交互检查通过 Blender 原生窗口事件队列分别发送按下、移动和松开，覆盖六轴起始、
表面起点、四向转弯、松开后延长、Enter、退格、取消清理、自定义按键及撤销重做。
这是自动原生事件验证，不代表对所有实际鼠标和键盘设备的穷尽人工测试。

真实安装在 `bl_ext.user_default.line_pipe` 命名空间验证。隔离目录在启动前创建，
保存偏好前检查 Blender 实际配置路径。本公开仓库的检查不会改动常用配置和已有
用户场景。

公开图为平视附近、适度水平侧转的非等距透视，宽高比至少 16:9，使用自建管道及
墙面。正交交互诊断图仅保留本地；配置、原始日志、恢复文件及生成产物不入 Git，
仓库包含可重复执行的验证脚本。

本验证仅针对建模范围，不证明绕障、自交预防、工业管件合规、流体仿真、端口吸附
或自动管网行为。部分 Blender 退出会输出少量未释放内存诊断；检查断言和退出码
有记录。
