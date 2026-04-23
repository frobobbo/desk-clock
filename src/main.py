"""
Desk Clock — main application
Hardware: Raspberry Pi Pico 2 W + Waveshare Pico e-Paper 7.5 B (800×480, B/W/Red)
"""

import time
import network
import ntptime
from machine import SPI, Pin

import config
import display_manager as dm
import weather
import quotes
from lib.epd7in5b import EPD7in5B

# ── hardware init ───────────────────────────────────────────────────────────────

def build_epd():
    spi  = SPI(1, baudrate=4_000_000, sck=Pin(config.EPD_SCK_PIN),
               mosi=Pin(config.EPD_MOSI_PIN))
    cs   = Pin(config.EPD_CS_PIN,   Pin.OUT, value=1)
    dc   = Pin(config.EPD_DC_PIN,   Pin.OUT)
    rst  = Pin(config.EPD_RST_PIN,  Pin.OUT)
    busy = Pin(config.EPD_BUSY_PIN, Pin.IN)
    return EPD7in5B(
        spi,
        cs,
        dc,
        rst,
        busy,
        busy_active=config.EPD_BUSY_ACTIVE,
        busy_timeout_ms=config.EPD_BUSY_TIMEOUT_MS,
    )


# ── WiFi ────────────────────────────────────────────────────────────────────────

def wifi_connect(timeout=20):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    for _ in range(timeout * 10):
        if wlan.isconnected():
            print("WiFi connected:", wlan.ifconfig()[0])
            return True
        time.sleep_ms(100)
    print("WiFi connection failed")
    return False


# ── time helpers ────────────────────────────────────────────────────────────────

def local_now():
    """Return local time using the Pico's RTC plus configured timezone offset."""
    utc = time.time()
    offset = int((config.TIMEZONE_OFFSET + config.DST_OFFSET) * 3600)
    return time.localtime(utc + offset)


def sync_time_from_ntp():
    """Sync the Pico's internal RTC from NTP."""
    try:
        ntptime.host = config.NTP_HOST
        ntptime.settime()                           # sets internal RTC to UTC
        local = local_now()
        print("Time synced: {}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*local))
        return True
    except Exception as e:
        print("NTP sync failed:", e)
        return False


# ── display splash ───────────────────────────────────────────────────────────────

def show_splash(epd):
    epd.fill(1)
    epd.text_scaled("THE DAILY CHRONICLE", 220, 200, scale=3, color=0)
    epd.text_scaled("Initialising...",     300, 250, scale=2, color=0)
    epd.display()


# ── main loop ────────────────────────────────────────────────────────────────────

def main():
    print("Booting desk clock...")

    epd = build_epd()
    print("EPD init start; BUSY pin =", epd.busy.value())
    epd.init()
    print("EPD init done; BUSY pin =", epd.busy.value())
    print("Clearing panel...")
    epd.clear()
    print("Drawing splash...")
    show_splash(epd)
    print("Splash drawn")

    # WiFi + NTP
    online = wifi_connect()
    if online:
        sync_time_from_ntp()

    # Initial data fetch
    wx     = weather.fetch(config.LATITUDE, config.LONGITUDE, config.TEMP_UNIT) \
             if online else weather._PLACEHOLDER
    q_text, q_author = quotes.fetch() if online else quotes._FALLBACK[0]

    last_weather_min = -config.WEATHER_REFRESH_MINUTES  # force first fetch
    last_quote_hour  = -config.QUOTE_REFRESH_HOURS      # force first fetch
    last_minute      = -1
    last_day         = -1
    partial_count    = 0

    while True:
        dt = local_now()
        year, month, day, hour, minute, second, weekday = dt[:7]

        # Elapsed counters (approximate, good enough for a clock)
        elapsed_min = hour * 60 + minute

        # Periodic WiFi re-fetch
        data_changed = False
        if online:
            mins_since_wx = (elapsed_min - last_weather_min) % (24 * 60)
            if mins_since_wx >= config.WEATHER_REFRESH_MINUTES:
                wx = weather.fetch(config.LATITUDE, config.LONGITUDE,
                                   config.TEMP_UNIT)
                last_weather_min = elapsed_min
                data_changed = True

            hrs_since_q = (hour - last_quote_hour) % 24
            if hrs_since_q >= config.QUOTE_REFRESH_HOURS:
                q_text, q_author = quotes.fetch()
                last_quote_hour = hour
                data_changed = True

        # Redraw once per minute
        if minute != last_minute:
            force_full = (
                not config.USE_PARTIAL_REFRESH or
                last_minute < 0 or
                day != last_day or
                data_changed or
                (
                    config.FULL_REFRESH_AFTER_PARTIALS > 0 and
                    partial_count >= config.FULL_REFRESH_AFTER_PARTIALS
                )
            )

            if force_full:
                print("Full display update {:02d}:{:02d}".format(hour, minute))
                epd.init()
                dm.render(
                    epd,
                    year, month, day, hour, minute, weekday,
                    wx["temp"], wx["unit"], wx["condition"], wx["icon"],
                    wx["humidity"], wx["wind_speed"], wx["wind_dir"],
                    q_text, q_author,
                    config.TIME_FORMAT,
                )
                epd.display()
                if config.USE_PARTIAL_REFRESH:
                    epd.init_partial()
                partial_count = 0
            else:
                print("Partial time update {:02d}:{:02d}".format(hour, minute))
                dm.render_time(epd, hour, minute, config.TIME_FORMAT)
                epd.display_partial()
                partial_count += 1

            last_minute = minute
            last_day = day

        # Sleep until ~5s before next minute tick to avoid drift
        sleep_s = 55 - second if second < 55 else 5
        time.sleep(max(1, sleep_s))


main()
