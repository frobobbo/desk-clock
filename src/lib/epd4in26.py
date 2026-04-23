"""
Waveshare 4.26" e-Paper Display Driver for MicroPython
Controller: SSD1619A  |  Resolution: 800 x 480  |  Colors: B/W

Default Pico 2 W wiring (see config.py to change pins):
  SCK   → GP10  (SPI1 CLK)
  MOSI  → GP11  (SPI1 TX)
  CS    → GP9
  DC    → GP8
  RST   → GP12
  BUSY  → GP13   HIGH = busy

Refer to Waveshare wiki for the latest official demo:
  https://www.waveshare.com/wiki/4.26inch_e-Paper_HAT
"""

import framebuf
import time
from machine import Pin, SPI

EPD_WIDTH  = 800
EPD_HEIGHT = 480

# SSD1619A commands
_SWRESET                    = 0x12
_DRIVER_OUTPUT_CTRL         = 0x01
_DATA_ENTRY_MODE            = 0x11
_SET_RAMX_ADDR              = 0x44
_SET_RAMY_ADDR              = 0x45
_BORDER_WAVEFORM_CTRL       = 0x3C
_TEMP_SENSOR_CTRL           = 0x18
_DISPLAY_UPDATE_CTRL2       = 0x22
_MASTER_ACTIVATION          = 0x20
_WRITE_RAM_BW               = 0x24
_SET_RAMX_COUNTER           = 0x4E
_SET_RAMY_COUNTER           = 0x4F
_WRITE_RAM_RED              = 0x26


class EPD4in26:
    def __init__(self, spi, cs, dc, rst, busy, busy_active=1, busy_timeout_ms=8000):
        self.spi  = spi
        self.cs   = cs
        self.dc   = dc
        self.rst  = rst
        self.busy = busy
        self.busy_active = 1 if busy_active else 0
        self.busy_timeout_ms = busy_timeout_ms

        self.width  = EPD_WIDTH
        self.height = EPD_HEIGHT

        self.buf = bytearray(EPD_WIDTH * EPD_HEIGHT // 8)
        self.fb  = framebuf.FrameBuffer(self.buf, EPD_WIDTH, EPD_HEIGHT,
                                        framebuf.MONO_HMSB)

    # ── low-level helpers ──────────────────────────────────────────────────

    def _cmd(self, cmd):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytes([cmd]))
        self.cs.value(1)

    def _data(self, data):
        self.dc.value(1)
        self.cs.value(0)
        if isinstance(data, int):
            self.spi.write(bytes([data]))
        else:
            self.spi.write(bytes(data))
        self.cs.value(1)

    def _wait(self, label="operation"):
        start = time.ticks_ms()
        while self.busy.value() == self.busy_active:
            if time.ticks_diff(time.ticks_ms(), start) > self.busy_timeout_ms:
                raise RuntimeError(
                    "EPD busy timeout during {} (busy pin stuck at {}, active={})".format(
                        label, self.busy.value(), self.busy_active
                    )
                )
            time.sleep_ms(10)
        time.sleep_ms(20)

    def _hw_reset(self):
        self.rst.value(1); time.sleep_ms(20)
        self.rst.value(0); time.sleep_ms(2)
        self.rst.value(1); time.sleep_ms(200)

    # ── public API ─────────────────────────────────────────────────────────

    def init(self):
        self._hw_reset()
        self._wait("post-reset idle wait")

        self._cmd(_SWRESET)
        self._wait("software reset")

        self._cmd(_TEMP_SENSOR_CTRL)
        self._data(0x80)

        self._cmd(0x0C)              # soft start
        self._data([0xAE, 0xC7, 0xC3, 0xC0, 0x80])

        self._cmd(_DRIVER_OUTPUT_CTRL)
        self._data([(EPD_HEIGHT - 1) % 256, (EPD_HEIGHT - 1) // 256, 0x02])

        self._cmd(_BORDER_WAVEFORM_CTRL)
        self._data(0x01)

        self._cmd(_DATA_ENTRY_MODE)
        self._data(0x01)             # X-increment, Y-decrement

        self._set_window(0, self.height - 1, self.width - 1, 0)

        self._reset_counters()
        self._wait("init completion")

    def _set_window(self, x_start, y_start, x_end, y_end):
        self._cmd(_SET_RAMX_ADDR)
        self._data([
            x_start & 0xFF,
            (x_start >> 8) & 0x03,
            x_end & 0xFF,
            (x_end >> 8) & 0x03,
        ])
        self._cmd(_SET_RAMY_ADDR)
        self._data([
            y_start & 0xFF,
            (y_start >> 8) & 0xFF,
            y_end & 0xFF,
            (y_end >> 8) & 0xFF,
        ])

    def _reset_counters(self):
        self._cmd(_SET_RAMX_COUNTER)
        self._data([0x00, 0x00])
        self._cmd(_SET_RAMY_COUNTER)
        self._data([0x00, 0x00])

    def clear(self, color=0xFF):
        """Fill display RAM.  0xFF = all white (default),  0x00 = all black."""
        self._reset_counters()
        self._cmd(_WRITE_RAM_BW)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(bytes([color]) * (EPD_WIDTH * EPD_HEIGHT // 8))
        self.cs.value(1)
        self._reset_counters()
        self._cmd(_WRITE_RAM_RED)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(bytes([color]) * (EPD_WIDTH * EPD_HEIGHT // 8))
        self.cs.value(1)
        self._refresh()

    def display(self):
        """Push the internal framebuffer to the display and trigger a full refresh."""
        self._reset_counters()
        self._cmd(_WRITE_RAM_BW)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(self.buf)
        self.cs.value(1)
        self._reset_counters()
        self._cmd(_WRITE_RAM_RED)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(self.buf)
        self.cs.value(1)
        self._refresh()

    def _refresh(self):
        self._cmd(_DISPLAY_UPDATE_CTRL2)
        self._data(0xF7)
        self._cmd(_MASTER_ACTIVATION)
        self._wait("display refresh")

    def sleep(self):
        self._cmd(0x10)              # deep sleep mode 1 (retains RAM)
        self._data(0x01)
        time.sleep_ms(100)

    # ── framebuffer convenience ────────────────────────────────────────────

    def fill(self, color=1):
        """1 = white background, 0 = black background."""
        self.fb.fill(color)

    def pixel(self, x, y, color=0):
        self.fb.pixel(x, y, color)

    def hline(self, x, y, w, color=0):
        self.fb.hline(x, y, w, color)

    def vline(self, x, y, h, color=0):
        self.fb.vline(x, y, h, color)

    def rect(self, x, y, w, h, color=0):
        self.fb.rect(x, y, w, h, color)

    def fill_rect(self, x, y, w, h, color=0):
        self.fb.fill_rect(x, y, w, h, color)

    def text(self, s, x, y, color=0):
        """Draw 8×8 pixel text (scale=1)."""
        self.fb.text(s, x, y, color)

    def text_scaled(self, s, x, y, scale=1, color=0):
        """Draw text scaled up by an integer factor using the built-in 8×8 font."""
        if scale == 1:
            self.fb.text(s, x, y, color)
            return
        tmp_buf = bytearray(8)
        tmp_fb  = framebuf.FrameBuffer(tmp_buf, 8, 8, framebuf.MONO_VLSB)
        for i, ch in enumerate(s):
            tmp_fb.fill(0)
            tmp_fb.text(ch, 0, 0, 1)
            cx = x + i * 8 * scale
            for row in range(8):
                for col in range(8):
                    if tmp_fb.pixel(col, row):
                        self.fb.fill_rect(cx + col * scale,
                                          y  + row * scale,
                                          scale, scale, color)
