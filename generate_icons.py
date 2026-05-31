# Location: Universal-Video-Downloader/generate_icons.py
# Script: generate_icons.py

"""Generate simple app icons for PyInstaller build."""

import os
from PIL import Image, ImageDraw

SIZES = (16, 48, 128)
COLOR_BG = (30, 100, 200)
COLOR_FG = (255, 255, 255)


def draw_icon(size):
    img = Image.new("RGBA", (size, size), COLOR_BG)
    draw = ImageDraw.Draw(img)
    margin = max(2, size // 8)
    shaft_w = max(2, size // 6)
    head = size // 3
    cx = size // 2
    top = margin
    bottom = size - margin

    draw.rectangle(
        [cx - shaft_w // 2, top + head, cx + shaft_w // 2, bottom - head // 2],
        fill=COLOR_FG,
    )
    draw.polygon(
        [
            (cx, bottom),
            (cx - head, bottom - head),
            (cx + head, bottom - head),
        ],
        fill=COLOR_FG,
    )
    draw.rectangle(
        [margin, top, size - margin, top + head],
        fill=COLOR_FG,
    )
    return img


def main():
    icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
    os.makedirs(icons_dir, exist_ok=True)
    for size in SIZES:
        path = os.path.join(icons_dir, f"icon{size}.png")
        draw_icon(size).save(path)
        print(f"Created {path}")


if __name__ == "__main__":
    main()
