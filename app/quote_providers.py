from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from html import unescape
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
RANDOM_PSALM_URL = "https://bible-api.com/data/web/random/PSA"
LITQUOTES_DAILY_URL = "https://www.litquotes.com/DailyQuote.php"

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
        "text": "It was the best of times, it was the worst of times.",
        "author": "Charles Dickens, A Tale of Two Cities",
    },
    {
        "text": "Beware; for I am fearless, and therefore powerful.",
        "author": "Mary Shelley, Frankenstein",
    },
    {
        "text": "There is nothing in the world so irresistibly contagious as laughter and good humor.",
        "author": "Charles Dickens, A Christmas Carol",
    },
    {
        "text": "All the world's a stage.",
        "author": "William Shakespeare, As You Like It",
    },
    {
        "text": "Tomorrow is always fresh, with no mistakes in it yet.",
        "author": "L. M. Montgomery, Anne of Green Gables",
    },
    {
        "text": "I would always rather be happy than dignified.",
        "author": "Charlotte Bronte, Jane Eyre",
    },
    {
        "text": "There are darknesses in life and there are lights.",
        "author": "Bram Stoker, Dracula",
    },
    {
        "text": "Nothing is so painful to the human mind as a great and sudden change.",
        "author": "Mary Shelley, Frankenstein",
    },
    {
        "text": "I cannot fix on the hour, or the spot, or the look or the words, which laid the foundation.",
        "author": "Jane Austen, Pride and Prejudice",
    },
    {
        "text": "The moment you doubt whether you can fly, you cease for ever to be able to do it.",
        "author": "J. M. Barrie, Peter Pan",
    },
    {
        "text": "I am not afraid of storms, for I am learning how to sail my ship.",
        "author": "Louisa May Alcott, Little Women",
    },
    {
        "text": "No one who had ever seen Catherine Morland in her infancy would have supposed her born to be an heroine.",
        "author": "Jane Austen, Northanger Abbey",
    },
    {
        "text": "A loving heart is the truest wisdom.",
        "author": "Charles Dickens, David Copperfield",
    },
    {
        "text": "The course of true love never did run smooth.",
        "author": "William Shakespeare, A Midsummer Night's Dream",
    },
    {
        "text": "The pain of parting is nothing to the joy of meeting again.",
        "author": "Charles Dickens, Nicholas Nickleby",
    },
    {
        "text": "There was a star danced, and under that was I born.",
        "author": "William Shakespeare, Much Ado About Nothing",
    },
    {
        "text": "My love's more richer than my tongue.",
        "author": "William Shakespeare, King Lear",
    },
    {
        "text": "The wide world is all before us.",
        "author": "William Shakespeare, Romeo and Juliet",
    },
    {
        "text": "I like good strong words that mean something.",
        "author": "Louisa May Alcott, Little Women",
    },
    {
        "text": "A dream itself is but a shadow.",
        "author": "William Shakespeare, Hamlet",
    },
    {
        "text": "The heart was made to be broken.",
        "author": "Oscar Wilde, De Profundis",
    },
    {
        "text": "A little sincerity is a dangerous thing, and a great deal of it is absolutely fatal.",
        "author": "Oscar Wilde, The Critic as Artist",
    },
    {
        "text": "The truth is rarely pure and never simple.",
        "author": "Oscar Wilde, The Importance of Being Earnest",
    },
    {
        "text": "It is a far, far better thing that I do, than I have ever done.",
        "author": "Charles Dickens, A Tale of Two Cities",
    },
    {
        "text": "Every atom of your flesh is as dear to me as my own.",
        "author": "Charlotte Bronte, Jane Eyre",
    },
    {
        "text": "To thine own self be true.",
        "author": "William Shakespeare, Hamlet",
    },
    {
        "text": "Love looks not with the eyes, but with the mind.",
        "author": "William Shakespeare, A Midsummer Night's Dream",
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
    except (TimeoutError, URLError, ValueError, KeyError, TypeError, OSError) as exc:
        quote_config = quote.model_copy(deep=True)
        _set_debug(
            quote_config,
            provider=quote.source,
            endpoint="configured value",
            fallback_used=True,
            fallback_reason=_debug_error(exc),
        )

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
        quote = QuoteConfig(
            enabled=fallback.enabled,
            source="on_this_day_literature",
            title=fallback.title or "On This Day in Literature",
            text=resolve_literature_event(),
            author=fallback.author,
        )
        _set_debug(quote, provider="on_this_day_literature", endpoint="wikipedia on-this-day feed")
        return quote
    return fallback


def _fetch_zenquotes_today(fallback: QuoteConfig) -> QuoteConfig:
    data = _get_json("https://zenquotes.io/api/today")
    item = data[0]
    quote = QuoteConfig(
        enabled=fallback.enabled,
        source="daily_author_quote",
        title=fallback.title or "Daily Quote",
        text=_clean_text(item["q"]),
        author=_clean_text(item["a"]),
    )
    _set_debug(quote, provider="zenquotes", endpoint="https://zenquotes.io/api/today")
    return quote


def _fetch_literature_quote(fallback: QuoteConfig) -> QuoteConfig:
    try:
        return _fetch_litquotes_daily(fallback)
    except (TimeoutError, URLError, ValueError, KeyError, TypeError, OSError) as exc:
        fallback_error = exc

    item = _daily_pick(_LITERATURE_QUOTES)
    quote = QuoteConfig(
        enabled=fallback.enabled,
        source="quotes_from_literature",
        title=fallback.title or "Quotes from Literature",
        text=_clean_text(item["text"]),
        author=_clean_text(item["author"]),
    )
    _set_debug(
        quote,
        provider="local_literature_quotes",
        endpoint="local fallback list",
        fallback_used=True,
        fallback_reason=_debug_error(fallback_error),
        attempted_endpoint=LITQUOTES_DAILY_URL,
    )
    return quote


def _fetch_litquotes_daily(fallback: QuoteConfig) -> QuoteConfig:
    html = _get_text(LITQUOTES_DAILY_URL)
    line = _extract_litquotes_daily_line(html)
    text, title, author = _parse_litquotes_line(line)
    quote = QuoteConfig(
        enabled=fallback.enabled,
        source="quotes_from_literature",
        title=fallback.title or "Quotes from Literature",
        text=_clean_text(text),
        author=_clean_text(f"{author}, {title}" if title else author),
    )
    _set_debug(quote, provider="litquotes", endpoint=LITQUOTES_DAILY_URL)
    return quote


def _extract_litquotes_daily_line(html: str) -> str:
    marker = re.search(r"The Daily Quote for .*? is:", html, flags=re.IGNORECASE | re.DOTALL)
    if not marker:
        raise ValueError("LitQuotes daily quote marker not found")

    tail = html[marker.end() :]
    end = re.search(r"<(?:br|hr|div|p|h[1-6])\b|\n\s*\n", tail, flags=re.IGNORECASE)
    raw = tail[: end.start()] if end else tail
    line = _html_to_text(raw)
    if not line:
        raise ValueError("LitQuotes daily quote line not found")
    return line


def _parse_litquotes_line(line: str) -> tuple[str, str, str]:
    match = re.match(r"(.+?)\s*~\s*(.+?)\s+by\s+(.+)$", line)
    if not match:
        raise ValueError("LitQuotes daily quote format not recognized")
    return match.group(1), match.group(2), match.group(3)


def _fetch_bible_reference(reference: str, title: str, source: str, fallback: QuoteConfig) -> QuoteConfig:
    endpoint = f"https://bible-api.com/{quote(reference)}?translation=kjv"
    data = _get_json(endpoint)
    text = _clean_bible_text(data["text"])
    quote = QuoteConfig(
        enabled=fallback.enabled,
        source=source,
        title=fallback.title or title,
        text=text,
        author=_clean_text(data["reference"]),
    )
    _set_debug(quote, provider="bible-api", endpoint=endpoint)
    return quote


def _fetch_daily_psalm(fallback: QuoteConfig, settings: SettingsConfig | None = None) -> QuoteConfig:
    esv_api_key = _esv_api_key(settings)
    fallback_error: BaseException | None = None
    if esv_api_key:
        try:
            reference = _fetch_random_psalm_reference()
            return _fetch_esv_reference(reference, "Daily Psalm", "daily_psalm", fallback, esv_api_key)
        except (TimeoutError, URLError, ValueError, KeyError, TypeError, OSError) as exc:
            fallback_error = exc

    reference = _daily_pick(_PSALM_READINGS)
    quote = _fetch_bible_reference(reference, "Daily Psalm", "daily_psalm", fallback)
    if fallback_error:
        quote.debug.update(
            {
                "fallback_used": True,
                "fallback_reason": _debug_error(fallback_error),
                "attempted_endpoint": f"{RANDOM_PSALM_URL} -> {ESV_API_URL}",
            }
        )
    elif not esv_api_key:
        quote.debug.update(
            {
                "fallback_used": True,
                "fallback_reason": "ESV API key not configured",
                "attempted_endpoint": ESV_API_URL,
            }
        )
    return quote


def _fetch_random_psalm_reference() -> str:
    data = _get_json(RANDOM_PSALM_URL)
    verse = data.get("random_verse") or data.get("verse") or data
    book = str(verse.get("book") or verse.get("book_name") or "Psalm")
    chapter = int(verse["chapter"])
    verse_number = int(verse["verse"])
    if verse.get("book_id") and str(verse["book_id"]).upper() != "PSA":
        raise ValueError("random verse was not from Psalms")
    return f"{_normalize_psalm_book_name(book)} {chapter}:{verse_number}"


def _normalize_psalm_book_name(book: str) -> str:
    return "Psalm" if book.strip().lower() in {"psalm", "psalms", "psa"} else book.strip()


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
    endpoint = f"{ESV_API_URL}?{params}"
    data = _get_json(
        endpoint,
        headers={"Authorization": f"Token {api_key}"},
    )
    passages = data.get("passages") or []
    text = _clean_bible_text(passages[0])
    quote = QuoteConfig(
        enabled=fallback.enabled,
        source=source,
        title=fallback.title or title,
        text=text,
        author=_clean_text(data.get("canonical") or reference),
    )
    _set_debug(quote, provider="esv", endpoint=_redact_query(endpoint), reference=reference)
    return quote


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
    quote = QuoteConfig(
        enabled=fallback.enabled,
        source="today_in_history",
        title=fallback.title or "Today in History",
        text=text,
        author=str(year) if year else "On this day",
    )
    _set_debug(quote, provider="wikipedia", endpoint=url)
    return quote


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


def _get_text(url: str, headers: dict[str, str] | None = None) -> str:
    request_headers = {
        "Accept": "text/html,application/xhtml+xml",
        "User-Agent": "desk-clock-config/0.2.6 (https://github.com/frobobbo/desk-clock)",
    }
    request_headers.update(headers or {})
    request = Request(url, headers=request_headers)
    with urlopen(request, timeout=8) as response:
        return response.read().decode("utf-8", errors="replace")


def _daily_pick(items: list[Any]) -> Any:
    if not items:
        raise ValueError("no provider items returned")
    return deepcopy(items[now().timetuple().tm_yday % len(items)])


def _today_key() -> str:
    return now().strftime("%Y-%m-%d")


def _clean_bible_text(text: str) -> str:
    return _clean_text(" ".join(line.strip() for line in text.splitlines() if line.strip()))


def _set_debug(
    quote: QuoteConfig,
    *,
    provider: str,
    endpoint: str,
    fallback_used: bool = False,
    fallback_reason: str = "",
    attempted_endpoint: str = "",
    reference: str = "",
) -> None:
    quote.debug = {
        "provider": provider,
        "endpoint": endpoint,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
    }
    if attempted_endpoint:
        quote.debug["attempted_endpoint"] = attempted_endpoint
    if reference:
        quote.debug["reference"] = reference


def _debug_error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _redact_query(url: str) -> str:
    return url.split("?", 1)[0]


def _html_to_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return _clean_text(unescape(text.replace("\xa0", " ")))


def _clean_text(text: str) -> str:
    return " ".join(str(text).replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'").split())
