# Development

Python 3.11+ is sufficient for packaging; Blender supplies its own Python for
integration. Runtime requires Blender 5.2+. No pip packages are needed.

```sh
python tools/quick_check.py
python tools/build.py --blender /path/to/blender
python tests/run_checks.py --blender /path/to/blender
```

On Windows, pass the full path to `blender.exe` as a quoted argument. The build
produces `dist/pipeworks-0.1.1.zip` and `dist/SHA256SUMS.txt`. ZIP timestamps,
permissions, order, and compression are fixed; repeated builds compare byte for
byte. The portable CI checks syntax, manifest/product metadata, standalone scope,
source/archive parity, and reproducibility. CI does not launch a Blender GUI.

The integration runner uses local ignored profiles under `verification/line-pipe/`.
It creates CONFIG, SCRIPTS, and EXTENSIONS before launching, validates the actual
config path in the install test, installs the real archive, and starts a second
process to check saved language preferences. It does not edit the user's regular
Blender settings.

For a native event-queue regression test, launch `tests/gui_line_pipe.py` with
Blender's `--enable-event-simulate` and pass `-- --six-axis`. First create the
three profile folders under `verification/line-pipe/six-axis-ui/` and point
`BLENDER_USER_CONFIG`, `BLENDER_USER_SCRIPTS`, and `BLENDER_USER_EXTENSIONS` to them.
That test starts with a self-authored disposable scene. Its orthographic diagnostic
images are not public presentation images. Use `tools/capture_preview.py` for the
wide perspective release visuals.

Generate an example in an isolated factory-startup process with
`--python tools/build_example.py`. It writes `examples/pipeworks-example.blend`.
Examples, verification output, profiles, installers, and publishing receipts are
ignored. Only this repository's nine-file `line_pipe/` extension is packaged.

## Release Procedure

1. Check the current source and supported Blender version.
2. Run package, integration, actual-install, and needed interactive checks.
3. Build and inspect wide non-isometric perspective images from self-authored geometry.
4. Commit the deliberate public file list; confirm no local profiles or other pipe code.
5. Push `main` and the version tag; check both CI runs.
6. Publish the ZIP, SHA256 file, and latest-release screenshots; verify public downloads.
7. Update local publishing receipts and catalog. Retire images from older release
   pages while preserving source tags and installer downloads.

---

## 简体中文

打包需要 Python 3.11+；集成检查使用 Blender 自带 Python。运行需要 Blender 5.2+，
无需 pip 依赖。上方三个命令依次运行便携检查、可选 Blender 清单验证及完整集成。
Windows 中以引号包裹 `blender.exe` 的完整路径。

构建输出 `dist/pipeworks-0.1.1.zip` 和 `SHA256SUMS.txt`。ZIP 的时间戳、权限、
文件顺序和压缩固定，重复构建逐字节相同。CI 检查语法、产品元数据、独立范围、
源码/包一致性和可复现性，不运行 Blender 图形界面。

集成运行器使用 Git 忽略的隔离配置，先创建 CONFIG/SCRIPTS/EXTENSIONS，安装
检查确认实际配置路径后才保存偏好；真实安装 ZIP 后另启进程检查语言记忆。
不会修改用户常用 Blender 配置。

原生事件队列测试使用 `--enable-event-simulate --python tests/gui_line_pipe.py
-- --six-axis`，运行前创建并通过环境变量指定 `verification/line-pipe/six-axis-ui/`
下三类配置目录。测试使用自建临时场景，正交诊断图不用于公开展示；公开宽幅透视
图使用 `tools/capture_preview.py`。

隔离启动并执行 `tools/build_example.py` 可生成自建示例。示例、验证输出、配置、
安装包及发布凭据均不入 Git；安装包仅含 `line_pipe/` 下九个扩展文件。

发布前验证源码、安装包和交互，检查宽幅非等距透视图，核对公开文件清单后提交。
推送 main 和版本标签，确认两次 CI 成功，再发布安装包、SHA256 与最新版本截图，
核对匿名下载并更新本地记录。新版本上线后撤下旧发布页图片，保留历史源码与安装包。
