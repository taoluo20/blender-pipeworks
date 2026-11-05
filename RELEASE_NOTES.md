# PipeWorks 0.5.1

Alt+left/middle/right mouse navigation now follows Blender's keymap while drawing
pipes. Custom bindings and Industry Compatible are supported.

- Alt+right mouse no longer cancels drawing or port picking.
- Orbit, pan and drag zoom keep 50% pipe-length feedback, then resume normal
  drawing speed after release, including when Alt is released before the mouse.
- Navigation also works while waiting for a start, choosing a bend and using
  Follow Tip. Unmodified right mouse still cancels the tool.

Install `pipeworks-0.5.1.zip` through Blender's **Install from Disk** to update
the existing `line_pipe` extension. Requires Blender 5.2+.

Validation: 126 installed-ZIP Alt navigation checks, 185 drawing checks,
83 existing navigation checks and 35 connection checks passed. The patched local
installation also passed 126 Alt navigation checks. ZIP contents, reproducibility
and Blender manifest validation are checked before publication.

---

## 简体中文

画管时，Alt+左/中/右键现已沿用 Blender 原有视角操作，支持自定义键位及
Industry Compatible。

- Alt+右键不再误取消绘制或管口拾取。
- 旋转、平移、拖动缩放保留 50% 管长反馈，松开后恢复正常续画；也支持先松开 Alt。
- 等待选起点、选择转弯、启用跟随管头时同样可导航；单独右键仍用于取消。

在 Blender「从磁盘安装」中选择 `pipeworks-0.5.1.zip`，更新既有 `line_pipe`
扩展。需要 Blender 5.2+。

验证通过：真实安装包 126 项 Alt 导航、185 项绘制、83 项既有导航及 35 项连接检查；
本机安装目录也通过 126 项 Alt 导航检查。发布前核对安装包内容、可复现构建及 Blender 清单。
