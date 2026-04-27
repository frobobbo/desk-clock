from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config_store import DisplayConfig, QuoteConfig


_CACHE: dict[tuple[str, str], QuoteConfig] = {}

_BIBLE_VERSES = [
    "John 3:16",
    "Romans 8:28",
    "Philippians 4:6-7",
    "Proverbs 3:5-6",
    "Isaiah 41:10",
    "Matthew 6:33",
    "Jeremiah 29:11",
]

_PSALM_READINGS = [
    "Psalm 23:1-2",
    "Psalm 46:10",
    "Psalm 118:24",
    "Psalm 27:1",
    "Psalm 121:1-2",
    "Psalm 19:14",
    "Psalm 91:1-2",
]


def resolve_display_content(display: DisplayConfig) -> DisplayConfig:
    resolved = display.model_copy(deep=True)
    if not resolved.quote.enabled:
        return resolved

    source = resolved.quote.source
    cache_key = (_today_key(), source)
    cached = _CACHE.get(cache_key)
    if cached:
        resolved.quote = cached.model_copy(deep=True)
        return resolved

    try:
        quote_config = _fetch_quote(source, resolved.quote)
    except (TimeoutError, URLError, ValueError, KeyError, TypeError, OSError):
        quote_config = resolved.quote

    _CACHE[cache_key] = quote_config.model_copy(deep=True)
    resolved.quote = quote_config
    return resolved


def _fetch_quote(source: str, fallback: QuoteConfig) -> QuoteConfig:
    if source == "daily_author_quote":
        return _fetch_zenquotes_today(fallback)
    if source == "daily_bible_verse":
        return _fetch_bible_reference(_daily_pick(_BIBLE_VERSES), "Daily Bible Verse", source, fallback)
    if source == "daily_psalm":
        return _fetch_bible_reference(_daily_pick(_PSALM_READINGS), "Daily Psalm", source, fallback)
    if source == "today_in_history":
        return _fetch_today_in_history(fallback)
    return fallback


def _fetch_zenquotes_today(fallback: QuoteConfig) -> QuoteConfig:
    data = _get_json("https://zenquotes.io/api/today")
    item = data[0]
    return QuoteConfig(
        enabled=fallback.enabled,
        source="daily_author_quote",
        title=fallback.title or "Daily Quote",
        text=_clean_text(item["q"]),
        author=_clean_text(item["a"]),
    )


def _fetch_bible_reference(reference: str, title: str, source: str, fallback: QuoteConfig) -> QuoteConfig:
    data = _get_json(f"https://bible-api.com/{quote(reference)}?translation=web")
    text = _clean_bible_text(data["text"])
    return QuoteConfig(
        enabled=fallback.enabled,
        source=source,
        title=fallback.title or title,
        text=text,
        author=_clean_text(data["reference"]),
    )


def _fetch_today_in_history(fallback: QuoteConfig) -> QuoteConfig:
    now = datetime.now(timezone.utc)
    url = "https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{:02d}/{:02d}".format(
        now.month,
        now.day,
    )
    data = _get_json(url)
    event = _daily_pick(data["events"])
    year = event.get("year")
    text = _clean_text(event["text"])
    return QuoteConfig(
        enabled=fallback.enabled,
        source="today_in_history",
        title=fallback.title or "Today in History",
        text=text,
        author=str(year) if year else "On this day",
    )


def _get_json(url: str) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "desk-clock-config/0.2.1 (https://github.com/frobobbo/desk-clock)",
        },
    )
    with urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _daily_pick(items: list[Any]) -> Any:
    if not items:
        raise ValueError("no provider items returned")
    return deepcopy(items[datetime.now(timezone.utc).timetuple().tm_yday % len(items)])


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _clean_bible_text(text: str) -> str:
    return _clean_text(" ".join(line.strip() for line in text.splitlines() if line.strip()))


def _clean_text(text: str) -> str:
    return " ".join(str(text).replace("\u201c", '"').replace("\u201d", '"').split())
