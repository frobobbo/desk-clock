#!/usr/bin/env python3
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "include" / "lmj_logo.h"
IMG = Path("/home/brett/Pictures/Screenshots/Screenshot From 2026-04-27 13-15-51.png")

TARGET_W = 190
TARGET_H = 242
THRESHOLD = 90


def main() -> None:
    img = Image.open(IMG).convert("L")
    img = img.resize((TARGET_W, TARGET_H), Image.LANCZOS)
    w, h = img.size

    data = [1 if img.getpixel((x, y)) >= THRESHOLD else 0
            for y in range(h) for x in range(w)]

    lines = [
        "#pragma once",
        "",
        "#include <Arduino.h>",
        "#include <pgmspace.h>",
        "",
        f"constexpr uint8_t LMJ_LOGO_WIDTH = {w};",
        f"constexpr uint8_t LMJ_LOGO_HEIGHT = {h};",
        "const uint8_t LMJ_LOGO_DATA[] PROGMEM = {",
    ]
    for i in range(0, len(data), 24):
        lines.append("    " + ", ".join(str(v) for v in data[i:i + 24]) + ",")
    lines += ["};", ""]

    OUT.write_text("\n".join(lines))
    ones = sum(data)
    print(f"wrote {OUT}  ({w}x{h}, {ones}/{len(data)} lit pixels, threshold={THRESHOLD})")


if __name__ == "__main__":
    main()
