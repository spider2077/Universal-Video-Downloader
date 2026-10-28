# Location: Universal-Video-Downloader/generate_icons.py
# Script: generate_icons.py

"""Generate the app icon: a rounded indigo-violet tile with a download arrow and a play badge.

Writes icons/icon{16,32,48,128,256}.png, icons/app_icon.ico (Windows) and the Android
launcher mipmaps. Pure Pillow, no external assets, so the build stays reproducible.
"""

import os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(HERE, "icons")
ANDROID_RES = os.path.join(HERE, "android", "app", "src", "main", "res")

PNG_SIZES = (16, 32, 48, 128, 256)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
ANDROID_MIPMAPS = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}

COLOR_TOP = (79, 70, 229)      # indigo
COLOR_BOTTOM = (168, 85, 247)  # violet
WHITE = (255, 255, 255, 255)
RENDER_SIZE = 1024             # drawn large, then downscaled with antialiasing


def gradient_tile(size, radius_frac=0.22):
    grad = Image.new("RGBA", (size, size))
    px = grad.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            px[x, y] = tuple(int(COLOR_TOP[i] + (COLOR_BOTTOM[i] - COLOR_TOP[i]) * t) for i in range(3)) + (255,)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * radius_frac), fill=255)
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile.paste(grad, (0, 0), mask)
    return tile


def arrow_and_tray(size):
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = size / 2
    shaft = size * 0.16
    d.rounded_rectangle([cx - shaft / 2, size * 0.20, cx + shaft / 2, size * 0.54], radius=shaft / 2, fill=WHITE)
    d.polygon([(cx - size * 0.24, size * 0.52), (cx + size * 0.24, size * 0.52), (cx, size * 0.70)], fill=WHITE)
    tray = size * 0.075
    d.rounded_rectangle([size * 0.20, size * 0.80, size * 0.80, size * 0.80 + tray], radius=tray / 2, fill=WHITE)
    return layer


def play_badge(size):
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = size * 0.17
    cx, cy = size * 0.74, size * 0.74
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE)
    tri = r * 0.55
    d.polygon([(cx - tri * 0.7, cy - tri), (cx - tri * 0.7, cy + tri), (cx + tri * 0.9, cy)], fill=COLOR_BOTTOM + (255,))
    return layer


def soft_shadow(layer, size):
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    alpha = layer.split()[3].point(lambda a: int(a * 0.35))
    shadow.paste((0, 0, 0, 255), (0, int(size * 0.02)), alpha)
    return shadow.filter(ImageFilter.GaussianBlur(size * 0.018))


def render(with_badge=True):
    size = RENDER_SIZE
    icon = gradient_tile(size)
    glyph = arrow_and_tray(size)
    icon.alpha_composite(soft_shadow(glyph, size))
    icon.alpha_composite(glyph)
    if with_badge:
        icon.alpha_composite(play_badge(size))
    return icon


def main():
    os.makedirs(ICONS_DIR, exist_ok=True)
    full = render(with_badge=True)
    plain = render(with_badge=False)   # the badge is just noise below 32 px

    def at(size):
        return (full if size >= 32 else plain).resize((size, size), Image.LANCZOS)

    for size in PNG_SIZES:
        path = os.path.join(ICONS_DIR, f"icon{size}.png")
        at(size).save(path)
        print(f"Created {path}")

    ico_path = os.path.join(ICONS_DIR, "app_icon.ico")
    at(256).save(ico_path, format="ICO", sizes=[(s, s) for s in ICO_SIZES],
                 append_images=[at(s) for s in ICO_SIZES if s != 256])
    print(f"Created {ico_path}")

    if os.path.isdir(ANDROID_RES):
        for density, size in ANDROID_MIPMAPS.items():
            folder = os.path.join(ANDROID_RES, f"mipmap-{density}")
            os.makedirs(folder, exist_ok=True)
            at(size).save(os.path.join(folder, "ic_launcher.png"))
        print("Updated Android launcher icons")


if __name__ == "__main__":
    main()
