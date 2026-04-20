"""
Desk Clock — main application
Hardware: Raspberry Pi Pico 2 W + DS3231 RTC + Waveshare 4.26" e-Paper HAT
"""

import time
import network
import ntptime
from machine import I2C, SPI, Pin

import config
import display_manager as dm
import weather
import quotes
from lib.epd4in26 import EPD4in26
from lib.ds3231   import DS3231

# ── hardware init ───────────────────────────────────────────────────────────────

def build_epd():
    spi  = SPI(1, baudrate=4_000_000, sck=Pin(config.EPD_SCK_PIN),
               mosi=Pin(config.EPD_MOSI_PIN))
    cs   = Pin(config.EPD_CS_PIN,   Pin.OUT)
    dc   = Pin(config.EPD_DC_PIN,   Pin.OUT)
    rst  = Pin(config.EPD_RST_PIN,  Pin.OUT)
    busy = Pin(config.EPD_BUSY_PIN, Pin.IN)
    return EPD4in26(spi, cs, dc, rst, busy)


def build_rtc():
    i2c = I2C(0, sda=Pin(config.I2C_SDA_PIN), scl=Pin(config.I2C_SCL_PIN),
              freq=400_000)
    return DS3231(i2c)


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


# ── NTP sync ────────────────────────────────────────────────────────────────────

def sync_rtc_from_ntp(rtc):
    """Sync DS3231 from NTP.  Applies timezone + DST offset from config."""
    try:
        ntptime.settime()                           # sets internal RTC to UTC
        utc     = time.time()
        offset  = int((config.TIMEZONE_OFFSET + config.DST_OFFSET) * 3600)
        local   = time.localtime(utc + offset)
        # local = (year, month, mday, hour, minute, second, weekday, yearday)
        rtc.set_datetime(local[0], local[1], local[2],
                         local[3], local[4], local[5],
                         local[6])
        print("RTC synced: {}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*local))
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
    epd.init()
    show_splash(epd)

    rtc = build_rtc()

    # WiFi + NTP
    online = wifi_connect()
    if online:
        sync_rtc_from_ntp(rtc)

    # Initial data fetch
    wx     = weather.fetch(config.LATITUDE, config.LONGITUDE, config.TEMP_UNIT) \
             if online else weather._PLACEHOLDER
    q_text, q_author = quotes.fetch() if online else quotes._FALLBACK[0]

    last_weather_min = -config.WEATHER_REFRESH_MINUTES  # force first fetch
    last_quote_hour  = -config.QUOTE_REFRESH_HOURS      # force first fetch
    last_minute      = -1

    while True:
        dt = rtc.get_datetime()          # (year, month, day, hour, min, sec, wday)
        year, month, day, hour, minute, second, weekday = dt

        # Elapsed counters (approximate, good enough for a clock)
        elapsed_min = hour * 60 + minute

        # Periodic WiFi re-fetch
        if online:
            mins_since_wx = (elapsed_min - last_weather_min) % (24 * 60)
            if mins_since_wx >= config.WEATHER_REFRESH_MINUTES:
                wx = weather.fetch(config.LATITUDE, config.LONGITUDE,
                                   config.TEMP_UNIT)
                last_weather_min = elapsed_min

            hrs_since_q = (hour - last_quote_hour) % 24
            if hrs_since_q >= config.QUOTE_REFRESH_HOURS:
                q_text, q_author = quotes.fetch()
                last_quote_hour = hour

        # Redraw once per minute
        if minute != last_minute:
            print("Updating display {:02d}:{:02d}".format(hour, minute))
            dm.render(
                epd,
                year, month, day, hour, minute, weekday,
                wx["temp"], wx["unit"], wx["condition"], wx["icon"],
                wx["humidity"], wx["wind_speed"], wx["wind_dir"],
                q_text, q_author,
                config.TIME_FORMAT,
            )
            epd.display()
            last_minute = minute

        # Sleep until ~5s before next minute tick to avoid drift
        sleep_s = 55 - second if second < 55 else 5
        time.sleep(max(1, sleep_s))


main()
