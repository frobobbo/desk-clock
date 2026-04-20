"""
Weather data via Open-Meteo (free, no API key required).
https://open-meteo.com/
"""

import urequests
import ujson

_BASE = "https://api.open-meteo.com/v1/forecast"

# WMO weather code → (description, icon_key)
_WMO_MAP = {
    0:  ("Clear Sky",      "sun"),
    1:  ("Mainly Clear",   "sun"),
    2:  ("Partly Cloudy",  "partly_cloudy"),
    3:  ("Overcast",       "cloud"),
    45: ("Fog",            "fog"),
    48: ("Rime Fog",       "fog"),
    51: ("Light Drizzle",  "drizzle"),
    53: ("Drizzle",        "drizzle"),
    55: ("Heavy Drizzle",  "drizzle"),
    61: ("Light Rain",     "rain"),
    63: ("Rain",           "rain"),
    65: ("Heavy Rain",     "rain"),
    71: ("Light Snow",     "snow"),
    73: ("Snow",           "snow"),
    75: ("Heavy Snow",     "snow"),
    77: ("Snow Grains",    "snow"),
    80: ("Rain Showers",   "rain"),
    81: ("Rain Showers",   "rain"),
    82: ("Violent Showers","rain"),
    85: ("Snow Showers",   "snow"),
    86: ("Heavy Snow Showers","snow"),
    95: ("Thunderstorm",   "thunder"),
    96: ("Thunderstorm",   "thunder"),
    99: ("Thunderstorm",   "thunder"),
}

_PLACEHOLDER = {
    "temp": "--",
    "unit": "F",
    "condition": "Unavailable",
    "icon": "cloud",
    "humidity": "--",
    "wind_speed": "--",
    "wind_dir": "",
}


def _wind_dir(deg):
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[round(deg / 45) % 8]


def fetch(lat, lon, unit="fahrenheit"):
    url = (
        "{}?latitude={}&longitude={}"
        "&current=temperature_2m,relative_humidity_2m,"
        "weather_code,wind_speed_10m,wind_direction_10m"
        "&temperature_unit={}&wind_speed_unit=mph"
    ).format(_BASE, lat, lon, unit)

    try:
        r = urequests.get(url, timeout=10)
        data = ujson.loads(r.text)
        r.close()

        cur  = data["current"]
        code = cur.get("weather_code", 0)
        desc, icon = _WMO_MAP.get(code, ("Unknown", "cloud"))
        unit_sym = "F" if unit == "fahrenheit" else "C"

        return {
            "temp":      str(round(cur["temperature_2m"])),
            "unit":      unit_sym,
            "condition": desc,
            "icon":      icon,
            "humidity":  str(cur.get("relative_humidity_2m", "--")),
            "wind_speed":str(round(cur.get("wind_speed_10m", 0))),
            "wind_dir":  _wind_dir(cur.get("wind_direction_10m", 0)),
        }
    except Exception as e:
        print("Weather fetch error:", e)
        return _PLACEHOLDER
