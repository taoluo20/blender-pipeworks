# Changelog

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
