#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import logging
from pathlib import Path
import sys

from render_book_clock import ClockData, GENERATED, render, save_outputs


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


def display() -> None:
    require_spi_device()

    try:
        from waveshare_epd import epd7in5b_V2
    except ImportError as exc:
        raise SystemExit(
            "Could not import waveshare_epd.epd7in5b_V2. Install waveshare-epaper "
            "or set PYTHONPATH to Waveshare's RaspberryPi_JetsonNano/python/lib directory."
        ) from exc

    _, black, red, _ = render(ClockData(now=datetime.now()))
    epd = epd7in5b_V2.EPD()
    logging.info("initializing Waveshare 7.5in B display")
    epd.init()
    logging.info("sending black/red framebuffers")
    epd.display(epd.getbuffer(black), epd.getbuffer(red))
    logging.info("sleeping display")
    epd.sleep()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--display", action="store_true", help="Render and send to the e-paper display")
    parser.add_argument("--preview-only", action="store_true", help="Only write preview PNGs")
    args = parser.parse_args()

    if args.preview_only or not args.display:
        save_outputs(ClockData(now=datetime.now()))
        logging.info("wrote preview files to %s", GENERATED)
        if not args.display:
            return

    display()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
