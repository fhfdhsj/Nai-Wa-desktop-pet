# 奶蛙桌宠

一个使用 Python + Tkinter 制作的 Windows 桌宠。支持眼神跟随、Q 弹、蓄力回弹、拖拽物理、432 帧捧腹大笑、系统托盘和设置面板。

当前版本：`v1.1.0`

## 下载使用

从 [GitHub Releases](https://github.com/fhfdhsj/Nai-Wa-desktop-pet/releases) 下载 `NaiWaDesktopPet.exe`，双击即可运行，无需安装 Python。

第一次启动时如果 Windows 提示安全确认，请确认文件来自本项目 Release。

## 操作

| 操作 | 效果 |
| --- | --- |
| 移动鼠标 | 待机时瞳孔轻微跟随 |
| 单击奶蛙 | Q 弹一下并播放轻音效 |
| 长按后松开 | 蓄力，松开时弹得更高 |
| 按住拖动 | 拎起奶蛙；松手后有速度、重力和边缘反弹 |
| 2.5 秒内连点 8 次 | 播放完整捧腹大笑 |
| 右键奶蛙 | 大笑、停止、姿势、设置、隐藏、休息、退出 |
| 双击托盘图标 | 重新显示奶蛙 |
| `Esc` | 退出桌宠 |

## 系统托盘

启动后会常驻 Windows 系统托盘，右键托盘图标可以：

- 显示或隐藏奶蛙
- 打开设置
- 退出程序

## 设置面板

右键奶蛙，选择“设置…”：

- 小 / 中 / 大三档大小
- 安静 / 普通 / 活跃三档随机动作频率
- 音效开关
- 对话气泡开关
- 窗口始终置顶
- 回到右下角

设置会自动保存。打包版设置保存在：

`%LOCALAPPDATA%\NaiWaDesktopPet\pet_settings.json`

## 源码运行

需要 Windows 和 Python 3.10～3.13：

```powershell
python -m pip install -r requirements.txt
python main.py
```

也可以双击 `启动奶蛙.bat`。启动脚本会在缺少依赖时自动安装。

## 构建 EXE

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe tools\build_release.py
```

构建结果：`dist\NaiWaDesktopPet.exe`

## GitHub 自动发布

仓库包含 `.github/workflows/release.yml`：

- 手动运行工作流会构建并上传 EXE artifact
- 推送 `v*` 标签会自动创建 GitHub Release 并附带 EXE

例如：

```powershell
git tag -a v1.1.0 -m "NaiWa Desktop Pet v1.1.0"
git push origin v1.1.0
```

## 素材与生成

- `assets/`：透明姿态、眼部图层、应用图标和本地合成音效
- `assets/laugh/`：432 帧捧腹大笑动画
- `assets/laugh.wav`：大笑音轨
- `prepare_assets.py`：从原始 JPG 重建透明姿态
- `prepare_effects.py`：生成眼部图层、音效和应用图标

如果需要从原始图片完整重建：

```powershell
python prepare_assets.py
```

需要 Pillow 和 NumPy。素材来源说明见 `ASSET_SOURCES.md`。