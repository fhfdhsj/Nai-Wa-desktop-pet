# 奶蛙桌宠

一个使用 Python + Tkinter 制作的轻量 Windows 桌宠。基础姿态来自目录中的四张奶蛙原图，捧腹大笑使用 432 帧动画和独立笑声音轨。

## 启动

双击 `启动奶蛙.bat`。

环境要求：

- Windows 10/11
- Python 3.10 或更高版本
- Pillow（`python -m pip install -r requirements.txt`）

## 操作

| 操作 | 效果 |
| --- | --- |
| 移动鼠标 | 待机时瞳孔轻微跟随 |
| 单击奶蛙 | Q 弹一下并播放轻音效 |
| 长按后松开 | 蓄力，松开时弹得更高 |
| 按住拖动 | 拎起奶蛙；松手后有速度、重力和边缘反弹 |
| 2.5 秒内连点 8 次 | 播放约 14.4 秒的完整捧腹大笑 |
| 右键奶蛙 | 捧腹大笑、停止大笑、换姿势、大小、音效、对话气泡、休息、退出 |
| `Esc` | 退出桌宠 |

对话气泡默认关闭，需要时可在右键菜单里打开。奶蛙会记住上次的大小、音效、气泡开关和桌面位置。再次启动 `启动奶蛙.bat` 时，如果程序已经在运行，不会重复启动。

## 文件说明

- `main.py`：桌宠主程序
- `assets/`：透明姿态素材、眼部图层、本地合成音效
- `assets/laugh/`：432 帧捧腹大笑动画
- `assets/laugh.wav`：捧腹大笑音轨
- `prepare_assets.py`：从原始 JPG 重新生成透明姿态素材
- `prepare_effects.py`：从待机图生成眼神图层和音效
- `_preview.png`：透明姿态检查图
- `_eye_preview.png`：眼部合成检查图
- `ASSET_SOURCES.md`：大笑素材来源与授权说明

如果修改了原始图片，可运行：

```powershell
python prepare_assets.py
```

重新生成素材需要 Pillow 和 NumPy。
