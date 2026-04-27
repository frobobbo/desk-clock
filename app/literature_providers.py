from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


_CACHE: dict[str, dict[str, str]] = {}

_LITERARY_QUOTES = [
    {
        "quote": "I declare after all there is no enjoyment like reading!",
        "author": "Jane Austen",
    },
    {
        "quote": "A room without books is like a body without a soul.",
        "author": "Marcus Tullius Cicero",
    },
    {
        "quote": "The books that the world calls immoral are books that show the world its own shame.",
        "author": "Oscar Wilde",
    },
    {
        "quote": "We read to know we are not alone.",
        "author": "William Nicholson",
    },
    {
        "quote": "There is no friend as loyal as a book.",
        "author": "Ernest Hemingway",
    },
    {
        "quote": "I have always imagined that Paradise will be a kind of library.",
        "author": "Jorge Luis Borges",
    },
    {
        "quote": "Words are, in my not-so-humble opinion, our most inexhaustible source of magic.",
        "author": "J. K. Rowling",
    },
]

_LITERARY_KEYWORDS = (
    "author",
    "book",
    "novel",
    "novelist",
    "poem",
    "poet",
    "poetry",
    "play",
    "playwright",
    "writer",
    "literary",
    "literature",
    "published",
    "publisher",
    "shakespeare",
    "austen",
    "dickens",
    "bronte",
    "woolf",
    "tolkien",
    "hemingway",
    "orwell",
    "twain",
    "dostoevsky",
)

_FALLBACK_LITERATURE_EVENTS = [
    "In 1616, William Shakespeare died in Stratford-upon-Avon, leaving behind plays and poems that reshaped English literature.",
    "In 1813, Jane Austen's Pride and Prejudice was first published, introducing one of literature's most enduring heroines.",
    "In 1925, F. Scott Fitzgerald's The Great Gatsby was published, becoming a defining novel of the Jazz Age.",
    "In 1954, J. R. R. Tolkien's The Fellowship of the Ring was published, opening The Lord of the Rings to readers.",
    "In 1949, George Orwell's Nineteen Eighty-Four was published, giving modern language some of its sharpest political warnings.",
]


def resolve_literary_display(now: datetime | None = None) -> dict[str, str]:
    now = now or datetime.now(timezone.utc)
    cache_key = now.strftime("%Y-%m-%d")
    cached = _CACHE.get(cache_key)
    if cached:
        return dict(cached)

    quote = _daily_pick(_LITERARY_QUOTES, now)
    payload = {
        "quote": quote["quote"],
        "author": quote["author"],
        "literature_title": "ON THIS DAY IN LITERATURE",
        "literature_text": _resolve_literature_event(now),
    }
    _CACHE[cache_key] = dict(payload)
    return payload


def _resolve_literature_event(now: datetime) -> str:
    try:
        data = _get_json(
            "https://en.wikipedia.org/api/rest_v1/feed/onthisday/all/{:02d}/{:02d}".format(
                now.month,
                now.day,
            )
        )
    except (TimeoutError, URLError, ValueError, KeyError, TypeError, OSError):
        return _daily_pick(_FALLBACK_LITERATURE_EVENTS, now)

    for section in ("events", "births", "deaths", "selected"):
        for item in data.get(section, []):
            text = _clean_text(str(item.get("text", "")))
            pages = item.get("pages", [])
            haystack = text + " " + " ".join(
                _clean_text(str(page.get("title", ""))) + " " + _clean_text(str(page.get("description", "")))
                for page in pages
                if isinstance(page, dict)
            )
            if _looks_literary(haystack):
                year = item.get("year")
                prefix = f"In {year}, " if year else ""
                return prefix + text[0].lower() + text[1:] if text else _daily_pick(_FALLBACK_LITERATURE_EVENTS, now)

    return _daily_pick(_FALLBACK_LITERATURE_EVENTS, now)


def _daily_pick(items: list[dict[str, str]] | list[str], now: datetime) -> Any:
    ordinal = int(now.strftime("%Y%m%d"))
    return items[ordinal % len(items)]


def _looks_literary(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _LITERARY_KEYWORDS)


def _clean_text(value: str) -> str:
    return " ".join(value.replace("_", " ").split())


def _get_json(url: str) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "desk-clock-config/0.2.5 (https://github.com/frobobbo/desk-clock)",
        },
    )
    with urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))
