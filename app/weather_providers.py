from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config_store import WeatherConfig

_CACHE: dict[str, WeatherConfig] = {}


def resolve_weather(weather: WeatherConfig) -> WeatherConfig:
    if not weather.enabled or not weather.location_label.strip():
        return weather

    cache_key = _cache_key(weather.location_label)
    cached = _CACHE.get(cache_key)
    if cached:
        return cached.model_copy(deep=True)

    try:
        resolved = _fetch_weather(weather)
    except (TimeoutError, URLError, ValueError, KeyError, TypeError, OSError):
        return weather

    _CACHE[cache_key] = resolved.model_copy(deep=True)
    return resolved


def _fetch_weather(weather: WeatherConfig) -> WeatherConfig:
    data = _get_json(f"https://wttr.in/{quote(weather.location_label)}?format=j1")
    current = data["current_condition"][0]
    today = data["weather"][0]
    return WeatherConfig(
        enabled=weather.enabled,
        location_label=weather.location_label,
        temperature=f"{current['temp_F']}F",
        temp_high=f"{today['maxtempF']}F",
        temp_low=f"{today['mintempF']}F",
        condition=current["weatherDesc"][0]["value"],
        humidity=f"{current['humidity']}%",
        wind=f"{current['windspeedMiles']} mph",
    )


def _cache_key(location: str) -> str:
    now = datetime.now(timezone.utc)
    half_hour = "00" if now.minute < 30 else "30"
    return now.strftime("%Y-%m-%d-%H") + f":{half_hour}:{location}"


def _get_json(url: str) -> Any:
    req = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "desk-clock-config/0.2.6 (https://github.com/frobobbo/desk-clock)",
    })
    with urlopen(req, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))
