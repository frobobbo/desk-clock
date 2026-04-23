"""
Book-themed display layout for the Waveshare Pico e-Paper 7.5 B (800 x 480).

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
CONTENT_TOP = BORDER + 4 + TITLE_H + 4

TIME_RECT_X = BORDER + 4 + MARGIN
TIME_RECT_Y = CONTENT_TOP + 6
TIME_RECT_W = SPINE_X - TIME_RECT_X - MARGIN - 4
TIME_RECT_H = 76

TIME_DIGIT_W = 48
TIME_DIGIT_H = 62
TIME_DIGIT_T = 6
TIME_DIGIT_GAP = 5
TIME_COLON_W = 10

LEFT_CONTENT_X = BORDER + 4 + MARGIN
LEFT_CENTER_X = SPINE_X // 2
RIGHT_CONTENT_X = SPINE_X + 4 + MARGIN
RIGHT_CONTENT_W = W - BORDER - 4 - MARGIN - RIGHT_CONTENT_X

DATE_Y = CONTENT_TOP + 96
WEATHER_Y = CONTENT_TOP + 214

QUOTE_BODY_SCALE = 3
QUOTE_LINE_H = 30

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


def _line(epd, x0, y0, x1, y1, color=BLACK):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        epd.pixel(x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _quad_curve(epd, x0, y0, cx, cy, x1, y1, color=BLACK):
    last_x, last_y = x0, y0
    for i in range(1, 33):
        t_num = i
        inv = 32 - t_num
        x = (inv * inv * x0 + 2 * inv * t_num * cx + t_num * t_num * x1) // (32 * 32)
        y = (inv * inv * y0 + 2 * inv * t_num * cy + t_num * t_num * y1) // (32 * 32)
        _line(epd, last_x, last_y, x, y, color)
        last_x, last_y = x, y


def _draw_book_background(epd):
    cover_x, cover_y = 14, 18
    cover_w, cover_h = W - 28, H - 34
    page_top = 56
    page_bottom = 442
    gutter_x = SPINE_X

    # Outer cover and open-page silhouette.
    epd.rect(cover_x, cover_y, cover_w, cover_h, BLACK)
    epd.rect(cover_x + 3, cover_y + 3, cover_w - 6, cover_h - 6, BLACK)
    _quad_curve(epd, 34, page_top, 190, 42, gutter_x - 8, page_top + 8)
    _quad_curve(epd, gutter_x + 8, page_top + 8, 610, 42, 766, page_top)
    _quad_curve(epd, 34, page_bottom, 190, 456, gutter_x - 8, page_bottom - 8)
    _quad_curve(epd, gutter_x + 8, page_bottom - 8, 610, 456, 766, page_bottom)
    _line(epd, 34, page_top, 34, page_bottom)
    _line(epd, 766, page_top, 766, page_bottom)

    # Gutter and page depth.
    _quad_curve(epd, gutter_x - 9, page_top + 7, gutter_x - 20, 245, gutter_x - 8, page_bottom - 8)
    _quad_curve(epd, gutter_x + 9, page_top + 7, gutter_x + 20, 245, gutter_x + 8, page_bottom - 8)
    epd.vline(gutter_x, page_top + 12, page_bottom - page_top - 24, BLACK)

    # Subtle gutter shading and cover shadows. Keep this near the book edges so
    # the clock, weather, and quote remain clean on the e-paper panel.
    for x in (382, 386, 414, 418):
        for y in range(86, 424, 12):
            _line(epd, x, y, x - 5 if x < gutter_x else x + 5, y + 7)

    for x in range(22, 68, 9):
        _line(epd, x, 30, x - 8, 66)
        _line(epd, x, 414, x - 8, 448)
    for x in range(732, 778, 9):
        _line(epd, x, 30, x + 8, 66)
        _line(epd, x, 414, x + 8, 448)

    for offset in (8, 15, 22):
        _quad_curve(epd, 42, page_top + offset, 190, page_top + offset - 11,
                    gutter_x - 20, page_top + offset + 3)
        _quad_curve(epd, gutter_x + 20, page_top + offset + 3,
                    610, page_top + offset - 11, 758, page_top + offset)
        _quad_curve(epd, 42, page_bottom - offset, 190, page_bottom - offset + 11,
                    gutter_x - 20, page_bottom - offset - 3)
        _quad_curve(epd, gutter_x + 20, page_bottom - offset - 3,
                    610, page_bottom - offset + 11, 758, page_bottom - offset)

    for offset in (31, 39, 47):
        _quad_curve(epd, 52, page_top + offset, 195, page_top + offset - 9,
                    gutter_x - 32, page_top + offset + 2)
        _quad_curve(epd, gutter_x + 32, page_top + offset + 2,
                    605, page_top + offset - 9, 748, page_top + offset)
        _quad_curve(epd, 52, page_bottom - offset, 195, page_bottom - offset + 9,
                    gutter_x - 32, page_bottom - offset - 2)
        _quad_curve(epd, gutter_x + 32, page_bottom - offset - 2,
                    605, page_bottom - offset + 9, 748, page_bottom - offset)

    # Header, footer, and center division are part of the book art, not text.
    epd.hline(34, 58, 732, BLACK)
    epd.hline(34, 60, 732, BLACK)
    epd.hline(34, FOOTER_Y, 732, BLACK)
    epd.hline(34, FOOTER_Y + 2, 732, BLACK)
    epd.vline(gutter_x - 1, CONTENT_TOP, FOOTER_Y - CONTENT_TOP, BLACK)
    epd.vline(gutter_x + 1, CONTENT_TOP, FOOTER_Y - CONTENT_TOP, BLACK)


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


def _text_c(epd, text, cx, y, scale=1, color=BLACK):
    """Draw text horizontally centred on cx."""
    x = cx - len(text) * 8 * scale // 2
    epd.text_scaled(text, x, y, scale, color)


def _h_segment(epd, x, y, w, t, color=BLACK):
    mid = t // 2
    for dy in range(t):
        inset = abs(mid - dy)
        epd.hline(x + inset, y + dy, w - 2 * inset, color)


def _v_segment(epd, x, y, h, t, color=BLACK):
    mid = t // 2
    for dx in range(t):
        inset = abs(mid - dx)
        epd.vline(x + dx, y + inset, h - 2 * inset, color)


_DIGIT_SEGMENTS = {
    "0": "abcedf",
    "1": "bc",
    "2": "abged",
    "3": "abgcd",
    "4": "fgbc",
    "5": "afgcd",
    "6": "afgecd",
    "7": "abc",
    "8": "abcdefg",
    "9": "abfgcd",
}


def _draw_digit(epd, ch, x, y, color=BLACK):
    segs = _DIGIT_SEGMENTS[ch]
    w = TIME_DIGIT_W
    h = TIME_DIGIT_H
    t = TIME_DIGIT_T
    h_len = w - 2 * t
    v_len = h // 2 - t
    mid_y = y + h // 2 - t // 2
    lower_y = y + h // 2 + t // 2

    if "a" in segs:
        _h_segment(epd, x + t, y, h_len, t, color)
    if "b" in segs:
        _v_segment(epd, x + w - t, y + t, v_len, t, color)
    if "c" in segs:
        _v_segment(epd, x + w - t, lower_y, v_len, t, color)
    if "d" in segs:
        _h_segment(epd, x + t, y + h - t, h_len, t, color)
    if "e" in segs:
        _v_segment(epd, x, lower_y, v_len, t, color)
    if "f" in segs:
        _v_segment(epd, x, y + t, v_len, t, color)
    if "g" in segs:
        _h_segment(epd, x + t, mid_y, h_len, t, color)


def _draw_colon(epd, x, y, color=BLACK):
    dot = 5
    epd.fill_rect(x + 2, y + 14, dot, dot, color)
    epd.fill_rect(x + 2, y + 30, dot, dot, color)


def _draw_time_text(epd, text, cx, y, color=BLACK):
    width = 0
    for ch in text:
        if ch == ":":
            width += TIME_COLON_W
        else:
            width += TIME_DIGIT_W
        width += TIME_DIGIT_GAP
    width -= TIME_DIGIT_GAP

    x = cx - width // 2
    for ch in text:
        if ch == ":":
            _draw_colon(epd, x, y, color)
            x += TIME_COLON_W + TIME_DIGIT_GAP
        else:
            _draw_digit(epd, ch, x, y, color)
            x += TIME_DIGIT_W + TIME_DIGIT_GAP
    return x


def render_time(epd, hour, minute, time_format=12):
    """Redraw only the time area for black/white partial refresh."""
    lcx = LEFT_CENTER_X
    ty = CONTENT_TOP + 10

    epd.fill_rect(TIME_RECT_X, TIME_RECT_Y, TIME_RECT_W, TIME_RECT_H, WHITE)

    if time_format == 12:
        ampm = "AM" if hour < 12 else "PM"
        h12  = hour % 12
        if h12 == 0:
            h12 = 12
        time_str = "{}:{:02d}".format(h12, minute)
    else:
        ampm = ""
        time_str = "{:02d}:{:02d}".format(hour, minute)

    time_right = _draw_time_text(epd, time_str, lcx - 20, ty, BLACK)

    if ampm:
        epd.text_scaled(ampm, time_right + 8, ty + 23, scale=2, color=BLACK)


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

    _draw_book_background(epd)

    # ── title bar ───────────────────────────────────────────────────────────────
    title = "-* THE DAILY CHRONICLE *-"
    _text_c(epd, title, W // 2, BORDER + 10, scale=2, color=BLACK)

    # ── footer ───────────────────────────────────────────────────────────────────
    epd.text_scaled("~ i ~",  BORDER + MARGIN,      FOOTER_Y + 5, 1, BLACK)
    epd.text_scaled("~ ii ~", SPINE_X + MARGIN + 2, FOOTER_Y + 5, 1, BLACK)

    # ── LEFT PAGE ────────────────────────────────────────────────────────────────
    lx = LEFT_CONTENT_X                    # left content start
    lcx = LEFT_CENTER_X                    # left page centre x

    # Time
    render_time(epd, hour, minute, time_format)

    # Day & date
    day_str  = DAYS[weekday].upper()
    date_str = "{} {}, {}".format(MONTHS[month - 1], day, year)
    _text_c(epd, day_str,  lcx, DATE_Y,      scale=3)
    _text_c(epd, date_str, lcx, DATE_Y + 28, scale=2)

    # Divider
    DIV_Y = CONTENT_TOP + 194
    epd.hline(lx, DIV_Y, SPINE_X - lx - MARGIN, BLACK)

    # Weather icon + info
    WY = WEATHER_Y
    icon_fn = _ICONS.get(icon_key, _icon_cloud)
    icon_fn(epd, lx + 8, WY)

    info_x = lx + 82
    epd.text_scaled("{} \xf8{}".format(temp, unit), info_x, WY + 2,  scale=4)
    epd.text_scaled(condition,                       info_x, WY + 42, scale=2)
    epd.text_scaled("Humidity {}%".format(humidity), info_x, WY + 70, scale=2)
    epd.text_scaled("Wind {} mph {}".format(wind_speed, wind_dir),
                    info_x, WY + 92, scale=2)

    # ── RIGHT PAGE ───────────────────────────────────────────────────────────────
    rx  = RIGHT_CONTENT_X
    rcx = SPINE_X + (W - SPINE_X) // 2

    _text_c(epd, "~ Quote of the Day ~", rcx, CONTENT_TOP + 10, scale=2, color=BLACK)

    QDY = CONTENT_TOP + 34
    epd.hline(rx, QDY, RIGHT_CONTENT_W, BLACK)

    # Large decorative opening quote mark
    epd.text_scaled('"', rx, QDY + 12, scale=5, color=BLACK)

    # Wrap and render quote body
    chars_per_line = RIGHT_CONTENT_W // (8 * QUOTE_BODY_SCALE)
    lines = _wrap(quote, chars_per_line)

    QTY = QDY + 58
    max_lines = (FOOTER_Y - 58 - QTY) // QUOTE_LINE_H

    for i, line in enumerate(lines[:max_lines]):
        epd.text_scaled(line, rx + 8, QTY + i * QUOTE_LINE_H,
                        scale=QUOTE_BODY_SCALE, color=BLACK)

    # Attribution
    attr = "- " + author
    attr_x = W - BORDER - 4 - MARGIN - len(attr) * 8 * 2
    epd.text_scaled(attr, attr_x, FOOTER_Y - 22, scale=2, color=BLACK)
