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
SOURCE = ROOT / "assets" / "source"
BORDER_IMAGE = SOURCE / "literary-border.png"

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
    upper_title: str = "LITERARY QUOTE OF THE DAY"
    upper_text: str = "I declare after all there is no enjoyment like reading!"
    upper_author: str = "Jane Austen"
    lower_title: str = "ON THIS DAY IN LITERATURE"
    lower_text: str = "In 1616, Shakespeare died in Stratford-upon-Avon on his 52nd birthday."
    lower_author: str = ""


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
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "desk-clock-rpi3/0.2.6"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        fallback = ClockData(now=now)
        upper = payload.get("upper") if isinstance(payload.get("upper"), dict) else {}
        lower = payload.get("lower") if isinstance(payload.get("lower"), dict) else {}
        quote = payload.get("quote") if isinstance(payload.get("quote"), dict) else {}
        return ClockData(
            now=now,
            greeting=greeting_for(now),
            upper_title=str(upper.get("title") or quote.get("title") or fallback.upper_title),
            upper_text=str(upper.get("text") or quote.get("text") or payload.get("quote") or fallback.upper_text),
            upper_author=str(upper.get("author") or quote.get("author") or payload.get("author") or fallback.upper_author),
            lower_title=str(lower.get("title") or payload.get("literature_title") or fallback.lower_title),
            lower_text=str(lower.get("text") or payload.get("literature_text") or fallback.lower_text),
            lower_author=str(lower.get("author") or fallback.lower_author),
        )
    except (TimeoutError, URLError, ValueError, KeyError, TypeError, OSError):
        return ClockData(now=now, greeting=greeting_for(now))


def font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf" if bold and italic else "",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf" if italic else "",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-BoldOblique.ttf" if bold and italic else "",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Oblique.ttf" if italic else "",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
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


def page_background() -> Image.Image:
    if BORDER_IMAGE.exists():
        image = Image.open(BORDER_IMAGE).convert("L")
        image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        image = ImageEnhance.Contrast(image).enhance(1.2)
        return image
    return Image.new("L", (WIDTH, HEIGHT), PAPER)


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
    image = page_background()

    draw = ImageDraw.Draw(image)
    title = font(31, bold=True)
    quote_font = font(35)
    author_font = font(23)
    small_caps = font(18, bold=True)
    body = font(23)

    centered_text(draw, WIDTH // 2, 114, data.greeting or greeting_for(data.now), title)

    centered_text(draw, WIDTH // 2, 198, data.upper_title.upper(), small_caps)
    y = wrapped_centered(draw, WIDTH // 2, 232, data.upper_text, quote_font, width=24, line_gap=48, max_lines=4)
    if data.upper_author:
        centered_text(draw, WIDTH // 2, min(y + 8, 450), f"- {data.upper_author}", author_font)

    centered_text(draw, WIDTH // 2, 494, data.lower_title.upper(), small_caps)
    y = wrapped_centered(draw, WIDTH // 2, 532, data.lower_text, body, width=30, line_gap=34, max_lines=4)
    if data.lower_author:
        centered_text(draw, WIDTH // 2, min(y + 4, 680), data.lower_author, font(18, italic=True))

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
