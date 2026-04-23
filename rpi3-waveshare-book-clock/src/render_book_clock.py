#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import argparse
import colorsys
import math
import textwrap

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BG = ROOT / "assets" / "source" / "book-background-source.png"
GENERATED = ROOT / "assets" / "generated"

WIDTH = 800
HEIGHT = 480


@dataclass(frozen=True)
class ClockData:
    now: datetime
    temperature: str = "72F"
    condition: str = "Partly Cloudy"
    humidity: str = "45%"
    wind: str = "8 mph N"
    quote: str = "A room without books is like a body without a soul."
    author: str = "Cicero"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/google-noto-vf/NotoSerif[wght].ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def cover_crop(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / img.width, target_h / img.height)
    resized = img.resize((math.ceil(img.width * scale), math.ceil(img.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def prepare_background() -> Image.Image:
    bg = Image.open(SOURCE_BG).convert("RGB")
    bg = cover_crop(bg, (WIDTH, HEIGHT))
    bg = ImageEnhance.Color(bg).enhance(0.72)
    bg = ImageEnhance.Contrast(bg).enhance(1.18)
    bg = ImageEnhance.Sharpness(bg).enhance(1.35)
    return bg


def draw_centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, typeface, fill: tuple[int, int, int]) -> None:
    text_box = draw.textbbox((0, 0), text, font=typeface)
    x = box[0] + (box[2] - box[0] - (text_box[2] - text_box[0])) // 2
    y = box[1] + (box[3] - box[1] - (text_box[3] - text_box[1])) // 2
    draw.text((x, y), text, font=typeface, fill=fill)


def draw_rule(draw: ImageDraw.ImageDraw, x0: int, y: int, x1: int, fill: tuple[int, int, int]) -> None:
    draw.line((x0, y, x1, y), fill=fill, width=2)
    draw.line((x0 + 12, y + 5, x1 - 12, y + 5), fill=fill, width=1)


def overlay_content(img: Image.Image, data: ClockData) -> Image.Image:
    out = img.copy()
    draw = ImageDraw.Draw(out)
    ink = (28, 24, 18)
    red = (154, 28, 20)

    title_font = font(36, bold=True)
    big_font = font(72, bold=True)
    medium_font = font(30)
    small_font = font(23)
    tiny_font = font(18)
    quote_font = font(25)

    draw_centered(draw, (110, 32, 690, 78), "THE DAILY CHRONICLE", title_font, ink)
    draw_rule(draw, 70, 92, 730, ink)

    time_text = data.now.strftime("%-I:%M %p")
    date_1 = data.now.strftime("%A")
    date_2 = data.now.strftime("%B %-d, %Y")

    draw_centered(draw, (80, 128, 350, 218), time_text, big_font, ink)
    draw_centered(draw, (95, 214, 335, 254), date_1, medium_font, ink)
    draw_centered(draw, (82, 254, 350, 292), date_2, small_font, ink)

    draw_rule(draw, 96, 318, 330, ink)
    draw.text((112, 346), f"{data.temperature}  {data.condition}", font=small_font, fill=ink)
    draw.text((112, 380), f"Humidity {data.humidity}", font=tiny_font, fill=ink)
    draw.text((112, 406), f"Wind {data.wind}", font=tiny_font, fill=ink)

    draw_centered(draw, (468, 130, 720, 168), "QUOTE OF THE DAY", medium_font, red)
    draw_rule(draw, 470, 184, 720, red)
    quote_lines = textwrap.wrap(f"\"{data.quote}\"", width=24)
    y = 218
    for line in quote_lines[:5]:
        draw.text((476, y), line, font=quote_font, fill=ink)
        y += 34
    draw.text((560, y + 14), f"- {data.author}", font=small_font, fill=ink)

    draw.text((178, 452), "page 042", font=tiny_font, fill=red)
    draw.text((580, 452), "page 043", font=tiny_font, fill=red)
    return out


def floyd_steinberg_1bit(gray: Image.Image, threshold: int) -> Image.Image:
    work = gray.convert("L")
    return work.convert("1", dither=Image.Dither.FLOYDSTEINBERG)


def split_epaper_channels(rgb: Image.Image) -> tuple[Image.Image, Image.Image, Image.Image]:
    pixels = rgb.convert("RGB").load()
    black = Image.new("1", (WIDTH, HEIGHT), 255)
    red = Image.new("1", (WIDTH, HEIGHT), 255)
    black_px = black.load()
    red_px = red.load()

    gray = rgb.convert("L")
    dithered_black = floyd_steinberg_1bit(gray, 132)
    dither_px = dithered_black.load()

    for y in range(HEIGHT):
        for x in range(WIDTH):
            r, g, b = pixels[x, y]
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            hue = h * 360
            is_red = (hue < 24 or hue > 340) and s > 0.30 and r > 85 and r > g * 1.35 and r > b * 1.35
            if is_red:
                red_px[x, y] = 0
                black_px[x, y] = 255
            elif dither_px[x, y] == 0:
                black_px[x, y] = 0
                red_px[x, y] = 255

    preview = Image.new("RGB", (WIDTH, HEIGHT), "white")
    black_mask = ImageChops.invert(black.convert("L"))
    red_mask = ImageChops.invert(red.convert("L"))
    preview.paste((0, 0, 0), mask=black_mask)
    preview.paste((180, 0, 0), mask=red_mask)
    return black, red, preview


def render(data: ClockData) -> tuple[Image.Image, Image.Image, Image.Image, Image.Image]:
    background = prepare_background()
    full_color = overlay_content(background, data)
    black, red, preview = split_epaper_channels(full_color)
    return full_color, black, red, preview


def save_outputs(data: ClockData) -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    full_color, black, red, preview = render(data)
    full_color.save(GENERATED / "book-clock-color-source.png")
    black.save(GENERATED / "book-clock-black.png")
    red.save(GENERATED / "book-clock-red.png")
    preview.save(GENERATED / "book-clock-preview.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--time", help="ISO datetime to render instead of current local time")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.time) if args.time else datetime.now()
    save_outputs(ClockData(now=now))
    print(f"wrote previews to {GENERATED}")


if __name__ == "__main__":
    main()
