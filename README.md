# 奶蛙桌宠

一个使用 Python + Tkinter 制作的 Windows 桌宠。支持眼神跟随、Q 弹、蓄力回弹、拖拽物理、系统托盘、设置面板，以及捧腹大笑、比耶、趴趴走和翻肚皮动作。

当前版本：`v1.2.0`

## 下载使用

从 [GitHub Releases](https://github.com/fhfdhsj/Nai-Wa-desktop-pet/releases) 下载 `NaiWaDesktopPet.exe`，双击即可运行，无需安装 Python。

## 操作

| 操作 | 效果 |
| --- | --- |
| 移动鼠标 | 待机时瞳孔轻微跟随 |
| 单击奶蛙 | Q 弹一下并播放轻音效 |
| 长按后松开 | 蓄力，松开时弹得更高 |
| 按住拖动 | 拎起奶蛙；松手后有速度、重力和边缘反弹 |
| 2.5 秒内连点 8 次 | 播放完整捧腹大笑 |
| 右键奶蛙 | 选择互动动作、设置、托盘和退出 |
| 双击托盘图标 | 重新显示奶蛙 |
| `Esc` | 退出桌宠 |

右键菜单中的动作包括：

- 摸摸奶蛙
- 比个耶
- 翻肚皮
- 趴趴走
- 捧腹大笑 / 停止大笑
- 随机动作
- 休息 / 唤醒

大小、音效和对话气泡只在设置面板中调整，右键菜单不再重复显示这些选项。

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

## 系统托盘

启动后会常驻 Windows 系统托盘，可以：

- 显示或隐藏奶蛙
- 打开设置
- 退出程序

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

`.github/workflows/release.yml` 支持：

- 手动运行工作流并上传 EXE artifact
- 推送 `v*` 标签后自动创建 GitHub Release 并附带 EXE

```powershell
git tag -a v1.2.0 -m "NaiWa Desktop Pet v1.2.0"
git push origin v1.2.0
```

## 素材与生成

- `assets/`：透明姿态、眼部图层、应用图标和本地合成音效
- `assets/laugh/`：432 帧捧腹大笑动画与音轨
- `assets/crawl/`：7 帧趴趴走动画
- `new-picture/`：新增姿势和趴趴走动作的原始图片
- `prepare_assets.py`：从原始图片重建透明姿态、彩蛋姿势和趴趴走帧
- `prepare_effects.py`：生成眼部图层、音效和应用图标

完整重建：

```powershell
python prepare_assets.py
```

需要 Pillow 和 NumPy。