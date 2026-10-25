from __future__ import annotations

import json
import math
import struct
import wave
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"
SFX_DIR = ASSET_DIR / "sfx"


def _component_boxes(mask: np.ndarray, min_area: int = 20) -> list[tuple[int, int, int, int, int]]:
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    boxes = []
    for start_y, start_x in zip(*np.nonzero(mask)):
        if seen[start_y, start_x]:
            continue
        queue = deque([(start_y, start_x)])
        seen[start_y, start_x] = True
        points = []
        while queue:
            y, x = queue.popleft()
            points.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        if len(points) >= min_area:
            ys = [point[0] for point in points]
            xs = [point[1] for point in points]
            boxes.append((len(points), min(xs), min(ys), max(xs), max(ys)))
    return sorted(boxes, reverse=True)


def _inpaint_region(rgba: np.ndarray, mask: np.ndarray, bounds: tuple[int, int, int, int]) -> None:
    """Fill a small masked region from its surrounding pixels."""
    x0, y0, x1, y1 = bounds
    patch = rgba[y0:y1, x0:x1].copy()
    hole = mask[y0:y1, x0:x1].copy()
    known = ~hole
    height, width = hole.shape
    for _ in range(max(height, width) * 2):
        fill = np.zeros_like(hole)
        updates = np.zeros((height, width, 4), dtype=np.float32)
        counts = np.zeros((height, width), dtype=np.int16)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            shifted_known = np.roll(known, (dy, dx), axis=(0, 1))
            shifted_rgb = np.roll(patch, (dy, dx), axis=(0, 1))
            valid = hole & shifted_known
            if dy < 0:
                valid[dy:, :] = False
            elif dy > 0:
                valid[:dy, :] = False
            if dx < 0:
                valid[:, dx:] = False
            elif dx > 0:
                valid[:, :dx] = False
            updates[valid] += shifted_rgb[valid]
            counts[valid] += 1
        newly = hole & (counts > 0)
        if not newly.any():
            break
        patch[newly] = (updates[newly] / counts[newly, None]).astype(np.uint8)
        known[newly] = True
        hole[newly] = False
    rgba[y0:y1, x0:x1] = patch


def make_eye_assets() -> None:
    idle_path = ASSET_DIR / "idle.png"
    if not idle_path.exists():
        raise FileNotFoundError("请先运行 prepare_assets.py 生成 idle.png")

    rgba = np.array(Image.open(idle_path).convert("RGBA"))
    r = rgba[..., 0].astype(np.int16)
    g = rgba[..., 1].astype(np.int16)
    b = rgba[..., 2].astype(np.int16)
    alpha = rgba[..., 3]
    green_mask = (alpha > 128) & (g > r * 1.05) & (g > b * 1.05) & (g > 45) & (r < 180)
    eyes = _component_boxes(green_mask, min_area=50)[:2]
    if len(eyes) != 2:
        raise ValueError(f"只找到 {len(eyes)} 只眼睛，无法生成眼神图层")
    eyes.sort(key=lambda box: box[1])

    eye_meta = []
    pupil_rgba = rgba.copy()
    input_height, input_width = alpha.shape
    for _, ex0, ey0, ex1, ey1 in eyes:
        eye_width = ex1 - ex0 + 1
        eye_height = ey1 - ey0 + 1
        dark = (rgba[..., :3].max(axis=2) < 92) & (alpha > 128)
        local_dark = np.zeros_like(alpha, dtype=bool)
        local_dark[ey0 : ey1 + 1, ex0 : ex1 + 1] = dark[ey0 : ey1 + 1, ex0 : ex1 + 1]
        dark_boxes = _component_boxes(local_dark, min_area=8)
        if not dark_boxes:
            raise ValueError("没有找到瞳孔")
        _, px0, py0, px1, py1 = dark_boxes[0]

        hole = np.zeros_like(alpha, dtype=bool)
        hole[py0 : py1 + 1, px0 : px1 + 1] = True
        hole_image = Image.fromarray((hole * 255).astype(np.uint8), "L")
        hole_image = hole_image.filter(ImageFilter.MaxFilter(3))
        hole = np.asarray(hole_image) > 0
        hole[:ey0, :] = False
        hole[ey1 + 1 :, :] = False
        hole[:, :ex0] = False
        hole[:, ex1 + 1 :] = False
        _inpaint_region(pupil_rgba, hole, (ex0 - 1, ey0 - 1, ex1 + 2, ey1 + 2))

        eye_meta.append(
            {
                "center": [round((px0 + px1 + 1) / 2.0, 3), round((py0 + py1 + 1) / 2.0, 3)],
                "eyeBox": [int(ex0), int(ey0), int(ex1 + 1), int(ey1 + 1)],
                "eyeSize": [int(eye_width), int(eye_height)],
            }
        )

    Image.fromarray(pupil_rgba, "RGBA").save(ASSET_DIR / "idle_eyes.png", optimize=True)

    resolution = 6
    width, height = 9 * resolution, 11 * resolution
    sprite = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite)
    draw.ellipse((1 * resolution, 1 * resolution, 8 * resolution - 1, 10 * resolution - 1), fill=(21, 18, 14, 255))
    draw.ellipse((2 * resolution, 2 * resolution, 4 * resolution, 4 * resolution), fill=(75, 83, 54, 150))
    sprite = sprite.resize((9, 11), Image.Resampling.LANCZOS)
    sprite.save(ASSET_DIR / "pupil.png", optimize=True)

    metadata = {
        "referenceSize": [input_width, input_height],
        "eyes": eye_meta,
        "pupilSize": [9, 11],
        "maxOffset": [2.2, 1.6],
    }
    (ASSET_DIR / "eye_geometry.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"eye assets -> {len(eye_meta)} pupils")


def _write_wav(path: Path, samples: list[float], sample_rate: int = 22050) -> None:
    path.parent.mkdir(exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = bytearray()
        for sample in samples:
            value = max(-1.0, min(1.0, sample))
            frames.extend(struct.pack("<h", round(value * 32767)))
        handle.writeframes(frames)


def make_sounds() -> None:
    sr = 22050

    pop = []
    for index in range(round(sr * 0.13)):
        t = index / sr
        frequency = 560 * math.exp(-t * 8.5) + 180
        envelope = math.exp(-t * 26) * min(1.0, t * 90)
        pop.append(0.16 * envelope * math.sin(2 * math.pi * frequency * t))

    boing = []
    for index in range(round(sr * 0.30)):
        t = index / sr
        frequency = 190 * math.exp(-t * 2.6) + 62
        vibrato = math.sin(2 * math.pi * 18 * t) * 0.018
        envelope = math.exp(-t * 8.5) * min(1.0, t * 70)
        boing.append((0.14 + vibrato) * envelope * math.sin(2 * math.pi * frequency * t))

    happy = []
    notes = (620, 760, 920, 820, 1040)
    for note in notes:
        for index in range(round(sr * 0.105)):
            t = index / sr
            envelope = math.sin(math.pi * min(1.0, t / 0.105)) ** 2
            happy.append(0.075 * envelope * math.sin(2 * math.pi * note * t))
        happy.extend([0.0] * round(sr * 0.018))

    _write_wav(SFX_DIR / "pop.wav", pop, sr)
    _write_wav(SFX_DIR / "boing.wav", boing, sr)
    _write_wav(SFX_DIR / "happy.wav", happy, sr)
    print("sound assets -> pop, boing, happy")


def make_app_icon() -> None:
    source = ASSET_DIR / "laugh" / "f0100.webp"
    if not source.exists():
        source = ASSET_DIR / "idle.png"
    image = Image.open(source).convert("RGBA")
    box = image.getchannel("A").getbbox()
    if box:
        image = image.crop(box)
    side = max(image.width, image.height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((side - image.width) // 2, (side - image.height) // 2))
    canvas = canvas.resize((256, 256), Image.Resampling.LANCZOS)
    canvas.save(
        ASSET_DIR / "app.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("app icon -> assets/app.ico")


def main() -> None:
    make_eye_assets()
    make_sounds()
    make_app_icon()


if __name__ == "__main__":
    main()
