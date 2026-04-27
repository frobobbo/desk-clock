from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config_store import AppConfig, ConfigStore, DisplayConfig, QuoteConfig
from .quote_providers import resolve_display_content, resolve_quote


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "data/display-config.json"))

app = FastAPI(title="Desk Clock Display Config", version="0.2.2")
store = ConfigStore(CONFIG_PATH)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config", response_model=AppConfig)
def get_config() -> AppConfig:
    return store.read()


@app.put("/api/config", response_model=AppConfig)
def put_config(config: AppConfig) -> AppConfig:
    return store.replace(config)


@app.get("/api/displays")
def list_displays() -> dict[str, list[str]]:
    config = store.read()
    return {"displays": sorted(config.displays.keys())}


@app.get("/api/displays/{display_id}", response_model=DisplayConfig)
def get_display(display_id: str) -> DisplayConfig:
    config = store.read()
    try:
        return resolve_display_content(config.displays[display_id])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="display not found") from exc


@app.put("/api/displays/{display_id}", response_model=AppConfig)
def put_display(display_id: str, display: DisplayConfig) -> AppConfig:
    return store.update_display(display_id, display)


@app.post("/api/quote/resolve", response_model=QuoteConfig)
def post_quote_resolve(quote: QuoteConfig) -> QuoteConfig:
    return resolve_quote(quote)
