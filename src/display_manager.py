"""
Book-themed display layout for the Waveshare 4.26" e-Paper (800 x 480).

┌────────────────────────────────────────────────────────────────────────────────┐
│  ╔══════════════════════════════════════════════════════════════════════════╗  │
│  ║               ✦  THE  DAILY  CHRONICLE  ✦                               ║  │
│  ╠══════════════════════════════════════╦═════════════════════════════════  ║  │
│  ║                                      ║                                   ║  │
│  ║         10:42  PM                    ║   ~ Quote of the Day ~            ║  │
│  ║        Wednesday                     ║  ─────────────────────            ║  │
│  ║      April 20, 2026                  ║                                   ║  │
│  ║  ───────────────────────             ║   "The only way to do great       ║  │
│  ║   ☀  72°F  Partly Cloudy            ║    work is to love what you do."  ║  │
│  ║      Humidity 45%  Wind 8mph N       ║                                   ║  │
│  ║                                      ║            — Steve Jobs           ║  │
│  ╚══════════════════════════════════════╩═════════════════════════════════  ╝  │
└────────────────────────────────────────────────────────────────────────────────┘

Coordinate system:  (0,0) = top-left
"""

import math

# ── layout constants ────────────────────────────────────────────────────────────
W, H = 800, 480
SPINE_X   = 400
TITLE_H   = 50            # height of title bar
BORDER    = 4             # outer/inner border line inset
FOOTER_Y  = 462
MARGIN    = 18            # per-page inner margin

BLACK, WHITE = 0, 1

DAYS   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]


# ── drawing helpers ─────────────────────────────────────────────────────────────

def _filled_circle(epd, cx, cy, r):
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(r * r - dy * dy))
        epd.hline(cx - dx, cy + dy, 2 * dx + 1, BLACK)


def _circle(epd, cx, cy, r):
    x, y, d = 0, r, 1 - r
    while x <= y:
        for px, py in [(cx+x,cy+y),(cx-x,cy+y),(cx+x,cy-y),(cx-x,cy-y),
                       (cx+y,cy+x),(cx-y,cy+x),(cx+y,cy-x),(cx-y,cy-x)]:
            if 0 <= px < W and 0 <= py < H:
                epd.pixel(px, py, BLACK)
        d = d + 2*x + 3 if d < 0 else d + 2*(x-y) + 5
        if d >= 0:
            y -= 1
        x += 1


def _wrap(text, max_chars):
    words = text.split(' ')
    lines, line = [], ''
    for w in words:
        if len(line) + len(w) + (1 if line else 0) <= max_chars:
            line += (' ' if line else '') + w
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def _text_c(epd, text, cx, y, scale=1):
    """Draw text horizontally centred on cx."""
    x = cx - len(text) * 8 * scale // 2
    epd.text_scaled(text, x, y, scale, BLACK)


# ── weather icons (60 × 60, top-left at ox,oy) ─────────────────────────────────

def _icon_sun(epd, ox, oy):
    cx, cy, r = ox + 30, oy + 30, 13
    _filled_circle(epd, cx, cy, r)
    for ang in range(0, 360, 45):
        rad = math.radians(ang)
        for d in range(18, 26):
            epd.pixel(cx + int(d * math.cos(rad)),
                      cy + int(d * math.sin(rad)), BLACK)


def _icon_cloud(epd, ox, oy):
    for cx2, cy2, r2 in [(ox+20,oy+38,13),(ox+35,oy+32,18),(ox+50,oy+38,13)]:
        _filled_circle(epd, cx2, cy2, r2)
    epd.fill_rect(ox+7, oy+38, 46, 13, WHITE)   # flatten the bottom


def _icon_partly_cloudy(epd, ox, oy):
    _icon_sun(epd, ox, oy - 8)
    # small cloud over sun bottom-right
    for cx2, cy2, r2 in [(ox+30,oy+44,10),(ox+42,oy+40,13),(ox+52,oy+44,9)]:
        _filled_circle(epd, cx2, cy2, r2)
    epd.fill_rect(ox+20, oy+44, 42, 10, WHITE)


def _icon_rain(epd, ox, oy):
    _icon_cloud(epd, ox, oy - 5)
    for i in range(4):
        epd.fill_rect(ox + 12 + i * 12, oy + 50, 2, 8, BLACK)


def _icon_snow(epd, ox, oy):
    _icon_cloud(epd, ox, oy - 5)
    for i in range(4):
        ex = ox + 12 + i * 12
        epd.fill_rect(ex, oy + 50, 2, 8, BLACK)
        epd.fill_rect(ex - 3, oy + 54, 8, 2, BLACK)


def _icon_thunder(epd, ox, oy):
    _icon_cloud(epd, ox, oy - 5)
    bolt = [(ox+32,oy+50),(ox+26,oy+58),(ox+30,oy+58),(ox+24,oy+68),(ox+38,oy+56),(ox+34,oy+56)]
    for i in range(len(bolt) - 1):
        x0, y0 = bolt[i]; x1, y1 = bolt[i+1]
        dx, dy = x1-x0, y1-y0
        steps = max(abs(dx), abs(dy))
        for s in range(steps + 1):
            epd.pixel(x0 + dx*s//steps, y0 + dy*s//steps, BLACK)


def _icon_fog(epd, ox, oy):
    for row in range(5):
        epd.hline(ox + 5, oy + 20 + row * 9, 50, BLACK)
        epd.hline(ox + 5, oy + 21 + row * 9, 50, BLACK)


_ICONS = {
    "sun":           _icon_sun,
    "cloud":         _icon_cloud,
    "partly_cloudy": _icon_partly_cloudy,
    "rain":          _icon_rain,
    "drizzle":       _icon_rain,
    "snow":          _icon_snow,
    "thunder":       _icon_thunder,
    "fog":           _icon_fog,
}


# ── main renderer ───────────────────────────────────────────────────────────────

def render(epd, year, month, day, hour, minute, weekday,
           temp, unit, condition, icon_key, humidity, wind_speed, wind_dir,
           quote, author, time_format=12):

    epd.fill(WHITE)

    # ── outer double border ──────────────────────────────────────────────────────
    epd.rect(BORDER,     BORDER,     W - 2*BORDER,     H - 2*BORDER,     BLACK)
    epd.rect(BORDER + 4, BORDER + 4, W - 2*(BORDER+4), H - 2*(BORDER+4), BLACK)

    # ── title bar ───────────────────────────────────────────────────────────────
    title = "-* THE DAILY CHRONICLE *-"
    _text_c(epd, title, W // 2, BORDER + 10, scale=2)

    ty = BORDER + 4 + TITLE_H
    epd.hline(BORDER + 4, ty,     W - 2*(BORDER+4), BLACK)
    epd.hline(BORDER + 4, ty + 2, W - 2*(BORDER+4), BLACK)

    CONTENT_TOP = ty + 4

    # ── spine ───────────────────────────────────────────────────────────────────
    epd.vline(SPINE_X, CONTENT_TOP, FOOTER_Y - CONTENT_TOP, BLACK)
    epd.vline(SPINE_X + 2, CONTENT_TOP, FOOTER_Y - CONTENT_TOP, BLACK)

    # ── footer ───────────────────────────────────────────────────────────────────
    epd.hline(BORDER + 4, FOOTER_Y,     W - 2*(BORDER+4), BLACK)
    epd.hline(BORDER + 4, FOOTER_Y + 2, W - 2*(BORDER+4), BLACK)
    epd.text_scaled("~ i ~",  BORDER + MARGIN,      FOOTER_Y + 5, 1, BLACK)
    epd.text_scaled("~ ii ~", SPINE_X + MARGIN + 2, FOOTER_Y + 5, 1, BLACK)

    # ── LEFT PAGE ────────────────────────────────────────────────────────────────
    lx = BORDER + 4 + MARGIN               # left content start
    lcx = (SPINE_X) // 2                   # left page centre x

    # Time
    if time_format == 12:
        ampm = "AM" if hour < 12 else "PM"
        h12  = hour % 12
        if h12 == 0: h12 = 12
        time_str = "{}:{:02d}".format(h12, minute)
    else:
        ampm = ""
        time_str = "{:02d}:{:02d}".format(hour, minute)

    TY = CONTENT_TOP + 12
    _text_c(epd, time_str, lcx - 20, TY, scale=6)

    if ampm:
        tx_end = lcx - 20 + len(time_str) * 8 * 6 // 2 + 10
        epd.text_scaled(ampm, tx_end, TY + 14, scale=3, color=BLACK)

    # Day & date
    day_str  = DAYS[weekday].upper()
    date_str = "{} {}, {}".format(MONTHS[month - 1], day, year)
    DY = TY + 48 + 12
    _text_c(epd, day_str,  lcx, DY,      scale=3)
    _text_c(epd, date_str, lcx, DY + 28, scale=2)

    # Divider
    DIV_Y = DY + 52
    epd.hline(lx, DIV_Y, SPINE_X - lx - MARGIN, BLACK)

    # Weather icon + info
    WY = DIV_Y + 10
    icon_fn = _ICONS.get(icon_key, _icon_cloud)
    icon_fn(epd, lx, WY)

    info_x = lx + 68
    epd.text_scaled("{} \xf8{}".format(temp, unit), info_x, WY + 4,  scale=4)
    epd.text_scaled(condition,                       info_x, WY + 42, scale=2)
    epd.text_scaled("Humidity {}%".format(humidity), info_x, WY + 64, scale=2)
    epd.text_scaled("Wind {} mph {}".format(wind_speed, wind_dir),
                    info_x, WY + 84, scale=2)

    # ── RIGHT PAGE ───────────────────────────────────────────────────────────────
    rx  = SPINE_X + 4 + MARGIN
    rcx = SPINE_X + (W - SPINE_X) // 2

    _text_c(epd, "~ Quote of the Day ~", rcx, CONTENT_TOP + 10, scale=2)

    QDY = CONTENT_TOP + 34
    epd.hline(rx, QDY, W - BORDER - 4 - MARGIN - rx, BLACK)

    # Large decorative opening quote mark
    epd.text_scaled('"', rx, QDY + 6, scale=4, color=BLACK)

    # Wrap and render quote body
    page_w = W - BORDER - 4 - MARGIN - rx
    chars_per_line = page_w // (8 * 2)     # scale=2 → 16px per char
    lines = _wrap(quote, chars_per_line)

    QTY = QDY + 42
    LINE_H = 20
    max_lines = (FOOTER_Y - 48 - QTY) // LINE_H

    for i, line in enumerate(lines[:max_lines]):
        epd.text_scaled(line, rx + 4, QTY + i * LINE_H, scale=2, color=BLACK)

    # Attribution
    attr = "- " + author
    attr_x = W - BORDER - 4 - MARGIN - len(attr) * 8 * 2
    epd.text_scaled(attr, attr_x, FOOTER_Y - 22, scale=2, color=BLACK)
