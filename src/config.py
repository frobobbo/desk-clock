# WiFi credentials
WIFI_SSID = "Johnsons.iot"
WIFI_PASSWORD = "Cstone01"

# Location for weather (decimal degrees)
LATITUDE = 42.6875   # Default: New York City
LONGITUDE = -83.2341

# Temperature unit: "fahrenheit" or "celsius"
TEMP_UNIT = "fahrenheit"

# Time format: 12 or 24
TIME_FORMAT = 12

# Timezone offset from UTC in hours (can be fractional, e.g. 5.5 for IST)
# Examples: -5=EST, -6=CST, -7=MST, -8=PST, +0=UTC, +1=CET
TIMEZONE_OFFSET = -5

# Additional offset for daylight saving time (0 or 1)
DST_OFFSET = 1

# Refresh intervals
WEATHER_REFRESH_MINUTES = 30
QUOTE_REFRESH_HOURS = 24

# The clock face is black/white only so the 7.5" B panel's black/white partial
# refresh path can be used for minute updates.
USE_PARTIAL_REFRESH = True

# If partial refresh is enabled, force a full refresh after this many partials.
# Set to 0 to disable forced cleanup.
FULL_REFRESH_AFTER_PARTIALS = 10

# NTP server
NTP_HOST = "pool.ntp.org"

# Pin assignments — Waveshare Pico e-Paper 7.5 B (plug-in board, same header as 4.26")
EPD_SCK_PIN  = 10   # SPI1 SCK
EPD_MOSI_PIN = 11   # SPI1 TX (MOSI)
EPD_CS_PIN   = 9
EPD_DC_PIN   = 8
EPD_RST_PIN  = 12
EPD_BUSY_PIN = 13

# Waveshare Pico e-Paper boards invert BUSY: pin reads 0 while the panel
# is refreshing, 1 when idle.  Flip to 1 if the display hangs on init.
EPD_BUSY_ACTIVE = 0

# 7.5" tri-color panels can take up to ~35 s per refresh; 60 s gives headroom.
EPD_BUSY_TIMEOUT_MS = 60000
