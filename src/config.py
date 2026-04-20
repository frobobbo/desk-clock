# WiFi credentials
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"

# Location for weather (decimal degrees)
LATITUDE = 40.7128   # Default: New York City
LONGITUDE = -74.0060

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

# NTP server
NTP_HOST = "pool.ntp.org"

# Pin assignments — Waveshare 4.26" e-Paper
EPD_SCK_PIN  = 10   # SPI1 SCK
EPD_MOSI_PIN = 11   # SPI1 TX (MOSI)
EPD_CS_PIN   = 9
EPD_DC_PIN   = 8
EPD_RST_PIN  = 12
EPD_BUSY_PIN = 13

# Pin assignments — DS3231 RTC
I2C_SDA_PIN = 4     # I2C0 SDA
I2C_SCL_PIN = 5     # I2C0 SCL
