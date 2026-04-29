from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any
from urllib.error import URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .config_store import DisplayConfig, QuoteConfig, SettingsConfig
from .literature_providers import resolve_literature_event
from .time_utils import now
from .weather_providers import resolve_weather


_CACHE: dict[tuple[str, str, str, str], QuoteConfig] = {}
ESV_API_URL = "https://api.esv.org/v3/passage/text/"

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

_LITERATURE_QUOTES = [
    {
        "text": "There is no charm equal to tenderness of heart.",
        "author": "Jane Austen, Emma",
    },
    {
        "text": "We are such stuff as dreams are made on.",
        "author": "William Shakespeare, The Tempest",
    },
    {
        "text": "Whatever our souls are made of, his and mine are the same.",
        "author": "Emily Bronte, Wuthering Heights",
    },
    {
        "text": "It is nothing to die; it is dreadful not to live.",
        "author": "Victor Hugo, Les Miserables",
    },
    {
        "text": "The world is full of obvious things which nobody by any chance ever observes.",
        "author": "Arthur Conan Doyle, The Hound of the Baskervilles",
    },
    {
        "text": "I am no bird; and no net ensnares me.",
        "author": "Charlotte Bronte, Jane Eyre",
    },
    {
        "text": "And now that you don't have to be perfect, you can be good.",
        "author": "John Steinbeck, East of Eden",
    },
]


def resolve_display_content(display: DisplayConfig, settings: SettingsConfig | None = None) -> DisplayConfig:
    resolved = display.model_copy(deep=True)
    if resolved.weather.enabled:
        resolved.weather = resolve_weather(resolved.weather)
    if resolved.quote.enabled:
        resolved.quote = resolve_quote(resolved.quote, settings)
    if resolved.upper.enabled:
        resolved.upper = resolve_quote(resolved.upper, settings)
    if resolved.lower.enabled:
        resolved.lower = resolve_quote(resolved.lower, settings)
    return resolved


def resolve_quote(quote: QuoteConfig, settings: SettingsConfig | None = None) -> QuoteConfig:
    esv_api_key = _esv_api_key(settings)
    cache_key = (_today_key(), quote.source, quote.title, esv_api_key)
    cached = _CACHE.get(cache_key)
    if cached:
        return cached.model_copy(deep=True)

    try:
        quote_config = _fetch_quote(quote.source, quote, settings)
    except (TimeoutError, URLError, ValueError, KeyError, TypeError, OSError):
        quote_config = quote

    _CACHE[cache_key] = quote_config.model_copy(deep=True)
    return quote_config


def _fetch_quote(source: str, fallback: QuoteConfig, settings: SettingsConfig | None = None) -> QuoteConfig:
    if source == "daily_author_quote":
        return _fetch_zenquotes_today(fallback)
    if source == "quotes_from_literature":
        return _fetch_literature_quote(fallback)
    if source == "daily_bible_verse":
        return _fetch_bible_reference(_daily_pick(_BIBLE_VERSES), "Daily Bible Verse", source, fallback)
    if source == "daily_psalm":
        return _fetch_daily_psalm(fallback, settings)
    if source == "today_in_history":
        return _fetch_today_in_history(fallback)
    if source == "on_this_day_literature":
        return QuoteConfig(
            enabled=fallback.enabled,
            source="on_this_day_literature",
            title=fallback.title or "On This Day in Literature",
            text=resolve_literature_event(),
            author=fallback.author,
        )
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


def _fetch_literature_quote(fallback: QuoteConfig) -> QuoteConfig:
    item = _daily_pick(_LITERATURE_QUOTES)
    return QuoteConfig(
        enabled=fallback.enabled,
        source="quotes_from_literature",
        title=fallback.title or "Quotes from Literature",
        text=_clean_text(item["text"]),
        author=_clean_text(item["author"]),
    )


def _fetch_bible_reference(reference: str, title: str, source: str, fallback: QuoteConfig) -> QuoteConfig:
    data = _get_json(f"https://bible-api.com/{quote(reference)}?translation=kjv")
    text = _clean_bible_text(data["text"])
    return QuoteConfig(
        enabled=fallback.enabled,
        source=source,
        title=fallback.title or title,
        text=text,
        author=_clean_text(data["reference"]),
    )


def _fetch_daily_psalm(fallback: QuoteConfig, settings: SettingsConfig | None = None) -> QuoteConfig:
    reference = _daily_pick(_PSALM_READINGS)
    esv_api_key = _esv_api_key(settings)
    if esv_api_key:
        try:
            return _fetch_esv_reference(reference, "Daily Psalm", "daily_psalm", fallback, esv_api_key)
        except (TimeoutError, URLError, ValueError, KeyError, TypeError, OSError):
            pass
    return _fetch_bible_reference(reference, "Daily Psalm", "daily_psalm", fallback)


def _esv_api_key(settings: SettingsConfig | None = None) -> str:
    if settings and settings.esv_api_key:
        return settings.esv_api_key.strip()
    return os.getenv("ESV_API_KEY", "").strip()


def _fetch_esv_reference(reference: str, title: str, source: str, fallback: QuoteConfig, api_key: str) -> QuoteConfig:
    params = urlencode(
        {
            "q": reference,
            "include-passage-references": "false",
            "include-verse-numbers": "false",
            "include-first-verse-numbers": "false",
            "include-footnotes": "false",
            "include-footnote-body": "false",
            "include-headings": "false",
            "include-short-copyright": "true",
            "include-copyright": "false",
            "include-passage-horizontal-lines": "false",
            "include-heading-horizontal-lines": "false",
            "include-selahs": "true",
            "indent-poetry": "false",
            "line-length": "0",
        }
    )
    data = _get_json(
        f"{ESV_API_URL}?{params}",
        headers={"Authorization": f"Token {api_key}"},
    )
    passages = data.get("passages") or []
    text = _clean_bible_text(passages[0])
    return QuoteConfig(
        enabled=fallback.enabled,
        source=source,
        title=fallback.title or title,
        text=text,
        author=_clean_text(data.get("canonical") or reference),
    )


def _fetch_today_in_history(fallback: QuoteConfig) -> QuoteConfig:
    today = now()
    url = "https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{:02d}/{:02d}".format(
        today.month,
        today.day,
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


def _get_json(url: str, headers: dict[str, str] | None = None) -> Any:
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "desk-clock-config/0.2.6 (https://github.com/frobobbo/desk-clock)",
    }
    request_headers.update(headers or {})
    request = Request(
        url,
        headers=request_headers,
    )
    with urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _daily_pick(items: list[Any]) -> Any:
    if not items:
        raise ValueError("no provider items returned")
    return deepcopy(items[now().timetuple().tm_yday % len(items)])


def _today_key() -> str:
    return now().strftime("%Y-%m-%d")


def _clean_bible_text(text: str) -> str:
    return _clean_text(" ".join(line.strip() for line in text.splitlines() if line.strip()))


def _clean_text(text: str) -> str:
    return " ".join(str(text).replace("\u201c", '"').replace("\u201d", '"').split())
