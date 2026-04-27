#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "include" / "klyra_clock_font.h"
FONT_PATH = Path("/home/brett/Downloads/klyra-font/KlyraRegular-gwJjY.ttf")

# All chars needed for %A (full weekday) and "%b %d" (abbreviated month + day)
DATE_CHARS = "ADFJMNOSTWabcdeghilnoprstuvy0123456789 "


def render_glyphs(chars: str, size: int, prefix: str) -> tuple[list[str], list[str]]:
    font = ImageFont.truetype(str(FONT_PATH), size)
    bboxes = {ch: font.getbbox(ch) for ch in chars}
    top = min(b[1] for b in bboxes.values())
    bottom = max(b[3] for b in bboxes.values())
    height = bottom - top

    decls: list[str] = [f"constexpr uint8_t {prefix}_HEIGHT = {height};"]
    maps: list[str] = []

    for ch in chars:
        bbox = bboxes[ch]
        width = bbox[2] - bbox[0]
        img = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(img)
        draw.text((-bbox[0], -top), ch, fill=255, font=font)
        mono = img.point(lambda p: 1 if p > 80 else 0, mode="1")
        data = list(mono.getdata())
        safe = {
            ":": "colon",
            "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
            "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
            "A": "A", "P": "P", "M": "M",
        }[ch]
        name = f"{prefix}_{safe}"
        decls.append(f"constexpr uint8_t {name}_WIDTH = {width};")
        decls.append(f"const uint8_t {name}_DATA[] PROGMEM = {{")
        for i in range(0, len(data), 24):
            chunk = ", ".join("1" if v else "0" for v in data[i:i+24])
            decls.append(f"    {chunk},")
        decls.append("};")
        maps.append((ch, name))

    return decls, [f"    case '{ch}': *width = {name}_WIDTH; *height = {prefix}_HEIGHT; return {name}_DATA;" for ch, name in maps]


def render_date_glyphs(size: int) -> tuple[list[str], list[str]]:
    """Render the full date alphabet (letters, digits, space) at the given size."""
    font = ImageFont.truetype(str(FONT_PATH), size)
    non_space = [ch for ch in DATE_CHARS if ch != ' ']
    bboxes = {ch: font.getbbox(ch) for ch in non_space}
    top = min(b[1] for b in bboxes.values())
    bottom = max(b[3] for b in bboxes.values())
    height = bottom - top

    # Space width: 60% of 'n' width
    n_bbox = bboxes['n']
    space_width = max(8, (n_bbox[2] - n_bbox[0]) * 6 // 10)

    decls: list[str] = [
        f"constexpr uint8_t KLYRA_D_HEIGHT = {height};",
        f"constexpr uint8_t KLYRA_D_space_WIDTH = {space_width};",
    ]
    cases: list[str] = [
        f"    case ' ': *width = KLYRA_D_space_WIDTH; *height = 0; return nullptr;",
    ]

    for ch in non_space:
        safe = ch if ch.isalnum() else 'colon'
        name = f"KLYRA_D_{safe}"
        bbox = bboxes[ch]
        width = bbox[2] - bbox[0]
        img = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(img)
        draw.text((-bbox[0], -top), ch, fill=255, font=font)
        mono = img.point(lambda p: 1 if p > 80 else 0, mode="1")
        data = list(mono.getdata())
        decls.append(f"constexpr uint8_t {name}_WIDTH = {width};")
        decls.append(f"const uint8_t {name}_DATA[] PROGMEM = {{")
        for i in range(0, len(data), 24):
            chunk = ", ".join("1" if v else "0" for v in data[i:i+24])
            decls.append(f"    {chunk},")
        decls.append("};")
        cases.append(f"    case '{ch}': *width = {name}_WIDTH; *height = KLYRA_D_HEIGHT; return {name}_DATA;")

    return decls, cases


def main() -> None:
    if not FONT_PATH.exists():
        raise SystemExit(f"font not found: {FONT_PATH}")

    large_decls, large_map = render_glyphs("0123456789:", 96, "KLYRA_L")
    small_decls, small_map = render_glyphs("APM", 44, "KLYRA_S")
    date_decls, date_cases = render_date_glyphs(44)

    lines = [
        "#pragma once",
        "",
        "#include <Arduino.h>",
        "#include <pgmspace.h>",
        "",
    ]
    lines.extend(large_decls)
    lines.append("")
    lines.extend(small_decls)
    lines.append("")
    lines.extend(date_decls)
    lines.extend([
        "",
        "inline const uint8_t* klyraLargeGlyph(char ch, uint8_t* width, uint8_t* height) {",
        "  switch (ch) {",
        *large_map,
        "    default: *width = 0; *height = 0; return nullptr;",
        "  }",
        "}",
        "",
        "inline const uint8_t* klyraSmallGlyph(char ch, uint8_t* width, uint8_t* height) {",
        "  switch (ch) {",
        *small_map,
        "    default: *width = 0; *height = 0; return nullptr;",
        "  }",
        "}",
        "",
        "inline const uint8_t* klyraDateGlyph(char ch, uint8_t* width, uint8_t* height) {",
        "  switch (ch) {",
        *date_cases,
        "    default: *width = 0; *height = 0; return nullptr;",
        "  }",
        "}",
        "",
    ])
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
