from machine import SPI, Pin
import time

import config
from lib.epd7in5b import EPD7in5B, BLACK, WHITE, RED


def main():
    spi  = SPI(1, baudrate=4_000_000, sck=Pin(10), mosi=Pin(11))
    cs   = Pin(9,  Pin.OUT, value=1)
    dc   = Pin(8,  Pin.OUT)
    rst  = Pin(12, Pin.OUT)
    busy = Pin(13, Pin.IN)

    epd = EPD7in5B(
        spi, cs, dc, rst, busy,
        busy_active=config.EPD_BUSY_ACTIVE,
        busy_timeout_ms=config.EPD_BUSY_TIMEOUT_MS,
    )

    print("BUSY pin before init:", busy.value())
    print("init...")
    epd.init()
    print("init done")

    print("phase 1: hardware clear to white")
    epd.clear()
    time.sleep_ms(2000)

    print("phase 2: B/W test pattern")
    epd.fill(WHITE)
    epd.rect(8, 8, 784, 464, BLACK)
    epd.rect(20, 20, 760, 440, BLACK)
    epd.hline(40, 120, 720, BLACK)
    epd.vline(400, 40, 360, BLACK)
    epd.text_scaled("EPD 7.5 B TEST", 160, 50, scale=3, color=BLACK)
    epd.text_scaled("Black/White channel", 90, 170, scale=2, color=BLACK)
    epd.text_scaled("Left", 140, 300, scale=2, color=BLACK)
    epd.text_scaled("Right", 520, 300, scale=2, color=BLACK)
    epd.display()
    print("B/W pattern done")
    time.sleep_ms(4000)

    print("phase 3: red channel test")
    epd.fill(WHITE)
    epd.rect(8, 8, 784, 464, BLACK)
    epd.text_scaled("RED CHANNEL", 200, 50, scale=4, color=RED)
    epd.hline(40, 100, 720, RED)
    epd.hline(40, 102, 720, RED)
    epd.text_scaled("If this text is red,", 80, 160, scale=2, color=RED)
    epd.text_scaled("the tri-colour channel works.", 80, 200, scale=2, color=RED)
    epd.text_scaled("Black text below for contrast:", 80, 260, scale=2, color=BLACK)
    epd.text_scaled("SPI / RST / BUSY all OK", 80, 300, scale=2, color=BLACK)
    epd.display()
    print("red test done")


main()
