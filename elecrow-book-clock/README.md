# ELECROW 5.79" Book Clock Sample

Sample Arduino/PlatformIO project for the ELECROW CrowPanel ESP32 5.79" E-Paper HMI Display.

The display is 792 x 272 visible pixels and black/white only, so the book background is rendered as a high-detail 1-bit dithered antique open-book spread. The generator creates:

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

## Build

With PlatformIO:

```bash
pio run
pio run -t upload
```

With Arduino IDE, open `src/main.cpp` as a sketch source reference and copy `include/book_background.h` plus the files from `lib/ElecrowEPD/src/` beside it.

## Design Notes

This panel cannot show grayscale. The background fakes realism with:

- dense paper fiber texture
- spine/gutter shadow
- curved page-edge shading
- deckled page borders
- subtle stains and foxing
- halftone-style dithering

For even better realism, render a 272 x 792 grayscale image on a desktop, dither it to 1-bit, and replace the generated bitmap while keeping the same byte layout.
