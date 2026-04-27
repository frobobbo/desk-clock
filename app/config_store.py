from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field


class WeatherConfig(BaseModel):
    enabled: bool = True
    location_label: str = "Rochester Hills, MI"
    temperature: str = "72F"
    condition: str = "Partly cloudy"
    humidity: str = "45%"
    wind: str = "8 mph N"


class QuoteConfig(BaseModel):
    enabled: bool = True
    text: str = "A room without books is like a body without a soul."
    author: str = "Marcus Tullius Cicero"


class DisplayConfig(BaseModel):
    enabled: bool = True
    headline: str = "The Daily Chronicle"
    subtitle: str = ""
    show_time: bool = True
    show_date: bool = True
    weather: WeatherConfig = Field(default_factory=WeatherConfig)
    quote: QuoteConfig = Field(default_factory=QuoteConfig)
    footer_left: str = "~ i ~"
    footer_right: str = "~ ii ~"
    refresh_minutes: int = Field(default=30, ge=1, le=1440)
    notes: str = ""


class AppConfig(BaseModel):
    updated_at: str = ""
    displays: dict[str, DisplayConfig] = Field(
        default_factory=lambda: {
            "elecrow": DisplayConfig(
                headline="KLYRA",
                subtitle="ESP32 5.79 e-paper",
                footer_left="weather",
                footer_right="clock",
            ),
            "waveshare-rpi3": DisplayConfig(
                headline="The Daily Chronicle",
                subtitle="Raspberry Pi 3 + Waveshare 7.5 B",
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
            return AppConfig.model_validate(data)

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
            return AppConfig.model_validate(json.load(handle))

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
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

