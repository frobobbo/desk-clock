#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import argparse
import math
import textwrap

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "assets" / "generated"

PANEL_WIDTH = 800
PANEL_HEIGHT = 480
WIDTH = 480
HEIGHT = 800
INK = 28
MID = 122
PAPER = 236


@dataclass(frozen=True)
class ClockData:
    now: datetime
    greeting: str = "Good morning, Lauren"
    quote: str = "I declare after all there is no enjoyment like reading!"
    author: str = "Jane Austen"
    literature_title: str = "ON THIS DAY IN LITERATURE"
    literature_text: str = "In 1616, Shakespeare died in Stratford-upon-Avon on his 52nd birthday."
    temperature: str = "72F"
    condition: str = "Cloudy"
    high_low: str = "H 75 L 58"
    reading_title: str = "CURRENTLY READING"
    book_title: str = "Pride and Prejudice"
    book_author: str = "Jane Austen"
    page_current: int = 142
    page_total: int = 386
    library_due: str = "May 6"


def font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/google-noto-vf/NotoSerif[wght].ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf" if bold and italic else "",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf" if italic else "",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, typeface) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=typeface)
    return box[2] - box[0], box[3] - box[1]


def centered_text(draw: ImageDraw.ImageDraw, center_x: int, y: int, text: str, typeface, fill: int = INK) -> None:
    w, _ = text_size(draw, text, typeface)
    draw.text((center_x - w // 2, y), text, font=typeface, fill=fill)


def wrapped_centered(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    y: int,
    text: str,
    typeface,
    width: int,
    line_gap: int,
    fill: int = INK,
    max_lines: int | None = None,
) -> int:
    lines = textwrap.wrap(text, width=width)
    if max_lines:
        lines = lines[:max_lines]
    for line in lines:
        centered_text(draw, center_x, y, line, typeface, fill)
        y += line_gap
    return y


def ornament_rule(draw: ImageDraw.ImageDraw, y: int, x0: int = 270, x1: int = 530) -> None:
    cx = (x0 + x1) // 2
    draw.line((x0, y, cx - 24, y), fill=INK, width=1)
    draw.line((cx + 24, y, x1, y), fill=INK, width=1)
    for dx in (-16, 0, 16):
        draw.ellipse((cx + dx - 5, y - 5, cx + dx + 5, y + 5), outline=INK, width=1)
    draw.polygon([(cx, y - 9), (cx + 5, y), (cx, y + 9), (cx - 5, y)], fill=INK)


def leaf_sprig(draw: ImageDraw.ImageDraw, x: int, y: int, direction: int) -> None:
    draw.line((x, y + 22, x + 34 * direction, y), fill=INK, width=2)
    for i in range(5):
        px = x + (8 + i * 6) * direction
        py = y + 19 - i * 4
        draw.ellipse((px - 4, py - 8, px + 4, py + 2), outline=INK, width=1)


def corner_marks(draw: ImageDraw.ImageDraw) -> None:
    corners = [(30, 28, 1, 1), (WIDTH - 30, 28, -1, 1), (30, HEIGHT - 28, 1, -1), (WIDTH - 30, HEIGHT - 28, -1, -1)]
    for x, y, sx, sy in corners:
        draw.line((x, y, x + 26 * sx, y), fill=INK, width=1)
        draw.line((x, y, x, y + 26 * sy), fill=INK, width=1)
        draw.arc((x - 8 if sx < 0 else x, y - 8 if sy < 0 else y, x + 16 if sx > 0 else x + 8, y + 16 if sy > 0 else y + 8), 0, 360, fill=INK)


def draw_cloud(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 6, y + 12, x + 34, y + 38), outline=INK, width=2)
    draw.ellipse((x + 26, y + 4, x + 58, y + 38), outline=INK, width=2)
    draw.ellipse((x + 50, y + 16, x + 78, y + 40), outline=INK, width=2)
    draw.rectangle((x + 16, y + 28, x + 68, y + 42), fill=PAPER)
    draw.arc((x + 6, y + 12, x + 34, y + 38), 180, 360, fill=INK, width=2)
    draw.arc((x + 26, y + 4, x + 58, y + 38), 180, 360, fill=INK, width=2)
    draw.arc((x + 50, y + 16, x + 78, y + 40), 180, 360, fill=INK, width=2)
    draw.line((x + 10, y + 39, x + 74, y + 39), fill=INK, width=2)


def draw_book_icon(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.line((x, y + 2, x, y + 28), fill=INK, width=2)
    draw.line((x + 28, y, x + 28, y + 28), fill=INK, width=2)
    draw.line((x + 56, y + 2, x + 56, y + 28), fill=INK, width=2)
    draw.line((x, y + 2, x + 28, y), fill=INK, width=2)
    draw.line((x + 56, y + 2, x + 28, y), fill=INK, width=2)
    draw.line((x, y + 28, x + 28, y + 22), fill=INK, width=2)
    draw.line((x + 56, y + 28, x + 28, y + 22), fill=INK, width=2)


def draw_bookshelf(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.line((x, y + 86, x + 150, y + 86), fill=INK, width=2)
    draw.rectangle((x + 8, y + 24, x + 138, y + 34), outline=INK, width=2)
    for i in range(8):
        bx = x + 18 + i * 13
        draw.rectangle((bx, y + 35, bx + 10, y + 84), outline=INK, width=1)
        draw.line((bx + 3, y + 42, bx + 3, y + 78), fill=MID, width=1)
    for ox, oy, scale in [(16, 0, 1), (48, -8, 2), (122, 2, 1)]:
        draw.rectangle((x + ox, y + 16 + oy, x + ox + 22, y + 30 + oy), outline=INK, width=1)
        draw.ellipse((x + ox + 2, y + 4 + oy, x + ox + 20, y + 21 + oy), outline=INK, width=1)
        for i in range(5):
            px = x + ox + 11 + (i - 2) * 4 * scale
            draw.line((x + ox + 11, y + 5 + oy, px, y - 18 + oy - i * 4), fill=INK, width=1)
            draw.ellipse((px - 3, y - 21 + oy - i * 4, px + 3, y - 15 + oy - i * 4), outline=INK, width=1)


def draw_reading_section(draw: ImageDraw.ImageDraw, data: ClockData) -> None:
    small_caps = font(13)
    body = font(18)
    small = font(16)
    x = 250
    text_x = x + 42
    draw_book_icon(draw, x, 556)
    draw.text((text_x, 563), data.reading_title, font=small_caps, fill=INK)
    title_y = 596
    for line in textwrap.wrap(data.book_title, width=17)[:2]:
        draw.text((text_x, title_y), line, font=body, fill=INK)
        title_y += 27
    draw.text((text_x, title_y + 2), f"by {data.book_author}", font=small, fill=INK)
    draw.text((text_x, title_y + 34), f"Page {data.page_current} of {data.page_total}", font=small, fill=INK)

    bar_x = text_x
    bar_y = title_y + 62
    bar_w = 150
    progress = max(0.0, min(1.0, data.page_current / max(data.page_total, 1)))
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + 9), radius=3, outline=INK, width=1)
    draw.rounded_rectangle((bar_x, bar_y, bar_x + int(bar_w * progress), bar_y + 9), radius=3, fill=INK)
    draw.text((text_x, min(bar_y + 32, HEIGHT - 46)), f"Next library due: {data.library_due}", font=small, fill=INK)


def draw_layout(data: ClockData) -> Image.Image:
    image = Image.new("L", (WIDTH, HEIGHT), PAPER)

    draw = ImageDraw.Draw(image)
    title = font(28)
    date_font = font(20)
    quote_font = font(29)
    author_font = font(21)
    small_caps = font(16)
    body = font(18)
    weather_temp = font(29)
    weather = font(18)

    draw.rounded_rectangle((12, 12, WIDTH - 12, HEIGHT - 12), radius=16, outline=INK, width=2)
    draw.rounded_rectangle((18, 18, WIDTH - 18, HEIGHT - 18), radius=12, outline=210, width=1)
    corner_marks(draw)

    centered_text(draw, WIDTH // 2, 46, data.greeting, title)
    ornament_rule(draw, 100, 105, 375)

    centered_text(draw, WIDTH // 2, 132, data.now.strftime("%A, %B %-d, %Y"), date_font)
    y = wrapped_centered(draw, WIDTH // 2, 182, data.quote, quote_font, width=32, line_gap=40, max_lines=2)
    centered_text(draw, WIDTH // 2, y + 5, f"- {data.author}", author_font)
    ornament_rule(draw, y + 58, 150, 330)

    centered_text(draw, WIDTH // 2, 328, data.literature_title, small_caps)
    wrapped_centered(draw, WIDTH // 2, 362, data.literature_text, body, width=48, line_gap=28, max_lines=3)

    draw.line((150, 530, 452, 530), fill=MID, width=2)
    draw.line((254, 550, 254, HEIGHT - 48), fill=MID, width=2)

    draw_bookshelf(draw, 32, 626)
    draw_cloud(draw, 150, 574)
    centered_text(draw, 188, 650, data.temperature, weather_temp)
    centered_text(draw, 188, 690, data.condition, weather)
    centered_text(draw, 188, 722, data.high_low, weather)
    draw_reading_section(draw, data)

    image = image.filter(ImageFilter.UnsharpMask(radius=1.1, percent=120, threshold=3))
    return image


def render(data: ClockData) -> tuple[Image.Image, Image.Image]:
    portrait = draw_layout(data)
    panel = portrait.rotate(90, expand=True)
    if panel.size != (PANEL_WIDTH, PANEL_HEIGHT):
        panel = panel.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.Resampling.LANCZOS)
    black = panel.point(lambda p: 0 if p < 190 else 255, "1")
    preview = portrait.point(lambda p: 0 if p < 190 else 255, "1").convert("L")
    return black, preview


def save_outputs(data: ClockData) -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    black, preview = render(data)
    black.save(GENERATED / "book-clock-black.png")
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
