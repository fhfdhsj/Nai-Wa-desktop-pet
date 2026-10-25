from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"
NEW_PICTURE_DIR = ROOT / "new-picture"
CRAWL_DIR = ASSET_DIR / "crawl"

SOURCES = {
    "wave_left": "085464afb28d573a0ab4f83e46a5e347.jpg",
    "wave_right": "65e8a366e9ba7da7ef1570c60feac030.jpg",
    "side": "5c6ddb24194160379e5350522fc007db.jpg",
    "sheet": "2efe93f887cd24074cd917cc46cb8319.jpg",
}

# Approximate character-only crops from the four-view reference sheet.
SHEET_CROPS = {
    "idle": (360, 55, 655, 620),
    "back": (865, 55, 1160, 620),
}


def remove_small_islands(alpha: np.ndarray, min_area: int = 600) -> np.ndarray:
    """Drop detached source-image fragments, such as the neighbouring character."""
    mask = alpha > 20
    seen = np.zeros_like(mask, dtype=bool)
    height, width = mask.shape
    for start_y, start_x in zip(*np.nonzero(mask)):
        if seen[start_y, start_x]:
            continue
        queue = deque([(start_y, start_x)])
        seen[start_y, start_x] = True
        points: list[tuple[int, int]] = []
        while queue:
            y, x = queue.popleft()
            points.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        if len(points) < min_area:
            ys, xs = zip(*points)
            alpha[np.asarray(ys), np.asarray(xs)] = 0
    return alpha


def remove_ground_shadow(alpha: np.ndarray, rgb: np.ndarray, min_area: int = 100) -> np.ndarray:
    """Remove the large light-gray floor shadow, but keep light toe pixels."""
    mask = alpha > 20
    mask[: int(mask.shape[0] * 0.68)] = False
    high = np.max(rgb, axis=2)
    low = np.min(rgb, axis=2)
    mask &= (high >= 175) & ((high - low) <= 55)

    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    for start_y, start_x in zip(*np.nonzero(mask)):
        if seen[start_y, start_x]:
            continue
        queue = deque([(start_y, start_x)])
        seen[start_y, start_x] = True
        points: list[tuple[int, int]] = []
        while queue:
            y, x = queue.popleft()
            points.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((ny, nx))
        if len(points) >= min_area:
            ys, xs = zip(*points)
            alpha[np.asarray(ys), np.asarray(xs)] = 0
    return alpha


def remove_white_background(image: Image.Image, fill_enclosed: bool = True, strict_white: bool = False) -> Image.Image:
    """Remove the connected light background while preserving the cream belly."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    high = np.maximum(np.maximum(r, g), b)
    low = np.minimum(np.minimum(r, g), b)
    if strict_white:
        near_white = (low >= 246) & (high - low <= 8)
    else:
        near_white = (low >= 224) & (high - low <= 32)

    candidate = Image.fromarray(np.where(near_white, 255, 0).astype(np.uint8), "L").copy()
    width, height = candidate.size
    for point in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        if candidate.getpixel(point) == 255:
            ImageDraw.floodfill(candidate, point, 128, thresh=0)

    # White background can also be enclosed by legs or arms. Find those
    # regions with a coarse seed grid; the cream belly is not near-white.
    for y in (range(8, height - 1, 16) if fill_enclosed else ()):
        for x in range(8, width - 1, 16):
            if candidate.getpixel((x, y)) == 255:
                ImageDraw.floodfill(candidate, (x, y), 128, thresh=0)

    background = np.asarray(candidate) == 128
    alpha = np.where(background, 0, 255).astype(np.uint8)
    alpha = remove_small_islands(alpha, min_area=5000)
    if not strict_white:
        alpha = remove_ground_shadow(alpha, rgb, min_area=100)
    alpha_img = Image.fromarray(alpha, "L")

    # Shave the white fringe, then soften the cutout edge slightly.
    alpha_img = alpha_img.filter(ImageFilter.MinFilter(3))
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(0.65))

    rgba = image.convert("RGBA")
    rgba.putalpha(alpha_img)
    bbox = alpha_img.point(lambda value: 255 if value > 12 else 0).getbbox()
    if bbox is None:
        raise ValueError("No character found after background removal")
    left, top, right, bottom = bbox
    margin = 3
    return rgba.crop(
        (
            max(0, left - margin),
            max(0, top - margin),
            min(rgba.width, right + margin),
            min(rgba.height, bottom + margin),
        )
    )


def fit_sprite(image: Image.Image, height: int = 300, max_width: int = 340) -> Image.Image:
    scale = min(height / image.height, max_width / image.width)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def save_sprite(name: str, source: Path, crop=None) -> Image.Image:
    image = Image.open(source).convert("RGB")
    if crop:
        image = image.crop(crop)
    sprite = fit_sprite(remove_white_background(image))
    sprite.save(ASSET_DIR / f"{name}.png", optimize=True)
    print(f"{name:10s} -> {sprite.width}x{sprite.height}")
    return sprite


def prepare_new_pictures() -> dict[str, Image.Image]:
    files = sorted(NEW_PICTURE_DIR.glob("*.jpg")) if NEW_PICTURE_DIR.exists() else []
    if len(files) < 14:
        print(f"new-picture skipped: found {len(files)} images")
        return {}

    result = {}
    for name, index in (("tummy", 0), ("peace", 13)):
        sprite = fit_sprite(remove_white_background(Image.open(files[index]).convert("RGB"), fill_enclosed=False, strict_white=True))
        sprite.save(ASSET_DIR / f"{name}.png", optimize=True)
        result[name] = sprite
        print(f"{name:10s} -> {sprite.width}x{sprite.height}")

    CRAWL_DIR.mkdir(exist_ok=True)
    for output_index, source_index in enumerate(range(3, 10), start=1):
        source = remove_white_background(Image.open(files[source_index]).convert("RGB"), fill_enclosed=False, strict_white=True)
        character = fit_sprite(source, height=210, max_width=300)
        canvas = Image.new("RGBA", (320, 250), (0, 0, 0, 0))
        canvas.alpha_composite(character, ((320 - character.width) // 2, 245 - character.height))
        canvas.save(CRAWL_DIR / f"f{output_index:02d}.png", optimize=True)
    print(f"crawl frames -> {len(files[3:10])}")
    return result


def make_preview(sprites: dict[str, Image.Image]) -> None:
    cell_w, cell_h = 370, 340
    columns = min(4, max(1, len(sprites)))
    rows = (len(sprites) + columns - 1) // columns
    preview = Image.new("RGB", (cell_w * columns, cell_h * rows), "#f4eee5")
    draw = ImageDraw.Draw(preview)
    for y in range(0, preview.height, 20):
        for x in range(0, preview.width, 20):
            if (x // 20 + y // 20) % 2:
                draw.rectangle((x, y, x + 19, y + 19), fill="#e8dfd2")

    for index, (name, sprite) in enumerate(sprites.items()):
        col, row = index % columns, index // columns
        x = col * cell_w + (cell_w - sprite.width) // 2
        y = row * cell_h + cell_h - sprite.height - 22
        preview.paste(sprite, (x, y), sprite)
        draw.text((col * cell_w + 12, row * cell_h + 10), name, fill="#493a2c")
    preview.save(ASSET_DIR / "_preview.png", optimize=True)


def main() -> None:
    ASSET_DIR.mkdir(exist_ok=True)
    sheet = ROOT / SOURCES["sheet"]
    sprites = {
        "idle": save_sprite("idle", sheet, SHEET_CROPS["idle"]),
        "wave_left": save_sprite("wave_left", ROOT / SOURCES["wave_left"]),
        "wave_right": save_sprite("wave_right", ROOT / SOURCES["wave_right"]),
        "side": save_sprite("side", ROOT / SOURCES["side"]),
        "back": save_sprite("back", sheet, SHEET_CROPS["back"]),
    }
    sprites.update(prepare_new_pictures())
    make_preview(sprites)

    # Generate the eye layer and local sound effects from the finished sprites.
    from prepare_effects import main as prepare_effects

    prepare_effects()
    print(f"Assets written to {ASSET_DIR}")


if __name__ == "__main__":
    main()






