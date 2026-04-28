#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys

from render_book_clock import GENERATED, fetch_clock_data, local_now, render, save_outputs


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def require_spi_device() -> None:
    spi_device = Path("/dev/spidev0.0")
    if spi_device.exists():
        return

    raise SystemExit(
        "SPI device /dev/spidev0.0 was not found. Enable SPI with "
        "`sudo raspi-config` -> Interface Options -> SPI, reboot, and verify "
        "with `ls -l /dev/spidev*`."
    )


def display(config_api_url: str | None = None) -> None:
    require_spi_device()

    try:
        from waveshare_epd import epd7in5_V2
    except ImportError as exc:
        try:
            from waveshare_epd import epd7in5 as epd7in5_V2
        except ImportError:
            raise SystemExit(
                "Could not import waveshare_epd.epd7in5_V2 or waveshare_epd.epd7in5. "
                "Install waveshare-epaper or set PYTHONPATH to Waveshare's "
                "RaspberryPi_JetsonNano/python/lib directory."
            ) from exc

    black, _ = render(fetch_clock_data(local_now(), config_api_url))
    epd = epd7in5_V2.EPD()
    logging.info("initializing Waveshare 7.5in black/white display")
    epd.init()
    logging.info("sending black/white framebuffer")
    epd.display(epd.getbuffer(black))
    logging.info("sleeping display")
    epd.sleep()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--display", action="store_true", help="Render and send to the e-paper display")
    parser.add_argument("--preview-only", action="store_true", help="Only write preview PNGs")
    parser.add_argument("--config-api-url", default=os.getenv("CONFIG_API_URL"), help="Config API base URL")
    args = parser.parse_args()

    if args.preview_only or not args.display:
        save_outputs(fetch_clock_data(local_now(), args.config_api_url))
        logging.info("wrote preview files to %s", GENERATED)
        if not args.display:
            return

    display(args.config_api_url)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
