# PipeWorks Project Preferences

- Scope this repository to interactive pipe drawing and the explicitly requested
  manual endpoint docking, fixed-end bridging, legacy Pipe Assembly port support,
  mesh repair, orthogonal-group curvature matching, authored ports, hollow profiles,
  the local fitting library, authored edge-count variants, copyable AI fitting
  specifications, and library fitting continuation during drawing. Automated network routing and online publication
  require a separate user request.
- The first selected port or group is the reference. The second port or active
  Shift-selected group matches it. Check each group in its own orthogonal frame.
- Keep the internal `line_pipe` extension ID, operators, and saved data keys
  compatible; the public product name and sidebar category are PipeWorks.
- Default the UI to English with one button for a complete Simplified Chinese
  switch, including options, tooltips, errors, and modal feedback.
- Public documentation uses a complete English section first, followed by a
  complete Simplified Chinese section.
- Default public previews and saved example views to non-isometric perspective
  (`PERSP`), near eye level with a modest horizontal turn.
- Public viewport screenshots are landscape, at least 16:9. Keep embedded images
  and image attachments only on the latest release page; preserve historical
  tags, source, and installer downloads.
- Generate installers reproducibly from this source into ignored `dist/` and
  publish them through GitHub Releases, not as committed ZIP files.
- Create all isolated Blender configuration directories before launch; assert
  the actual `bpy.utils.user_resource('CONFIG')` path before saving preferences.
- Keep local profiles, logs, recovery scenes, and publishing receipts ignored.

## 简体中文

- 范围包含交互式画管及已明确要求的管口吸附、固定两端桥接、旧 Pipe Assembly 管口兼容、
  网格修复、正交组曲率、管口标记、空管、本地管件库和绘制时接续库件。自动管网及在线发布需另行要求。
- 第一口或第一组为基准，第二口或 Shift 选中的活动组向其对齐。各组按自身的正交方向验证。
- 保留 `line_pipe` 扩展 ID、操作符及已存数据键；对外名称和侧栏统一 PipeWorks。
- 界面默认英文，用一个按钮切换完整简体中文，覆盖选项、提示、错误及操作反馈。
- 公开文档先完整英文，再完整简体中文。
- 默认公开预览及示例使用非等距透视，优先平视并适度水平侧转。
- 公开视口截图至少 16:9，仅最新版发布页保留图片嵌入和图片附件。
- 安装包由源码可复现生成，放在 Releases；历史标签、源码及下载保留。
- 启动隔离 Blender 前创建所有配置目录，保存偏好前校验实际配置路径。
- 本地配置、日志、恢复文件和发布记录不入 Git。
