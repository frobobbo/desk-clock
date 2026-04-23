# Raspberry Pi 3 Waveshare 7.5" Book Clock

Sample project for a Raspberry Pi 3 driving a Waveshare 7.5" e-Paper Module/HAT (B).

This version uses a full raster background workflow:

- source artwork: `assets/source/book-background-source.png`
- processed black channel preview: `assets/generated/book-clock-black.png`
- processed red channel preview: `assets/generated/book-clock-red.png`
- composite preview: `assets/generated/book-clock-preview.png`

The panel is 800 x 480 and supports three display states: white, black, and red. The renderer uses Pillow to crop, sharpen, dither, and separate the artwork into the two 1-bit images expected by Waveshare's Python driver.

## Hardware

- Raspberry Pi 3
- Waveshare 7.5inch e-Paper Module/HAT (B), V2/V3 compatible
- 800 x 480 red/black/white SPI e-paper panel

Waveshare notes that V3 hardware is compatible with the V2 demo, so this project targets the Python module `epd7in5b_V2`.

## Raspberry Pi Setup

Enable SPI:

```bash
sudo raspi-config
```

Then enable `Interface Options` -> `SPI`.

Install dependencies:

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil python3-numpy python3-spidev python3-rpi.gpio
pip3 install waveshare-epaper
```

Some Waveshare examples use their GitHub checkout instead of the PyPI package:

```bash
git clone https://github.com/waveshare/e-Paper.git
```

If you use the checkout, run this project with `PYTHONPATH` pointed at its Python library folder:

```bash
PYTHONPATH=/path/to/e-Paper/RaspberryPi_JetsonNano/python/lib python3 src/display_book_clock.py --display
```

## Render A Preview

```bash
python3 src/render_book_clock.py
```

This writes PNG previews into `assets/generated/`.

## Display On The Panel

```bash
python3 src/display_book_clock.py --display
```

To render only without touching GPIO/display hardware:

```bash
python3 src/display_book_clock.py --preview-only
```

## Notes

Full red/black/white refreshes on this panel are slow, roughly tens of seconds. That is normal for tri-color e-paper. For a clock, render the full art at boot or hourly, then consider a simplified black-only partial update path for minute changes if the exact panel revision supports it well.

## Sources

- Waveshare product page: https://www.waveshare.com/product/7.5inch-e-paper-hat-b.htm
- Waveshare wiki/manual: https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_(B)_Manual
- Waveshare Python package: https://pypi.org/project/waveshare-epaper/
