# PipeWorks Project Preferences

- Scope this repository to interactive solid pipe drawing. Automatic connection,
  fittings, assembly, and network tools require a separate user request.
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

- 本仓库仅实现交互式实心画管。自动连接、管件库、组装及管网需另行明确授权。
- 保留 `line_pipe` 扩展 ID、操作符及已存数据键；对外名称和侧栏统一 PipeWorks。
- 界面默认英文，用一个按钮切换完整简体中文，覆盖选项、提示、错误及操作反馈。
- 公开文档先完整英文，再完整简体中文。
- 默认公开预览及示例使用非等距透视，优先平视并适度水平侧转。
- 公开视口截图至少 16:9，仅最新版发布页保留图片嵌入和图片附件。
- 安装包由源码可复现生成，放在 Releases；历史标签、源码及下载保留。
- 启动隔离 Blender 前创建所有配置目录，保存偏好前校验实际配置路径。
- 本地配置、日志、恢复文件和发布记录不入 Git。
