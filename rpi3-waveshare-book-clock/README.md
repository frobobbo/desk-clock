# Raspberry Pi 3 Waveshare 7.5" B/W Book Clock

Sample project for a Raspberry Pi 3 driving a Waveshare 7.5" black/white e-Paper raw display.

This version renders a portrait literary dashboard inspired by an antique framed book plate:

- processed black channel preview: `assets/generated/book-clock-black.png`
- portrait preview: `assets/generated/book-clock-preview.png`

The logical design is drawn as `480 x 800` portrait art, then rotated into the `800 x 480` framebuffer expected by Waveshare's Python driver. Mount the panel in portrait orientation for the display to match the preview.

## Hardware

- Raspberry Pi 3
- Waveshare 7.5inch E-Ink Raw Display, black/white, 800 x 480 SPI

The display code targets Waveshare's black/white Python module `epd7in5_V2`, with a fallback to `epd7in5` for older library checkouts.

## Raspberry Pi Setup

Enable SPI:

```bash
sudo raspi-config
```

Then enable `Interface Options` -> `SPI`.

Reboot after enabling SPI, then verify the device node exists:

```bash
sudo reboot
ls -l /dev/spidev*
```

You should see at least:

```text
/dev/spidev0.0
```

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

Full black/white refreshes are much faster than the tri-color panel, but still avoid unnecessary repeated refreshes to reduce ghosting.

## Sources

- Waveshare product page: https://www.waveshare.com/product/displays/e-paper/epaper-1/7.5inch-e-paper.htm
- Waveshare Python package: https://pypi.org/project/waveshare-epaper/
