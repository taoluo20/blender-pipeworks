# Changelog

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
