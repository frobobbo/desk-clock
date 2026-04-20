"""
Quote of the Day via ZenQuotes.io (free, no API key required).
https://zenquotes.io/
"""

import urequests
import ujson

_URL = "https://zenquotes.io/api/today"

_FALLBACK = [
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("In the middle of every difficulty lies opportunity.", "Albert Einstein"),
    ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
]

_fallback_idx = 0


def fetch():
    global _fallback_idx
    try:
        r = urequests.get(_URL, timeout=10)
        data = ujson.loads(r.text)
        r.close()
        entry = data[0]
        return entry["q"], entry["a"]
    except Exception as e:
        print("Quote fetch error:", e)
        q, a = _FALLBACK[_fallback_idx % len(_FALLBACK)]
        _fallback_idx += 1
        return q, a
