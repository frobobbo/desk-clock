"""
Waveshare Pico e-Paper 7.5 B driver for MicroPython
Controller: UC8179C  |  Resolution: 800 x 480  |  Colors: B/W/Red

Default Pico wiring (Waveshare Pico e-Paper plug-in board):
  SCK   → GP10  (SPI1 CLK)
  MOSI  → GP11  (SPI1 TX)
  CS    → GP9
  DC    → GP8
  RST   → GP12
  BUSY  → GP13   LOW = busy (Pico board inverts the signal)
"""

import framebuf
import time

EPD_WIDTH  = 800
EPD_HEIGHT = 480

BLACK = 0
WHITE = 1
RED   = 2


class EPD7in5B:
    def __init__(self, spi, cs, dc, rst, busy, busy_active=0, busy_timeout_ms=30000):
        self.spi  = spi
        self.cs   = cs
        self.dc   = dc
        self.rst  = rst
        self.busy = busy
        self.busy_active     = busy_active
        self.busy_timeout_ms = busy_timeout_ms

        self.width  = EPD_WIDTH
        self.height = EPD_HEIGHT

        # The 7.5" B panel expects data in the same layout used by Waveshare's
        # Pico example: HLSB framebuffer bytes sent one 8-pixel-wide column at a
        # time.  Using HMSB/linear row order makes text appear scrambled.
        # BW buffer: bit=1→white, bit=0→black
        self.buf_bw  = bytearray(EPD_WIDTH * EPD_HEIGHT // 8)
        # RED buffer: bit=1→red, bit=0→transparent
        self.buf_red = bytearray(EPD_WIDTH * EPD_HEIGHT // 8)
        self.fb_bw   = framebuf.FrameBuffer(self.buf_bw,  EPD_WIDTH, EPD_HEIGHT, framebuf.MONO_HLSB)
        self.fb_red  = framebuf.FrameBuffer(self.buf_red, EPD_WIDTH, EPD_HEIGHT, framebuf.MONO_HLSB)
        self.fb_bw.fill(1)   # white
        self.fb_red.fill(0)  # no red

    # ── low-level helpers ───────────────────────────────────────────────────

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
                    "EPD timeout during {} (pin={}, active={})".format(
                        label, self.busy.value(), self.busy_active
                    )
                )
            time.sleep_ms(10)
        time.sleep_ms(20)

    def _hw_reset(self):
        self.rst.value(1); time.sleep_ms(20)
        self.rst.value(0); time.sleep_ms(2)
        self.rst.value(1); time.sleep_ms(20)

    # ── public API ──────────────────────────────────────────────────────────

    def init(self):
        self._hw_reset()

        self._cmd(0x06)  # Booster Soft Start
        self._data([0x17, 0x17, 0x28, 0x17])

        self._cmd(0x04)  # Power On
        time.sleep_ms(100)
        self._wait("power on")

        self._cmd(0x00)  # Panel Setting: KWR mode, LUT from OTP
        self._data(0x0F)

        self._cmd(0x61)  # Resolution: 800 x 480
        self._data([0x03, 0x20, 0x01, 0xE0])

        self._cmd(0x15)
        self._data(0x00)

        self._cmd(0x50)  # VCOM and Data Interval Setting
        self._data([0x11, 0x07])

        self._cmd(0x60)  # TCON Setting
        self._data(0x22)

        self._cmd(0x65)  # Flash Mode
        self._data([0x00, 0x00, 0x00, 0x00])

    def init_partial(self):
        """Initialise the controller for black/white partial refreshes."""
        self._hw_reset()

        self._cmd(0x00)  # Panel Setting
        self._data(0x1F)

        self._cmd(0x04)  # Power On
        time.sleep_ms(100)
        self._wait("partial power on")

        self._cmd(0xE0)
        self._data(0x02)

        self._cmd(0xE5)
        self._data(0x6E)

        self._cmd(0x50)  # VCOM and Data Interval Setting
        self._data([0xA9, 0x07])

    def display(self):
        """Push framebuffers to the panel and trigger a full refresh (~15 s)."""
        self._cmd(0x10)  # Black/White channel
        self._write_panel_buffer(self.buf_bw)

        self._cmd(0x13)  # Red channel
        self._write_panel_buffer(self.buf_red)

        self._cmd(0x12)  # Display Refresh
        time.sleep_ms(100)
        self._wait("display refresh")

    def display_partial(self, x=0, y=0, w=None, h=None):
        """Refresh black/white content using the controller's partial mode.

        This panel's Waveshare Pico demo only exercises partial refresh by
        sending a full-screen black/white image through the partial-refresh
        pipeline.  In practice that is much more reliable than cropped partial
        windows on this tri-color controller, while still avoiding the slow,
        flashing red/black global refresh.
        """
        x_start = 0
        y_start = 0
        x_end = self.width
        y_end = self.height

        self._cmd(0x91)  # Enter partial mode
        self._cmd(0x90)  # Partial window
        self._data([
            x_start // 256, x_start % 256,
            (x_end - 1) // 256, (x_end - 1) % 256,
            y_start // 256, y_start % 256,
            (y_end - 1) // 256, (y_end - 1) % 256,
            0x01,
        ])

        self._cmd(0x10)
        self._write_partial_fill_buffer(0xFF, x_start, y_start, x_end, y_end)

        self._cmd(0x13)
        self._write_partial_panel_buffer(self.buf_bw, x_start, y_start, x_end, y_end)

        self._cmd(0x12)  # Display Refresh
        time.sleep_ms(100)
        self._wait("partial display refresh")

    def clear(self):
        """Hardware clear to all white."""
        self._cmd(0x10)
        self._write_fill_buffer(0xFF)  # all white
        self._cmd(0x13)
        self._write_fill_buffer(0x00)  # no red
        self._cmd(0x12)
        time.sleep_ms(100)
        self._wait("clear")

    def sleep(self):
        self._cmd(0x02)  # Power Off
        self._data(0x00)
        self._wait("power off")
        self._cmd(0x07)  # Deep Sleep
        self._data(0xA5)

    def _write_panel_buffer(self, buf):
        """Write an HLSB framebuffer in the panel's expected byte order."""
        high = self.height
        wide = self.width // 8
        self.dc.value(1)
        self.cs.value(0)
        for i in range(wide):
            start = i * high
            self.spi.write(buf[start:start + high])
        self.cs.value(1)

    def _write_fill_buffer(self, value):
        """Write a solid-color channel in the same order as image buffers."""
        high = self.height
        wide = self.width // 8
        chunk = bytes([value]) * high
        self.dc.value(1)
        self.cs.value(0)
        for _ in range(wide):
            self.spi.write(chunk)
        self.cs.value(1)

    def _write_partial_panel_buffer(self, buf, x_start, y_start, x_end, y_end):
        high = self.height
        height = y_end - y_start
        first_col = x_start // 8
        last_col = x_end // 8
        self.dc.value(1)
        self.cs.value(0)
        for col in range(first_col, last_col):
            start = col * high + y_start
            self.spi.write(buf[start:start + height])
        self.cs.value(1)

    def _write_partial_fill_buffer(self, value, x_start, y_start, x_end, y_end):
        height = y_end - y_start
        cols = (x_end - x_start) // 8
        chunk = bytes([value]) * height
        self.dc.value(1)
        self.cs.value(0)
        for _ in range(cols):
            self.spi.write(chunk)
        self.cs.value(1)

    # ── framebuffer convenience ─────────────────────────────────────────────

    def _bw_red(self, color):
        """Return (bw_bit, red_bit) for a given color constant."""
        if color == RED:
            return 1, 1   # BW=white so black doesn't bleed; RED=1 means red
        if color == BLACK:
            return 0, 0   # BW=black; RED=0 transparent
        return 1, 0        # WHITE: BW=white, RED=0 transparent

    def fill(self, color=WHITE):
        bw, red = self._bw_red(color)
        self.fb_bw.fill(bw)
        self.fb_red.fill(red)

    def pixel(self, x, y, color=BLACK):
        bw, red = self._bw_red(color)
        self.fb_bw.pixel(x, y, bw)
        self.fb_red.pixel(x, y, red)

    def hline(self, x, y, w, color=BLACK):
        bw, red = self._bw_red(color)
        self.fb_bw.hline(x, y, w, bw)
        self.fb_red.hline(x, y, w, red)

    def vline(self, x, y, h, color=BLACK):
        bw, red = self._bw_red(color)
        self.fb_bw.vline(x, y, h, bw)
        self.fb_red.vline(x, y, h, red)

    def rect(self, x, y, w, h, color=BLACK):
        bw, red = self._bw_red(color)
        self.fb_bw.rect(x, y, w, h, bw)
        self.fb_red.rect(x, y, w, h, red)

    def fill_rect(self, x, y, w, h, color=BLACK):
        bw, red = self._bw_red(color)
        self.fb_bw.fill_rect(x, y, w, h, bw)
        self.fb_red.fill_rect(x, y, w, h, red)

    def text(self, s, x, y, color=BLACK):
        bw, red = self._bw_red(color)
        self.fb_bw.text(s, x, y, bw)
        self.fb_red.text(s, x, y, red)

    def text_scaled(self, s, x, y, scale=1, color=BLACK):
        if scale == 1:
            self.text(s, x, y, color)
            return
        bw, red = self._bw_red(color)
        tmp_buf = bytearray(8)
        tmp_fb  = framebuf.FrameBuffer(tmp_buf, 8, 8, framebuf.MONO_VLSB)
        for i, ch in enumerate(s):
            tmp_fb.fill(0)
            tmp_fb.text(ch, 0, 0, 1)
            cx = x + i * 8 * scale
            for row in range(8):
                for col in range(8):
                    if tmp_fb.pixel(col, row):
                        self.fb_bw.fill_rect(cx + col*scale, y + row*scale, scale, scale, bw)
                        self.fb_red.fill_rect(cx + col*scale, y + row*scale, scale, scale, red)
