# ELECROW 5.79" Book Clock Sample

Sample Arduino/PlatformIO project for the ELECROW CrowPanel ESP32 5.79" E-Paper HMI Display.

The current sketch renders a centered single-column "watchface" layout inspired by a luxury book-style panel:

- top book icon
- large live clock
- weekday and date
- weather block from the internal config API
- quote block from the internal config API

Refresh behavior:

- minute changes use `EPD_PartUpdate()` after redrawing only the clock region
- hour changes trigger a full redraw and global refresh so weather/quote sections can update cleanly
- the firmware fetches display content from `https://deskclock.johnsons.casa/api/displays/elecrow`
- `refresh_minutes` from the config API controls how often the device checks for updated weather/quote content

The display driver itself exposes a `792 x 272` visible area on top of an `800 x 272` internal framebuffer. This sample keeps the vendor API intact and layers the layout on top of that framebuffer.

The generator still creates these background assets if you want to return to a bitmap-backed design:

- `include/book_background.h` - firmware bitmap stored in flash for `EPD_ShowPicture`
- `data/book_background.pbm` - preview image you can open locally

## Hardware Target

- ELECROW CrowPanel ESP32 5.79" E-Paper HMI Display
- ESP32-S3-WROOM-1-N8R8
- 8 MB flash, 8 MB PSRAM
- SSD1683 x2 e-paper driver
- 792 x 272 black/white visible panel
- 800 x 272 internal ELECROW framebuffer because the dual SSD1683 controllers leave an 8-column gap

ELECROW's Arduino examples use `EPD.h` and a 27,200-byte image buffer. This sample includes the reusable display driver files copied from ELECROW's official 5.79" Arduino demo package.

## Included Vendor Files

These files are included under `lib/ElecrowEPD/src/`:

- `EPD.h`
- `EPD.cpp`
- `EPD_Init.h`
- `EPD_Init.cpp`
- `EPDfont.h`
- `spi.h`
- `spi.cpp`

Source package:

```text
https://www.elecrow.com/download/product/CrowPanel/E-paper/5.79-DIS08792E/Arduino/Demos.zip
```

I did not include ELECROW's large demo image headers or WiFi/BLE example sketches because this sample only needs the reusable display driver.

ELECROW's tutorial instructs Arduino IDE users to select:

- Board: `ESP32S3 Dev Module`
- Partition Scheme: `Huge APP (3MB No OTA/1MB SPIFFS)`
- PSRAM: `OPI PSRAM`

The included `platformio.ini` mirrors those assumptions.

## Generate The Background

From this directory:

```bash
python3 tools/generate_book_background.py
```

The generated firmware asset is about 26.3 KB, which is reasonable for the ESP32-S3's flash. The preview is a plain PBM file so no Python imaging dependency is required.

## Configure Time / WiFi / API

The firmware can be built with WiFi credentials as PlatformIO build flags so secrets do not need to be committed:

```bash
PLATFORMIO_BUILD_FLAGS='-DWIFI_SSID=\"your_ssid\" -DWIFI_PASSWORD=\"your_password\"' pio run
```

The default API endpoint is:

```text
https://deskclock.johnsons.casa
```

Override it at build time if needed:

```bash
PLATFORMIO_BUILD_FLAGS='-DWIFI_SSID=\"your_ssid\" -DWIFI_PASSWORD=\"your_password\" -DCONFIG_API_URL=\"https://deskclock.johnsons.casa\"' pio run
```

If WiFi credentials are left blank, the sample falls back to elapsed time starting from the compile timestamp. If WiFi is configured and NTP succeeds, the clock uses real local time.

If the config API is unavailable, the screen keeps rendering with built-in fallback weather and quote values.

## Build

With PlatformIO:

```bash
pio run
pio run -t upload
```

With Arduino IDE, open `src/main.cpp` as a sketch source reference and copy `include/book_background.h` plus the files from `lib/ElecrowEPD/src/` beside it.

## Design Notes

The active sketch uses a black card with white ornamental line work rather than a bitmap background. That keeps minute partial refreshes cleaner and makes the centered watchface easier to read on this narrow e-paper panel.

If you want to go back to a bitmap-backed design later, the generator can still emit a firmware header and PBM preview from `tools/generate_book_background.py`.
