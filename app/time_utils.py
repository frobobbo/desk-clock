from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_TIMEZONE = "America/New_York"


def app_timezone() -> ZoneInfo:
    name = os.getenv("APP_TIMEZONE") or os.getenv("TZ") or DEFAULT_TIMEZONE
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)


def now() -> datetime:
    return datetime.now(app_timezone())
