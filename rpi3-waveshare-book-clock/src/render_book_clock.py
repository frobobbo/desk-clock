#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import argparse
import json
import os
import textwrap
from urllib.error import URLError
from urllib.request import Request, urlopen

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
    greeting: str = ""
    quote: str = "I declare after all there is no enjoyment like reading!"
    author: str = "Jane Austen"
    literature_title: str = "ON THIS DAY IN LITERATURE"
    literature_text: str = "In 1616, Shakespeare died in Stratford-upon-Avon on his 52nd birthday."


def greeting_for(now: datetime) -> str:
    hour = now.hour
    if 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 17:
        period = "afternoon"
    elif 17 <= hour < 22:
        period = "evening"
    else:
        period = "night"
    return f"Good {period}, Lyndsay"


def fetch_clock_data(now: datetime, api_url: str | None = None) -> ClockData:
    api_url = (api_url or os.getenv("CONFIG_API_URL") or "http://deskclock.johnsons.casa").rstrip("/")
    url = f"{api_url}/api/displays/waveshare-rpi3/literary"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "desk-clock-rpi3/0.2.5"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return ClockData(
            now=now,
            greeting=greeting_for(now),
            quote=str(payload.get("quote") or ClockData(now=now).quote),
            author=str(payload.get("author") or ClockData(now=now).author),
            literature_title=str(payload.get("literature_title") or ClockData(now=now).literature_title),
            literature_text=str(payload.get("literature_text") or ClockData(now=now).literature_text),
        )
    except (TimeoutError, URLError, ValueError, KeyError, TypeError, OSError):
        return ClockData(now=now, greeting=greeting_for(now))


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


def flourish(draw: ImageDraw.ImageDraw, center_x: int, y: int, width: int = 210) -> None:
    draw.line((center_x - width // 2, y, center_x - 26, y), fill=INK, width=1)
    draw.line((center_x + 26, y, center_x + width // 2, y), fill=INK, width=1)
    draw.ellipse((center_x - 8, y - 8, center_x + 8, y + 8), outline=INK, width=1)
    draw.polygon(
        [
            (center_x, y - 12),
            (center_x + 7, y),
            (center_x, y + 12),
            (center_x - 7, y),
        ],
        outline=INK,
    )
    for side in (-1, 1):
        sx = center_x + side * 24
        draw.arc((sx - 18, y - 14, sx + 18, y + 14), 205 if side < 0 else -25, 335 if side < 0 else 155, fill=INK, width=1)


def corner_marks(draw: ImageDraw.ImageDraw) -> None:
    corners = [(30, 28, 1, 1), (WIDTH - 30, 28, -1, 1), (30, HEIGHT - 28, 1, -1), (WIDTH - 30, HEIGHT - 28, -1, -1)]
    for x, y, sx, sy in corners:
        draw.line((x, y, x + 26 * sx, y), fill=INK, width=1)
        draw.line((x, y, x, y + 26 * sy), fill=INK, width=1)
        draw.arc((x - 8 if sx < 0 else x, y - 8 if sy < 0 else y, x + 16 if sx > 0 else x + 8, y + 16 if sy > 0 else y + 8), 0, 360, fill=INK)


def draw_layout(data: ClockData) -> Image.Image:
    image = Image.new("L", (WIDTH, HEIGHT), PAPER)

    draw = ImageDraw.Draw(image)
    title = font(28)
    date_font = font(20)
    quote_font = font(32)
    author_font = font(22)
    small_caps = font(17)
    body = font(21)

    draw.rounded_rectangle((12, 12, WIDTH - 12, HEIGHT - 12), radius=16, outline=INK, width=2)
    draw.rounded_rectangle((18, 18, WIDTH - 18, HEIGHT - 18), radius=12, outline=210, width=1)
    corner_marks(draw)

    centered_text(draw, WIDTH // 2, 46, data.greeting or greeting_for(data.now), title)
    ornament_rule(draw, 100, 105, 375)

    centered_text(draw, WIDTH // 2, 132, data.now.strftime("%A, %B %-d, %Y"), date_font)
    flourish(draw, WIDTH // 2, 174, 150)

    y = wrapped_centered(draw, WIDTH // 2, 224, data.quote, quote_font, width=26, line_gap=44, max_lines=4)
    centered_text(draw, WIDTH // 2, min(y + 8, 450), f"- {data.author}", author_font)
    flourish(draw, WIDTH // 2, 506, 190)

    centered_text(draw, WIDTH // 2, 552, data.literature_title.upper(), small_caps)
    wrapped_centered(draw, WIDTH // 2, 596, data.literature_text, body, width=34, line_gap=32, max_lines=5)
    ornament_rule(draw, 744, 125, 355)

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
    parser.add_argument("--config-api-url", help="Config API base URL")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.time) if args.time else datetime.now()
    save_outputs(fetch_clock_data(now, args.config_api_url))
    print(f"wrote previews to {GENERATED}")


if __name__ == "__main__":
    main()
