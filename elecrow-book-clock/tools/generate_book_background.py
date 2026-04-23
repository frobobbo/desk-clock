#!/usr/bin/env python3
"""
Generate a 1-bit antique open-book background for the ELECROW 5.79" panel.

No external dependencies are required. The firmware output is meant for
ELECROW's EPD_ShowPicture API: row-major, MSB-first, 1 = black ink,
0 = white paper.
"""

from __future__ import annotations

from pathlib import Path
import math


ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "include" / "book_background.h"
PREVIEW = ROOT / "data" / "book_background.pbm"

W = 792
H = 272


def clamp(value: float, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, int(value)))


def hash01(x: int, y: int, seed: int = 0) -> float:
    n = (x * 374761393 + y * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    n ^= n >> 16
    return (n & 0xFFFFFF) / float(0x1000000)


def smooth_noise(x: float, y: float, scale: float, seed: int) -> float:
    gx = int(x / scale)
    gy = int(y / scale)
    fx = (x / scale) - gx
    fy = (y / scale) - gy
    fx = fx * fx * (3.0 - 2.0 * fx)
    fy = fy * fy * (3.0 - 2.0 * fy)

    a = hash01(gx, gy, seed)
    b = hash01(gx + 1, gy, seed)
    c = hash01(gx, gy + 1, seed)
    d = hash01(gx + 1, gy + 1, seed)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def page_edge_left(y: int) -> int:
    return int(18 + 3 * math.sin(y / 38.0) + 2 * math.sin(y / 13.0))


def page_edge_right(y: int) -> int:
    return int(W - 19 + 3 * math.sin(y / 41.0 + 0.8) + 2 * math.sin(y / 14.0))


def luminance(x: int, y: int) -> int:
    left = page_edge_left(y)
    right = page_edge_right(y)
    top = 14 + int(2 * math.sin(x / 45.0))
    bottom = H - 15 + int(2 * math.sin(x / 43.0 + 1.1))

    if x < left or x > right or y < top or y > bottom:
        shade = 238
        shade -= 34 * math.exp(-((x - W / 2) ** 2) / 14000.0)
        return clamp(shade)

    shade = 225

    # Gutter shadow and page curl.
    center = W / 2
    shade -= 48 * math.exp(-((x - center) ** 2) / 170.0)
    shade -= 19 * math.exp(-((x - left) ** 2) / 45.0)
    shade -= 22 * math.exp(-((x - right) ** 2) / 45.0)
    shade -= 14 * math.exp(-((y - top) ** 2) / 80.0)
    shade -= 18 * math.exp(-((y - bottom) ** 2) / 80.0)

    # Warm paper texture translated to monochrome density.
    shade += (smooth_noise(x, y, 18.0, 1) - 0.5) * 24
    shade += (smooth_noise(x, y, 6.0, 2) - 0.5) * 10
    shade += (hash01(x, y, 3) - 0.5) * 12

    # Long vertical fibers.
    fiber = math.sin(x * 0.65 + smooth_noise(x, y, 26.0, 4) * 3.5)
    if fiber > 0.92 and hash01(x, y // 4, 5) > 0.35:
        shade -= 35

    # Foxing and stains.
    for sx, sy, r, depth in (
        (96, 46, 34, 18),
        (690, 66, 30, 16),
        (112, 222, 38, 18),
        (648, 226, 46, 17),
        (398, 136, 62, 12),
    ):
        dist = math.hypot(x - sx, y - sy)
        if dist < r:
            shade -= depth * (1 - dist / r) * (0.65 + smooth_noise(x, y, 7.0, sx))

    # Faint page ruling/print-through lines outside primary text areas.
    if 36 < y < 236 and 40 < x < 752 and not (348 < x < 444):
        wave = int(y + 2 * math.sin(x / 24.0))
        if ((wave % 24 in (0, 1)) and x < 342) or ((wave % 27 == 0) and x > 450):
            shade -= 20

    # Spine crease and page-edge linework.
    if abs(x - center) < 2 and 38 < y < H - 38:
        shade -= 62
    if abs(x - left) < 2 or abs(x - right) < 2:
        shade -= 54
    if abs(y - top) < 2 or abs(y - bottom) < 2:
        shade -= 38

    # Deckled edge flecks.
    if x - left < 9 or right - x < 9 or y - top < 8 or bottom - y < 8:
        if hash01(x, y, 9) > 0.72:
            shade -= 70

    return clamp(shade)


BAYER_8 = (
    (0, 48, 12, 60, 3, 51, 15, 63),
    (32, 16, 44, 28, 35, 19, 47, 31),
    (8, 56, 4, 52, 11, 59, 7, 55),
    (40, 24, 36, 20, 43, 27, 39, 23),
    (2, 50, 14, 62, 1, 49, 13, 61),
    (34, 18, 46, 30, 33, 17, 45, 29),
    (10, 58, 6, 54, 9, 57, 5, 53),
    (42, 26, 38, 22, 41, 25, 37, 21),
)


def is_black(x: int, y: int) -> bool:
    lum = luminance(x, y)
    threshold = 42 + BAYER_8[y & 7][x & 7] * 2.2
    return lum < threshold


def packed_picture_bits() -> bytearray:
    out = bytearray()
    for y in range(H):
        for byte_x in range(0, W, 8):
            value = 0
            for bit in range(8):
                if is_black(byte_x + bit, y):
                    value |= 0x80 >> bit
            out.append(value)
    return out


def write_header(bits: bytes) -> None:
    lines = [
        "#pragma once",
        "",
        "#include <Arduino.h>",
        "#include <pgmspace.h>",
        "",
        f"constexpr uint16_t BOOK_BACKGROUND_WIDTH = {W};",
        f"constexpr uint16_t BOOK_BACKGROUND_HEIGHT = {H};",
        f"constexpr uint32_t BOOK_BACKGROUND_BYTES = {len(bits)};",
        "",
        "// Row-major, MSB-first, for EPD_ShowPicture: 1 = black, 0 = white.",
        "const uint8_t BOOK_BACKGROUND_BITS[] PROGMEM = {",
    ]
    for i in range(0, len(bits), 12):
        chunk = ", ".join(f"0x{b:02X}" for b in bits[i : i + 12])
        lines.append(f"    {chunk},")
    lines.append("};")
    lines.append("")
    HEADER.write_text("\n".join(lines))


def write_pbm(bits: bytes) -> None:
    with PREVIEW.open("wb") as f:
        f.write(f"P4\n{W} {H}\n".encode("ascii"))
        f.write(bits)


def main() -> None:
    picture_bits = packed_picture_bits()
    HEADER.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    write_header(picture_bits)
    write_pbm(picture_bits)
    print(f"wrote {HEADER.relative_to(ROOT)} ({len(picture_bits)} bytes)")
    print(f"wrote {PREVIEW.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
