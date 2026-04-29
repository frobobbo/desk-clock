from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from pydantic import BaseModel, Field

from .time_utils import now


class WeatherConfig(BaseModel):
    enabled: bool = True
    location_label: str = "Rochester Hills, MI"
    temperature: str = "72F"
    temp_high: str = ""
    temp_low: str = ""
    condition: str = "Partly cloudy"
    humidity: str = "45%"
    wind: str = "8 mph N"


ContentSource = Literal[
    "daily_author_quote",
    "daily_bible_verse",
    "daily_psalm",
    "today_in_history",
    "on_this_day_literature",
]


class QuoteConfig(BaseModel):
    enabled: bool = True
    source: ContentSource = "daily_author_quote"
    title: str = "Daily Quote"
    text: str = "A room without books is like a body without a soul."
    author: str = "Marcus Tullius Cicero"


class SectionConfig(QuoteConfig):
    pass


class SettingsConfig(BaseModel):
    esv_api_key: str = ""


class DisplayConfig(BaseModel):
    enabled: bool = True
    headline: str = "The Daily Chronicle"
    subtitle: str = ""
    show_time: bool = True
    show_date: bool = True
    weather: WeatherConfig = Field(default_factory=WeatherConfig)
    quote: QuoteConfig = Field(default_factory=QuoteConfig)
    upper: SectionConfig = Field(
        default_factory=lambda: SectionConfig(
            title="Literary Quote of the Day",
            text="I declare after all there is no enjoyment like reading!",
            author="Jane Austen",
        )
    )
    lower: SectionConfig = Field(
        default_factory=lambda: SectionConfig(
            source="on_this_day_literature",
            title="On This Day in Literature",
            text="In 1616, Shakespeare died in Stratford-upon-Avon on his 52nd birthday.",
            author="",
        )
    )
    footer_left: str = "~ i ~"
    footer_right: str = "~ ii ~"
    refresh_minutes: int = Field(default=30, ge=1, le=1440)
    notes: str = ""


class AppConfig(BaseModel):
    updated_at: str = ""
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    displays: dict[str, DisplayConfig] = Field(
        default_factory=lambda: {
            "elecrow": DisplayConfig(
                headline="KLYRA",
                subtitle="ESP32 5.79 e-paper",
                weather=WeatherConfig(
                    location_label="Rochester Hills, MI",
                    temperature="72F",
                    condition="Partly Cloudy",
                    humidity="45%",
                    wind="8 mph N",
                ),
                quote=QuoteConfig(
                    source="daily_psalm",
                    title="Daily Psalm",
                    text="The Lord is my shepherd; I shall not want.",
                    author="Psalm 23:1",
                ),
                footer_left="weather",
                footer_right="clock",
            ),
            "waveshare-rpi3": DisplayConfig(
                headline="The Daily Chronicle",
                subtitle="Raspberry Pi 3 + Waveshare 7.5 B",
                upper=SectionConfig(
                    source="daily_author_quote",
                    title="Literary Quote of the Day",
                    text="I declare after all there is no enjoyment like reading!",
                    author="Jane Austen",
                ),
                lower=SectionConfig(
                    source="on_this_day_literature",
                    title="On This Day in Literature",
                    text="In 1616, Shakespeare died in Stratford-upon-Avon on his 52nd birthday.",
                    author="",
                ),
            ),
        }
    )


class ConfigStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = Lock()

    def read(self) -> AppConfig:
        with self._lock:
            if not self.path.exists():
                config = AppConfig(updated_at=_now())
                self._write_unlocked(config)
                return config

            with self.path.open("r", encoding="utf-8") as handle:
                data: dict[str, Any] = json.load(handle)
            return _load_config(data)

    def replace(self, config: AppConfig) -> AppConfig:
        with self._lock:
            config.updated_at = _now()
            self._write_unlocked(config)
            return config

    def update_display(self, display_id: str, display: DisplayConfig) -> AppConfig:
        with self._lock:
            config = self._read_unlocked()
            config.displays[display_id] = display
            config.updated_at = _now()
            self._write_unlocked(config)
            return config

    def _read_unlocked(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig(updated_at=_now())
        with self.path.open("r", encoding="utf-8") as handle:
            return _load_config(json.load(handle))

    def _write_unlocked(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = config.model_dump(mode="json")

        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)


def _now() -> str:
    return now().isoformat(timespec="seconds")


def _load_config(data: dict[str, Any]) -> AppConfig:
    config = AppConfig.model_validate(data)
    displays = data.get("displays", {})
    pi_raw = displays.get("waveshare-rpi3", {}) if isinstance(displays, dict) else {}
    pi_display = config.displays.get("waveshare-rpi3")
    if pi_display and isinstance(pi_raw, dict) and "upper" not in pi_raw:
        pi_display.upper = SectionConfig.model_validate(pi_display.quote.model_dump(mode="json"))
    return config
