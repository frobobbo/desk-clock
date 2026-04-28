# Raspberry Pi 3 Waveshare 7.5" B/W Book Clock

Sample project for a Raspberry Pi 3 driving a Waveshare 7.5" black/white e-Paper raw display.

This version renders a portrait literary dashboard inspired by an antique framed book plate:

- processed black channel preview: `assets/generated/book-clock-black.png`
- portrait preview: `assets/generated/book-clock-preview.png`
- greeting changes by time of day and is fixed to Lyndsay
- literary quote and on-this-day-in-literature content are fetched from the Desk Clock Config API

The logical design is drawn as `480 x 800` portrait art, then rotated into the `800 x 480` framebuffer expected by Waveshare's Python driver. Mount the panel in portrait orientation for the display to match the preview.

## Hardware

- Raspberry Pi 3
- Waveshare 7.5inch E-Ink Raw Display, black/white, 800 x 480 SPI

The display code targets Waveshare's black/white Python module `epd7in5_V2`, with a fallback to `epd7in5` for older library checkouts.

## Raspberry Pi Setup

### Automated Install

On the Raspberry Pi, run:

```bash
curl -fsSL https://raw.githubusercontent.com/frobobbo/desk-clock/main/rpi3-waveshare-book-clock/tools/install-pi.sh | sudo bash
```

The installer will:

- install OS packages needed for Pillow, SPI, GPIO, and the Waveshare driver
- enable SPI in Raspberry Pi config
- clone this repository to `/opt/desk-clock`
- create a Python virtual environment
- install `rpi3-waveshare-book-clock/requirements.txt`
- install a `desk-clock-rpi.service` systemd unit
- install a `desk-clock-rpi.timer` that refreshes the display hourly
- render a local preview to verify Python dependencies

If SPI was not already enabled, reboot after install:

```bash
sudo reboot
```

Then verify SPI:

```bash
ls -l /dev/spidev*
```

Render to the display once:

```bash
sudo systemctl start desk-clock-rpi.service
```

View logs:

```bash
journalctl -u desk-clock-rpi.service -n 100 --no-pager
```

Check the hourly refresh timer:

```bash
systemctl status desk-clock-rpi.timer
```

Installer options can be passed as environment variables:

```bash
curl -fsSL https://raw.githubusercontent.com/frobobbo/desk-clock/main/rpi3-waveshare-book-clock/tools/install-pi.sh \
  | sudo INSTALL_DIR=/opt/desk-clock APP_USER=pi RUN_ON_INSTALL=1 bash
```

Useful options:

| Variable | Default | Purpose |
|---|---|---|
| `REPO_URL` | `https://github.com/frobobbo/desk-clock.git` | Git repository to clone |
| `BRANCH` | `main` | Git branch to install |
| `INSTALL_DIR` | `/opt/desk-clock` | Clone location |
| `APP_USER` | invoking sudo user | User that runs the display service |
| `CREATE_SERVICE` | `1` | Set to `0` to skip systemd unit/timer creation |
| `RUN_ON_INSTALL` | `0` | Set to `1` to refresh the e-ink display immediately |

### Manual Install

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
sudo apt-get install -y python3-pip python3-pil python3-numpy python3-spidev python3-rpi.gpio fonts-gfs-baskerville
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

The renderer uses `http://deskclock.johnsons.casa` by default. Override the Config API base URL with either:

```bash
CONFIG_API_URL=http://deskclock.johnsons.casa python3 src/render_book_clock.py
```

or:

```bash
python3 src/render_book_clock.py --config-api-url http://deskclock.johnsons.casa
```

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
