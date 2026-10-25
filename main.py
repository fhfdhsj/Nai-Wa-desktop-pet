from __future__ import annotations

import ctypes
import json
import math
import os
import queue
import random
import sys
import time
import tkinter as tk
from collections import OrderedDict, deque
from pathlib import Path
from tkinter import messagebox, ttk

try:
    from PIL import Image, ImageTk
except ImportError:
    fallback = tk.Tk()
    fallback.withdraw()
    messagebox.showerror(
        "缺少 Pillow",
        "奶蛙桌宠需要 Pillow。\n\n请在此目录打开终端并运行：\n"
        "python -m pip install -r requirements.txt",
    )
    fallback.destroy()
    raise SystemExit(1)

try:
    import winsound
except ImportError:
    winsound = None

try:
    import pystray
except ImportError:
    pystray = None



APP_VERSION = "1.1.0"


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


ROOT_DIR = resource_root()
ASSET_DIR = ROOT_DIR / "assets"
SFX_DIR = ASSET_DIR / "sfx"
APP_HOME = (Path(os.environ.get("LOCALAPPDATA", Path.home())) / "NaiWaDesktopPet") if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
SETTINGS_PATH = APP_HOME / "pet_settings.json"
EYE_GEOMETRY_PATH = ASSET_DIR / "eye_geometry.json"

KEY_COLOR = "#ff00ff"
WINDOW_WIDTH = 380
WINDOW_HEIGHT = 360
CENTER_X = WINDOW_WIDTH // 2
GROUND_Y = 346
LAUGH_FPS = 30.0
LAUGH_LIFT = 1.06
CHROMA_RGB = (255, 0, 255)
ALPHA_CUTOFF = 110
MUTEX_NAME = "Local\\NaiWaDesktopPet_Enhanced_v2"
SIZE_PRESETS = (("小", 0.72), ("中", 0.86), ("大", 1.0))
DEFAULT_SIZE = 2
ANIMATION_KEYS = ("quiet", "normal", "active")
ANIMATION_LABELS = ("安静", "普通", "活跃")
ANIMATION_DELAYS = {"quiet": (40000, 70000), "normal": (14000, 28000), "active": (7000, 14000)}
POSE_FILES = {
    "idle": "idle_eyes.png",
    "wave_left": "wave_left.png",
    "wave_right": "wave_right.png",
    "side": "side.png",
    "back": "back.png",
}

WAVE_LINES = (
    "奶蛙在这里！",
    "今天也要开心呀～",
    "呱！",
    "要不要休息一下？",
    "奶蛙向你挥挥手～",
)
SIDE_LINES = ("摸一会儿鱼…", "肚子有点饿了。", "在想晚饭吃什么。")
POKE_LINES = ("诶嘿，被摸到了！", "再摸一下～", "奶蛙喜欢贴贴。")
CLICK_LINES = ("呱？", "痒痒的～", "奶蛙在呢。")


def enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def get_work_area(root: tk.Tk) -> tuple[int, int, int, int]:
    """Return the primary monitor work area, excluding the taskbar."""
    if sys.platform == "win32":
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        rect = RECT()
        try:
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            pass
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


def load_settings() -> dict:
    defaults = {"size": DEFAULT_SIZE, "sound": True, "bubble": False, "topmost": True, "animation": "normal", "x": None, "y": None}
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return defaults
    if isinstance(data, dict):
        defaults.update(data)
    try:
        defaults["size"] = max(0, min(len(SIZE_PRESETS) - 1, int(defaults["size"])))
    except Exception:
        defaults["size"] = DEFAULT_SIZE
    defaults["sound"] = bool(defaults.get("sound", True))
    defaults["bubble"] = bool(defaults.get("bubble", False))
    defaults["topmost"] = bool(defaults.get("topmost", True))
    if defaults.get("animation") not in ANIMATION_DELAYS:
        defaults["animation"] = "normal"
    return defaults


def save_settings(settings: dict) -> None:
    APP_HOME.mkdir(parents=True, exist_ok=True)
    try:
        SETTINGS_PATH.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def acquire_single_instance():
    if sys.platform != "win32":
        return object()
    kernel32 = ctypes.windll.kernel32
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        return object()
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return None
    return handle


class NaiWaPet:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.settings = load_settings()
        self.root.title(f"奶蛙桌宠 v{APP_VERSION}")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", bool(self.settings.get("topmost", True)))
        self.root.configure(bg=KEY_COLOR)
        if sys.platform == "win32":
            self.root.wm_attributes("-transparentcolor", KEY_COLOR)
            self.root.attributes("-toolwindow", True)

        self.canvas = tk.Canvas(
            root,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            bg=KEY_COLOR,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.pack()

        self.size_index = int(self.settings.get("size", DEFAULT_SIZE))
        self.scale = SIZE_PRESETS[self.size_index][1]
        self.sound_enabled = tk.BooleanVar(master=root, value=bool(self.settings.get("sound", True)))
        self.bubble_enabled = tk.BooleanVar(master=root, value=bool(self.settings.get("bubble", False)))
        self.topmost_enabled = tk.BooleanVar(master=root, value=bool(self.settings.get("topmost", True)))
        self.animation_mode = tk.StringVar(master=root, value=str(self.settings.get("animation", "normal")))
        self.menu_open = False
        self.settings_window: tk.Toplevel | None = None
        self.tray_icon = None
        self.tray_queue: queue.Queue[str] = queue.Queue()
        self.hidden = False
        self.closed = False
        icon_path = ASSET_DIR / "app.ico"
        if sys.platform == "win32" and icon_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass

        self.base_images: dict[str, Image.Image] = {}
        self.alpha_masks: dict[str, tuple[bytes, int, int]] = {}
        self.static_photo_cache: dict[tuple[str, int], ImageTk.PhotoImage] = {}
        self.pupil_photo_cache: dict[int, ImageTk.PhotoImage] = {}
        self.dynamic_photo: ImageTk.PhotoImage | None = None
        self._static_key: tuple[str, int, int, int] | None = None
        self._load_assets()

        self.pose = "idle"
        self.sleeping = False
        self.excited = False
        self.excited_until = 0.0
        self.excited_next_pose = 0.0
        self.last_excited = -100.0
        self.anim_started = time.monotonic()
        self.last_render = 0.0
        self.sprite_y = float(GROUND_Y)
        self.current_size = self._base_size(self.pose, 1.0, 1.0)
        self.shadow_visible = False

        self.press_active = False
        self.press_time = 0.0
        self.press_origin = (0, 0)
        self.press_window = (0, 0)
        self.dragging = False
        self.drag_velocity = (0.0, 0.0)
        self.last_drag_time = 0.0
        self.last_drag_point = (0.0, 0.0)

        self.jelly_start: float | None = None
        self.jelly_strength = 0.0
        self.motion_active = False
        self.motion_velocity = (0.0, 0.0)
        self.motion_last_time = 0.0

        self.action_after: str | None = None
        self.pose_after: str | None = None
        self.bubble_after: str | None = None
        self.click_times: deque[float] = deque(maxlen=12)
        self.last_click_line = -100.0
        self.eye_positions = [(0.0, 0.0) for _ in self.eye_meta]
        self.eye_next = 0.0

        self.laughing = False
        self.laugh_index = -1
        self.laugh_start = 0.0
        self.laugh_photo: ImageTk.PhotoImage | None = None
        self.laugh_alpha: tuple[bytes, int, int] | None = None
        self.laugh_render_size = (1, 1)
        self.laugh_cache: OrderedDict[int, tuple[ImageTk.PhotoImage, bytes, int, int, tuple[int, int]]] = OrderedDict()

        self._build_scene()
        self._build_menu()
        self._bind_events()
        self._restore_position()
        self._refresh_visual(time.monotonic())
        self.root.after(900, self._schedule_random_action)
        self.root.after(16, self._animate)
        self._setup_tray()
        self.root.after(150, self._poll_tray)

    def _load_assets(self) -> None:
        missing = []
        for pose, filename in POSE_FILES.items():
            path = ASSET_DIR / filename
            if not path.exists() and pose == "idle":
                path = ASSET_DIR / "idle.png"
            if not path.exists():
                missing.append(filename)
                continue
            image = Image.open(path).convert("RGBA")
            self.base_images[pose] = image
            alpha = image.getchannel("A").point(lambda value: 255 if value >= ALPHA_CUTOFF else 0)
            self.alpha_masks[pose] = (alpha.tobytes(), image.width, image.height)
        if missing:
            raise FileNotFoundError("缺少素材：" + ", ".join(missing))

        self.pupil_base: Image.Image | None = None
        self.eye_meta: list[dict] = []
        self.eye_reference = (self.base_images["idle"].width, self.base_images["idle"].height)
        self.eye_max_offset = (2.2, 1.6)
        pupil_path = ASSET_DIR / "pupil.png"
        try:
            metadata = json.loads(EYE_GEOMETRY_PATH.read_text(encoding="utf-8"))
            self.eye_reference = tuple(metadata["referenceSize"])
            self.eye_meta = list(metadata.get("eyes", []))
            self.eye_max_offset = tuple(metadata.get("maxOffset", (2.2, 1.6)))
            if pupil_path.exists():
                self.pupil_base = Image.open(pupil_path).convert("RGBA")
        except Exception:
            self.eye_meta = []

        laugh_dir = ASSET_DIR / "laugh"
        self.laugh_frames = sorted(laugh_dir.glob("f*.webp")) if laugh_dir.exists() else []

    def _build_scene(self) -> None:
        self.shadow = self.canvas.create_oval(
            CENTER_X - 48,
            GROUND_Y - 11,
            CENTER_X + 48,
            GROUND_Y + 7,
            fill="#d3ad37",
            outline="",
            stipple="gray50",
            state="hidden",
        )
        self.sprite = self.canvas.create_image(
            CENTER_X,
            GROUND_Y,
            image=self._static_photo("idle"),
            anchor="s",
            tags=("pet",),
        )
        self.eye_items = []
        for _ in self.eye_meta:
            item = self.canvas.create_image(
                CENTER_X,
                GROUND_Y - 260,
                image=self._pupil_photo(),
                anchor="center",
                state="hidden",
            )
            self.eye_items.append(item)

        bubble_points = (
            107, 24, 239, 24, 250, 35, 250, 74, 239, 85,
            107, 85, 96, 74, 96, 35,
        )
        self.bubble_tail = self.canvas.create_polygon(
            169, 78, 188, 78, 177, 96,
            fill="#fff9e9", outline="", state="hidden",
        )
        self.bubble_bg = self.canvas.create_polygon(
            bubble_points,
            smooth=True,
            splinesteps=24,
            fill="#fff9e9",
            outline="#e8ad36",
            width=2,
            state="hidden",
        )
        self.bubble_text = self.canvas.create_text(
            CENTER_X,
            54,
            text="",
            width=140,
            fill="#5c4327",
            font=("Microsoft YaHei UI", 10, "bold"),
            justify="center",
            state="hidden",
        )
        self._raise_bubble()

    def _setup_tray(self) -> None:
        icon_path = ASSET_DIR / "app.ico"
        if pystray is None or not icon_path.exists():
            return
        try:
            image = Image.open(icon_path).convert("RGBA")
            menu = pystray.Menu(
                pystray.MenuItem("显示奶蛙", lambda *_: self._queue_tray("show"), default=True),
                pystray.MenuItem("隐藏奶蛙", lambda *_: self._queue_tray("hide")),
                pystray.MenuItem("设置", lambda *_: self._queue_tray("settings")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", lambda *_: self._queue_tray("quit")),
            )
            self.tray_icon = pystray.Icon("NaiWaDesktopPet", image, f"奶蛙桌宠 v{APP_VERSION}", menu)
            self.tray_icon.run_detached()
        except Exception:
            self.tray_icon = None

    def _queue_tray(self, action: str) -> None:
        self.tray_queue.put(action)

    def _poll_tray(self) -> None:
        if self.closed:
            return
        try:
            while True:
                action = self.tray_queue.get_nowait()
                if action == "show":
                    self.show_pet()
                elif action == "hide":
                    self.hide_to_tray()
                elif action == "settings":
                    self.show_pet()
                    self.open_settings_ui()
                elif action == "quit":
                    self.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(150, self._poll_tray)

    def show_pet(self) -> None:
        self.hidden = False
        self.root.deiconify()
        self.root.attributes("-topmost", bool(self.topmost_enabled.get()))
        self.root.lift()

    def hide_to_tray(self) -> None:
        if self.tray_icon is None:
            messagebox.showinfo("奶蛙桌宠", "系统托盘不可用，请直接最小化或退出。", parent=self.root)
            return
        self.hidden = True
        self.root.withdraw()
        try:
            self.tray_icon.notify("奶蛙还在托盘里，双击图标可以回来。", "奶蛙桌宠")
        except Exception:
            pass

    def open_settings_ui(self) -> None:
        if self.settings_window is not None:
            try:
                if self.settings_window.winfo_exists():
                    self.settings_window.deiconify()
                    self.settings_window.lift()
                    self.settings_window.focus_force()
                    return
            except tk.TclError:
                pass
            self.settings_window = None

        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title(f"奶蛙桌宠 v{APP_VERSION} - 设置")
        window.configure(bg="#f6efe2")
        window.resizable(False, False)
        window.attributes("-topmost", True)
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", self._close_settings_ui)
        icon_path = ASSET_DIR / "app.ico"
        if sys.platform == "win32" and icon_path.exists():
            try:
                window.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass

        style = ttk.Style(window)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 14, "bold"), foreground="#5c4327")
        style.configure("Hint.TLabel", foreground="#806b54")

        frame = ttk.Frame(window, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="奶蛙桌宠", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text=f"版本 {APP_VERSION}", style="Hint.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 16))

        size_var = tk.StringVar(value=SIZE_PRESETS[self.size_index][0])
        ttk.Label(frame, text="大小").grid(row=2, column=0, sticky="w", pady=7)
        ttk.Combobox(frame, textvariable=size_var, values=[item[0] for item in SIZE_PRESETS], state="readonly", width=18).grid(row=2, column=1, sticky="ew", padx=(18, 0), pady=7)

        current_animation = self.animation_mode.get()
        animation_label = ANIMATION_LABELS[ANIMATION_KEYS.index(current_animation)] if current_animation in ANIMATION_KEYS else "普通"
        animation_var = tk.StringVar(value=animation_label)
        ttk.Label(frame, text="随机动作频率").grid(row=3, column=0, sticky="w", pady=7)
        ttk.Combobox(frame, textvariable=animation_var, values=list(ANIMATION_LABELS), state="readonly", width=18).grid(row=3, column=1, sticky="ew", padx=(18, 0), pady=7)

        sound_var = tk.BooleanVar(value=self.sound_enabled.get())
        bubble_var = tk.BooleanVar(value=self.bubble_enabled.get())
        topmost_var = tk.BooleanVar(value=self.topmost_enabled.get())
        ttk.Checkbutton(frame, text="启用音效", variable=sound_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 4))
        ttk.Checkbutton(frame, text="显示对话气泡", variable=bubble_var).grid(row=5, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(frame, text="窗口始终置顶", variable=topmost_var).grid(row=6, column=0, columnspan=2, sticky="w", pady=4)

        buttons = ttk.Frame(frame)
        buttons.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        ttk.Button(buttons, text="回到右下角", command=self.reset_position).pack(side="left")
        ttk.Button(buttons, text="取消", command=self._close_settings_ui).pack(side="right")
        ttk.Button(buttons, text="保存", command=lambda: self._save_settings_ui(size_var, animation_var, sound_var, bubble_var, topmost_var)).pack(side="right", padx=(0, 8))

        window.update_idletasks()
        left, top, right, bottom = get_work_area(self.root)
        width, height = window.winfo_reqwidth(), window.winfo_reqheight()
        x = max(left, min(right - width, self.x + (WINDOW_WIDTH - width) // 2))
        y = max(top, min(bottom - height, self.y - height - 12))
        window.geometry(f"+{x}+{y}")
        window.focus_force()

    def _save_settings_ui(self, size_var, animation_var, sound_var, bubble_var, topmost_var) -> None:
        labels = [item[0] for item in SIZE_PRESETS]
        new_size = labels.index(size_var.get()) if size_var.get() in labels else self.size_index
        if new_size != self.size_index:
            self.set_size(new_size)
        self.sound_enabled.set(bool(sound_var.get()))
        self.bubble_enabled.set(bool(bubble_var.get()))
        self.topmost_enabled.set(bool(topmost_var.get()))
        self.root.attributes("-topmost", self.topmost_enabled.get())
        label = animation_var.get() if animation_var.get() in ANIMATION_LABELS else "普通"
        self.animation_mode.set(ANIMATION_KEYS[ANIMATION_LABELS.index(label)])
        if not self.bubble_enabled.get():
            self._cancel_bubble()
        self._save_settings()
        self._schedule_random_action()
        self._close_settings_ui()

    def _close_settings_ui(self) -> None:
        if self.settings_window is not None:
            try:
                self.settings_window.destroy()
            except tk.TclError:
                pass
            self.settings_window = None


    def _build_menu(self) -> None:
        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label="摸摸奶蛙", command=self.poke)
        self.menu.add_command(label="捧腹大笑", command=self.start_laugh)
        self.menu.add_command(label="停止大笑", command=self.stop_laugh)
        self.menu.add_command(label="换个姿势", command=self.random_action)
        self.menu.add_command(label="设置…", command=self.open_settings_ui)
        self.menu.add_command(label="隐藏到托盘", command=self.hide_to_tray)
        self.menu.add_separator()

        self.size_var = tk.IntVar(master=self.root, value=self.size_index)
        size_menu = tk.Menu(self.menu, tearoff=False)
        for index, (label, _) in enumerate(SIZE_PRESETS):
            size_menu.add_radiobutton(
                label=label,
                value=index,
                variable=self.size_var,
                command=lambda i=index: self.set_size(i),
            )
        self.menu.add_cascade(label="大小", menu=size_menu)
        self.menu.add_checkbutton(
            label="音效",
            variable=self.sound_enabled,
            command=self._toggle_sound,
        )
        self.menu.add_checkbutton(
            label="对话气泡",
            variable=self.bubble_enabled,
            command=self._toggle_bubble,
        )
        self.menu.add_separator()
        self.menu.add_command(label="休息一下", command=self.sleep)
        self.menu.add_command(label="唤醒奶蛙", command=self.wake)
        self.menu.add_command(label="回到右下角", command=self.reset_position)
        self.menu.add_separator()
        self.menu.add_command(label="使用说明", command=self.show_help)
        self.menu.add_command(label="退出桌宠", command=self.quit)

    def _bind_events(self) -> None:
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._show_menu)
        self.root.bind("<Escape>", lambda _event: self.quit())

    def _restore_position(self) -> None:
        left, top, right, bottom = get_work_area(self.root)
        default_x = right - WINDOW_WIDTH - 30
        default_y = bottom - WINDOW_HEIGHT - 8
        try:
            x = int(self.settings["x"]) if self.settings.get("x") is not None else default_x
            y = int(self.settings["y"]) if self.settings.get("y") is not None else default_y
        except Exception:
            x, y = default_x, default_y
        x = max(left, min(right - WINDOW_WIDTH, x))
        y = max(top, min(bottom - WINDOW_HEIGHT - 8, y))
        self.x, self.y = x, y
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")
    def _set_window_position(self, x: int, y: int) -> None:
        self.x, self.y = int(x), int(y)
        self.root.geometry(f"+{self.x}+{self.y}")

    def _base_size(self, pose: str, sx: float, sy: float) -> tuple[int, int]:
        image = self.base_images[pose]
        return (
            max(1, round(image.width * self.scale * sx)),
            max(1, round(image.height * self.scale * sy)),
        )

    def _photo_from_rgba(self, image: Image.Image) -> ImageTk.PhotoImage:
        """Flatten alpha onto the chroma key so Tk never blends edges into black."""
        mask = image.getchannel("A").point(lambda value: 255 if value >= ALPHA_CUTOFF else 0)
        flat = Image.new("RGB", image.size, CHROMA_RGB)
        flat.paste(image.convert("RGB"), (0, 0), mask)
        return ImageTk.PhotoImage(flat, master=self.root)

    def _static_photo(self, pose: str) -> ImageTk.PhotoImage:
        key = (pose, self.size_index)
        photo = self.static_photo_cache.get(key)
        if photo is None:
            image = self.base_images[pose]
            size = (
                max(1, round(image.width * self.scale)),
                max(1, round(image.height * self.scale)),
            )
            image = image.resize(size, Image.Resampling.LANCZOS)
            photo = self._photo_from_rgba(image)
            self.static_photo_cache[key] = photo
        return photo

    def _pupil_photo(self) -> ImageTk.PhotoImage | None:
        if self.pupil_base is None:
            return None
        photo = self.pupil_photo_cache.get(self.size_index)
        if photo is None:
            size = (
                max(1, round(self.pupil_base.width * self.scale)),
                max(1, round(self.pupil_base.height * self.scale)),
            )
            image = self.pupil_base.resize(size, Image.Resampling.LANCZOS)
            # The pupil sits on an opaque green eye. Keep its soft alpha so the
            # small overlay does not turn into a hard black square.
            photo = ImageTk.PhotoImage(image, master=self.root)
            self.pupil_photo_cache[self.size_index] = photo
        return photo

    def _say(self, message: str, duration_ms: int = 1900) -> None:
        if not self.bubble_enabled.get():
            self._cancel_bubble()
            self._hide_bubble()
            return
        self._cancel_bubble()
        self.canvas.itemconfigure(self.bubble_text, text=message, state="normal")
        self.canvas.itemconfigure(self.bubble_bg, state="normal")
        self.canvas.itemconfigure(self.bubble_tail, state="normal")
        self._raise_bubble()
        self.bubble_after = self.root.after(duration_ms, self._hide_bubble)

    def _hide_bubble(self) -> None:
        self.bubble_after = None
        for item in (self.bubble_text, self.bubble_bg, self.bubble_tail):
            self.canvas.itemconfigure(item, state="hidden")

    def _cancel_bubble(self) -> None:
        if self.bubble_after:
            self.root.after_cancel(self.bubble_after)
            self.bubble_after = None
        self._hide_bubble()

    def _raise_bubble(self) -> None:
        self.canvas.tag_raise(self.bubble_tail)
        self.canvas.tag_raise(self.bubble_bg)
        self.canvas.tag_raise(self.bubble_text)

    def _cancel_timers(self) -> None:
        for attr in ("action_after", "pose_after"):
            timer = getattr(self, attr)
            if timer:
                self.root.after_cancel(timer)
                setattr(self, attr, None)

    def _schedule_random_action(self, delay_ms: int | None = None) -> None:
        if self.sleeping or self.laughing or self.press_active or self.motion_active:
            return
        if self.action_after:
            self.root.after_cancel(self.action_after)
        if delay_ms is None:
            low, high = ANIMATION_DELAYS.get(self.animation_mode.get(), ANIMATION_DELAYS["normal"])
            delay_ms = random.randint(low, high)
        self.action_after = self.root.after(delay_ms, self.random_action)

    def _set_pose(self, pose: str) -> None:
        self.pose = pose
        self._static_key = None
        if pose != "idle" and not self.excited:
            for item in self.eye_items:
                self.canvas.itemconfigure(item, state="hidden")

    def random_action(self) -> None:
        if self.sleeping:
            self.wake()
            return
        if self.laughing or self.press_active or self.dragging or self.motion_active:
            self.action_after = self.root.after(4500, self.random_action)
            return
        self._cancel_timers()
        self._set_pose(random.choice(("wave_left", "wave_right", "side")))
        if self.pose == "side":
            if random.random() < 0.7:
                self._say(random.choice(SIDE_LINES))
        else:
            if random.random() < 0.65:
                self._say(random.choice(WAVE_LINES))
            self._show_shadow()
        self.pose_after = self.root.after(random.randint(1700, 2400), self._return_to_idle)

    def _return_to_idle(self) -> None:
        self.pose_after = None
        if self.sleeping or self.laughing:
            return
        self._set_pose("idle")
        self._hide_shadow()
        self._schedule_random_action()

    def poke(self) -> None:
        if self.sleeping:
            self.wake()
            return
        self._cancel_timers()
        self._cancel_bubble()
        self._set_pose(random.choice(("wave_left", "wave_right")))
        self._say(random.choice(POKE_LINES), 1700)
        self._show_shadow()
        self._play_sound("pop")
        self._trigger_jelly(0.10)
        self.pose_after = self.root.after(1700, self._return_to_idle)

    def start_laugh(self) -> None:
        if not self.laugh_frames:
            self._say("没有找到大笑素材。", 1400)
            return
        self._stop_motion()
        self._cancel_timers()
        self._cancel_bubble()
        self.sleeping = False
        self.excited = False
        self.laughing = True
        self.laugh_start = time.monotonic()
        self.laugh_index = -1
        self.pose = "laugh"
        self._static_key = None
        for item in self.eye_items:
            self.canvas.itemconfigure(item, state="hidden")
        self._show_shadow()
        self._show_laugh_frame(0)
        self._play_laugh_audio()

    def stop_laugh(self) -> None:
        if not self.laughing:
            return
        self.laughing = False
        self._stop_laugh_audio()
        self._set_pose("idle")
        self._hide_shadow()
        self._schedule_random_action()

    def _laugh_frame(self, index: int):
        index = max(0, min(len(self.laugh_frames) - 1, int(index)))
        cached = self.laugh_cache.get(index)
        if cached is not None:
            self.laugh_cache.move_to_end(index)
            return cached
        with Image.open(self.laugh_frames[index]) as source:
            base = source.convert("RGBA")
        render_scale = self.scale * LAUGH_LIFT
        size = (
            max(1, round(base.width * render_scale)),
            max(1, round(base.height * render_scale)),
        )
        resized = base.resize(size, Image.Resampling.BILINEAR)
        photo = self._photo_from_rgba(resized)
        alpha = base.getchannel("A").point(lambda value: 255 if value >= ALPHA_CUTOFF else 0)
        entry = (photo, alpha.tobytes(), base.width, base.height, size)
        self.laugh_cache[index] = entry
        if len(self.laugh_cache) > 36:
            self.laugh_cache.popitem(last=False)
        return entry

    def _show_laugh_frame(self, index: int) -> None:
        photo, alpha, base_w, base_h, size = self._laugh_frame(index)
        self.laugh_photo = photo
        self.laugh_alpha = (alpha, base_w, base_h)
        self.laugh_index = index
        self.laugh_render_size = size
        self.current_size = size
        self.sprite_y = float(GROUND_Y)
        self.canvas.itemconfigure(self.sprite, image=photo)
        self.canvas.coords(self.sprite, CENTER_X, self.sprite_y)
        for item in self.eye_items:
            self.canvas.itemconfigure(item, state="hidden")
        if self.shadow_visible:
            width = max(48, round(size[0] * 0.38))
            self.canvas.coords(self.shadow, CENTER_X - width / 2, GROUND_Y - 10, CENTER_X + width / 2, GROUND_Y + 7)
            self.canvas.itemconfigure(self.shadow, state="normal")
            self.canvas.tag_lower(self.shadow)

    def _play_laugh_audio(self) -> None:
        if not self.sound_enabled.get() or winsound is None:
            return
        path = ASSET_DIR / "laugh.wav"
        if not path.exists():
            return
        try:
            winsound.PlaySound(
                str(path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
        except Exception:
            pass

    def _stop_laugh_audio(self) -> None:
        if winsound is None:
            return
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    def sleep(self) -> None:
        self._cancel_timers()
        self._cancel_bubble()
        if self.laughing:
            self.laughing = False
            self._stop_laugh_audio()
        self.excited = False
        self.sleeping = True
        self._set_pose("back")
        self._show_shadow()
        self._say("Zzz… 奶蛙睡了。", 2300)

    def wake(self) -> None:
        if not self.sleeping:
            self.poke()
            return
        self.sleeping = False
        self._cancel_timers()
        self._set_pose("idle")
        self._hide_shadow()
        self._say("奶蛙醒啦～", 1500)
        self._play_sound("pop")
        self._schedule_random_action(7000)

    def set_size(self, index: int) -> None:
        index = max(0, min(len(SIZE_PRESETS) - 1, int(index)))
        if index == self.size_index:
            return
        self.size_index = index
        self.scale = SIZE_PRESETS[index][1]
        self.size_var.set(index)
        self._static_key = None
        self.pupil_photo_cache.clear()
        self.laugh_cache.clear()
        if self.laughing and self.laugh_index >= 0:
            self._show_laugh_frame(self.laugh_index)
        self._save_settings()
        self._say(f"变成{SIZE_PRESETS[index][0]}号啦～", 1200)
        self._play_sound("pop")

    def reset_position(self) -> None:
        left, top, right, bottom = get_work_area(self.root)
        self._set_window_position(right - WINDOW_WIDTH - 30, bottom - WINDOW_HEIGHT - 8)
        self._save_settings()
        self._say("回到右下角啦～", 1200)

    def show_help(self) -> None:
        messagebox.showinfo(
            "奶蛙桌宠",
            "眼神会跟着鼠标移动。\n\n"
            "单击：Q 弹一下\n"
            "长按后松开：蓄力回弹\n"
            "按住拖动：扔到桌面上，会受重力落下\n"
            "短时间连点 8 次：播放完整捧腹大笑\n\n"
            "右键可以捧腹大笑、停止大笑、换姿势、调大小、开关音效和对话气泡、休息或退出。",
            parent=self.root,
        )

    def _toggle_sound(self) -> None:
        self._save_settings()
        if self.sound_enabled.get():
            self._play_sound("pop")
        else:
            self._stop_laugh_audio()

    def _toggle_bubble(self) -> None:
        self._save_settings()
        if self.bubble_enabled.get():
            self._say("对话气泡打开啦～", 1200)
        else:
            self._cancel_bubble()
            self._hide_bubble()

    def _play_sound(self, name: str) -> None:
        if self.laughing or not self.sound_enabled.get() or winsound is None:
            return
        path = SFX_DIR / f"{name}.wav"
        if not path.exists():
            return
        try:
            winsound.PlaySound(
                str(path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
        except Exception:
            pass

    def _trigger_jelly(self, strength: float) -> None:
        self.jelly_start = time.monotonic()
        self.jelly_strength = max(0.04, min(0.24, strength))

    def _squash(self, now: float) -> tuple[float, float]:
        if self.press_active and not self.dragging:
            charge = max(0.0, min(1.0, (now - self.press_time - 0.12) / 1.1))
            sy = 1.0 - 0.075 * charge
            return 1.0 / math.sqrt(sy), sy
        if self.dragging:
            return 1.0 / math.sqrt(1.04), 1.04
        if self.jelly_start is not None:
            elapsed = now - self.jelly_start
            if elapsed >= 0.78:
                self.jelly_start = None
            else:
                sy = 1.0 - self.jelly_strength * math.exp(-7.2 * elapsed) * math.cos(23.0 * elapsed)
                sy = max(0.76, min(1.18, sy))
                return 1.0 / math.sqrt(sy), sy
        return 1.0, 1.0

    def _refresh_visual(self, now: float) -> None:
        if self.laughing:
            self.sprite_y = float(GROUND_Y)
            self.current_size = self.laugh_render_size
            self.canvas.coords(self.sprite, CENTER_X, self.sprite_y)
            for item in self.eye_items:
                self.canvas.itemconfigure(item, state="hidden")
            if self.shadow_visible:
                width = max(48, round(self.laugh_render_size[0] * 0.38))
                self.canvas.coords(self.shadow, CENTER_X - width / 2, GROUND_Y - 10, CENTER_X + width / 2, GROUND_Y + 7)
                self.canvas.itemconfigure(self.shadow, state="normal")
                self.canvas.tag_lower(self.shadow)
            return

        sx, sy = self._squash(now)
        target_size = self._base_size(self.pose, sx, sy)
        dynamic = abs(sx - 1.0) > 0.002 or abs(sy - 1.0) > 0.002
        if dynamic:
            image = self.base_images[self.pose].resize(target_size, Image.Resampling.BILINEAR)
            self.dynamic_photo = self._photo_from_rgba(image)
            self.canvas.itemconfigure(self.sprite, image=self.dynamic_photo)
            self._static_key = None
        else:
            key = (self.pose, self.size_index, target_size[0], target_size[1])
            if self._static_key != key:
                self.canvas.itemconfigure(self.sprite, image=self._static_photo(self.pose))
                self._static_key = key
            self.dynamic_photo = None

        self.current_size = target_size
        if self.sleeping or self.dragging or self.motion_active:
            bob = 0.0
        elif self.pose == "idle":
            phase = now - self.anim_started
            bob = 1.3 + math.sin(phase * 2.2) * 1.3
        else:
            phase = now - self.anim_started
            bob = -abs(math.sin(phase * 6.0)) * 2.0
        self.sprite_y = GROUND_Y + bob
        self.canvas.coords(self.sprite, CENTER_X, self.sprite_y)

        if self.shadow_visible:
            width = max(48, round(target_size[0] * 0.38))
            self.canvas.coords(self.shadow, CENTER_X - width / 2, GROUND_Y - 10, CENTER_X + width / 2, GROUND_Y + 7)
            self.canvas.itemconfigure(self.shadow, state="normal")
            self.canvas.tag_lower(self.shadow)

        self._update_eyes(now, target_size)
    def _update_eyes(self, now: float, target_size: tuple[int, int]) -> None:
        visible = (
            bool(self.eye_meta)
            and self.pupil_base is not None
            and self.pose == "idle"
            and not self.sleeping
            and not self.dragging
        )
        if not visible:
            for item in self.eye_items:
                self.canvas.itemconfigure(item, state="hidden")
            return

        width, height = target_size
        reference_w, reference_h = self.eye_reference
        sprite_left = CENTER_X - width / 2
        sprite_top = self.sprite_y - height
        if now >= self.eye_next:
            try:
                pointer_x, pointer_y = self.root.winfo_pointerxy()
            except tk.TclError:
                pointer_x, pointer_y = -1, -1
            if pointer_x != -1 and pointer_y != -1:
                self.eye_next = now + 1 / 30
                for index, eye in enumerate(self.eye_meta):
                    center_x, center_y = eye["center"]
                    eye_x = self.x + sprite_left + center_x / reference_w * width
                    eye_y = self.y + sprite_top + center_y / reference_h * height
                    dx = pointer_x - eye_x
                    dy = pointer_y - eye_y
                    distance = math.hypot(dx, dy)
                    factor = math.tanh(distance / 85.0) / distance if distance > 1e-6 else 0.0
                    target_x = dx * factor * self.eye_max_offset[0]
                    target_y = dy * factor * self.eye_max_offset[1]
                    old_x, old_y = self.eye_positions[index]
                    blend = 0.32
                    self.eye_positions[index] = (
                        old_x + (target_x - old_x) * blend,
                        old_y + (target_y - old_y) * blend,
                    )

        for index, eye in enumerate(self.eye_meta):
            center_x, center_y = eye["center"]
            eye_x = sprite_left + center_x / reference_w * width
            eye_y = sprite_top + center_y / reference_h * height
            offset_x, offset_y = self.eye_positions[index]
            self.canvas.coords(
                self.eye_items[index],
                eye_x + offset_x * self.scale,
                eye_y + offset_y * self.scale,
            )
            self.canvas.itemconfigure(self.eye_items[index], image=self._pupil_photo(), state="normal")

    def _show_shadow(self) -> None:
        self.shadow_visible = True
        self.canvas.itemconfigure(self.shadow, state="normal")
        self.canvas.tag_lower(self.shadow)

    def _hide_shadow(self) -> None:
        self.shadow_visible = False
        self.canvas.itemconfigure(self.shadow, state="hidden")

    def _is_on_pet(self, x: float, y: float) -> bool:
        width, height = self.current_size
        left = CENTER_X - width / 2
        top = self.sprite_y - height
        if not (left <= x < left + width and top <= y < top + height):
            return False
        if self.pose == "laugh" and self.laugh_alpha is not None:
            alpha, base_w, base_h = self.laugh_alpha
        else:
            alpha, base_w, base_h = self.alpha_masks[self.pose]
        bx = int((x - left) / width * base_w)
        by = int((y - top) / height * base_h)
        bx = max(0, min(base_w - 1, bx))
        by = max(0, min(base_h - 1, by))
        return alpha[by * base_w + bx] != 0

    def _on_press(self, event: tk.Event) -> None:
        if self.laughing:
            return
        if self.menu_open or not self._is_on_pet(event.x, event.y):
            self.press_active = False
            return
        self.root.focus_force()
        if self.sleeping:
            self.wake()
            self.press_active = False
            return
        self._stop_motion()
        self._cancel_timers()
        self._cancel_bubble()
        self._set_pose("idle")
        self.press_active = True
        self.press_time = time.monotonic()
        self.press_origin = (event.x_root, event.y_root)
        self.press_window = (self.x, self.y)
        self.dragging = False
        self.drag_velocity = (0.0, 0.0)
        self.last_drag_time = self.press_time
        self.last_drag_point = (float(event.x_root), float(event.y_root))

    def _on_drag(self, event: tk.Event) -> None:
        if not self.press_active:
            return
        dx = event.x_root - self.press_origin[0]
        dy = event.y_root - self.press_origin[1]
        if not self.dragging and math.hypot(dx, dy) > 4:
            self.dragging = True
        if not self.dragging:
            return
        left, top, right, bottom = get_work_area(self.root)
        x = max(left, min(right - WINDOW_WIDTH, self.press_window[0] + dx))
        y = max(top, min(bottom - WINDOW_HEIGHT - 8, self.press_window[1] + dy))
        now = time.monotonic()
        dt = max(1e-4, now - self.last_drag_time)
        vx = (x - self.last_drag_point[0]) / dt
        vy = (y - self.last_drag_point[1]) / dt
        self.drag_velocity = (
            self.drag_velocity[0] * 0.65 + vx * 0.35,
            self.drag_velocity[1] * 0.65 + vy * 0.35,
        )
        self.last_drag_time = now
        self.last_drag_point = (float(x), float(y))
        self._set_window_position(x, y)

    def _on_release(self, _event: tk.Event) -> None:
        if not self.press_active:
            return
        now = time.monotonic()
        was_dragging = self.dragging
        self.press_active = False
        self.dragging = False
        if was_dragging:
            vx, vy = self.drag_velocity
            if math.hypot(vx, vy) < 35:
                vx = vy = 0.0
            self.motion_velocity = (
                max(-900.0, min(900.0, vx)),
                max(-900.0, min(900.0, vy)),
            )
            self.motion_active = True
            self.motion_last_time = now
            self._save_settings()
            return

        duration = now - self.press_time
        charge = max(0.0, min(1.0, (duration - 0.18) / 1.1))
        self._trigger_jelly(0.065 + 0.19 * charge)
        self._play_sound("boing" if charge > 0.72 else "pop")
        if charge > 0.72:
            self._say("蓄力满啦！", 1100)
        self._register_click(now)

    def _register_click(self, now: float) -> None:
        self.click_times.append(now)
        while self.click_times and now - self.click_times[0] > 2.5:
            self.click_times.popleft()
        if len(self.click_times) >= 8:
            self.click_times.clear()
            self.start_laugh()
            return
        if now - self.last_click_line > 1.4 and random.random() < 0.35:
            self.last_click_line = now
            self._say(random.choice(CLICK_LINES), 1000)
        self._schedule_random_action(7000)

    def _stop_motion(self) -> None:
        self.motion_active = False
        self.motion_velocity = (0.0, 0.0)

    def _update_motion(self, now: float) -> None:
        if not self.motion_active:
            return
        dt = max(0.001, min(0.05, now - self.motion_last_time))
        self.motion_last_time = now
        vx, vy = self.motion_velocity
        vy += 1250.0 * dt
        left, top, right, bottom = get_work_area(self.root)
        x = self.x + vx * dt
        y = self.y + vy * dt
        max_x = right - WINDOW_WIDTH
        max_y = bottom - WINDOW_HEIGHT - 8
        if x < left:
            x = left
            vx = abs(vx) * 0.38
        elif x > max_x:
            x = max_x
            vx = -abs(vx) * 0.38
        if y < top:
            y = top
            vy = abs(vy) * 0.42
        elif y > max_y:
            y = max_y
            if abs(vy) > 70:
                vy = -abs(vy) * 0.46
            else:
                vy = 0.0
            vx *= 0.72
        vx *= math.exp(-1.8 * dt)
        if y >= max_y - 0.5:
            vx *= math.exp(-7.0 * dt)
        self.motion_velocity = (vx, vy)
        self._set_window_position(round(x), round(y))
        if y >= max_y - 0.5 and abs(vx) < 16 and abs(vy) < 20:
            self._stop_motion()
            self._save_settings()

    def _animate(self) -> None:
        now = time.monotonic()
        self._update_motion(now)
        if self.laughing:
            elapsed = now - self.laugh_start
            index = min(len(self.laugh_frames) - 1, int(elapsed * LAUGH_FPS))
            if index != self.laugh_index:
                self._show_laugh_frame(index)
            if elapsed >= len(self.laugh_frames) / LAUGH_FPS:
                self.stop_laugh()

        if now - self.last_render >= 1 / 30:
            self.last_render = now
            self._refresh_visual(now)
        self.root.after(16, self._animate)

    def _show_menu(self, event: tk.Event) -> None:
        if not self._is_on_pet(event.x, event.y):
            return
        self.menu_open = True
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu_open = False
            try:
                self.menu.grab_release()
            except tk.TclError:
                pass

    def _save_settings(self) -> None:
        save_settings(
            {
                "size": self.size_index,
                "sound": bool(self.sound_enabled.get()),
                "bubble": bool(self.bubble_enabled.get()),
                "topmost": bool(self.topmost_enabled.get()),
                "animation": self.animation_mode.get(),
                "x": self.x,
                "y": self.y,
            }
        )

    def quit(self) -> None:
        if self.closed:
            return
        self.closed = True
        self._close_settings_ui()
        if self.laughing:
            self._stop_laugh_audio()
        self._save_settings()
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self.root.destroy()


def main() -> None:
    enable_dpi_awareness()
    guard = None
    if "--self-test" not in sys.argv:
        guard = acquire_single_instance()
        if guard is None:
            fallback = tk.Tk()
            fallback.withdraw()
            messagebox.showinfo("奶蛙桌宠", "奶蛙已经在桌面上啦～")
            fallback.destroy()
            return

    root = None
    try:
        root = tk.Tk()
        app = NaiWaPet(root)
        if "--self-test" in sys.argv:
            root.after(1100, app.quit)
        root.mainloop()
    except Exception as error:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
        error_root = tk.Tk()
        error_root.withdraw()
        messagebox.showerror("奶蛙启动失败", f"{error}\n\n请运行 prepare_assets.py 和 prepare_effects.py 重新生成素材。")
        error_root.destroy()
        raise


if __name__ == "__main__":
    main()
