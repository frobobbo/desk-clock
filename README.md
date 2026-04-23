# The Daily Chronicle — Desk Clock

A book-themed desk clock running on a **Raspberry Pi Pico 2 W**.  
Displays the current time, date, weather, and a Quote of the Day on a  
**Waveshare 4.26" e-Paper HAT (800 × 480)**.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │              -* THE DAILY CHRONICLE *-                               │   │
│  ├──────────────────────────────────────┬─────────────────────────────  │   │
│  │                                      │                               │   │
│  │         10:42  PM                    │  ~ Quote of the Day ~         │   │
│  │        Wednesday                     │ ─────────────────────         │   │
│  │      April 20, 2026                  │                               │   │
│  │  ────────────────────                │  "The only way to do great    │   │
│  │   ☀  72°F  Partly Cloudy            │   work is to love what        │   │
│  │      Humidity 45%  Wind 8mph N       │   you do."                   │   │
│  │                                      │        - Steve Jobs           │   │
│  ├──────────────────────────────────────┴─────────────────────────────  │   │
│  │   ~ i ~                                                  ~ ii ~      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Hardware

| Component | Description |
|---|---|
| Raspberry Pi Pico 2 W | Microcontroller with WiFi (RP2350) |
| Waveshare 4.26" e-Paper HAT | 800 × 480 SPI e-Paper display (B/W) |

---

## Wiring Diagram

### Waveshare 4.26" e-Paper HAT → Pico 2 W

```
Waveshare HAT                Pico 2 W
─────────────────────────────────────────────────────────
 VCC  (3.3V)  ──────────────  Pin 36  (3V3 OUT)
 GND          ──────────────  Pin 38  (GND)
 DIN  (MOSI)  ──────────────  Pin 15  GP11  [SPI1 TX]
 CLK  (SCK)   ──────────────  Pin 14  GP10  [SPI1 SCK]
 CS           ──────────────  Pin 12  GP9
 DC           ──────────────  Pin 11  GP8
 RST          ──────────────  Pin 16  GP12
 BUSY         ──────────────  Pin 17  GP13
```

### Pico 2 W Pinout Reference

```
                   ┌─────────────────────┐
              VBUS ┤1                 40├ VBUS
              VSYS ┤2                 39├ VSYS
               GND ┤3                 38├ GND   ◄── HAT GND
         3V3 (OUT) ┤4  [3V3 OUT]      37├ 3V3_EN
         3V3 (OUT) ┤36 [3V3 OUT] ─────36├        ◄── HAT VCC
              GP27 ┤32                35├ ADC_VREF
              GP26 ┤31                34├ GP28
               GND ┤33                33├ GND
              GP22 ┤29                28├ GP21
              GP21 ┤27                27├ GP20
              GP20 ┤26                26├ GP19
              GP19 ┤25                25├ GP18
              GP18 ┤24                24├ GP17
              GP17 ┤23                23├ GP16
              GP16 ┤22                22├ GP15
               GND ┤23(GND)           21├ GP14
              GP13 ┤17 [BUSY] ◄────      │
              GP12 ┤16 [RST]  ◄────      │
              GP11 ┤15 [MOSI] ◄── HAT    │
              GP10 ┤14 [SCK]  ◄────      │
               GND ┤13                12├ GP9  [CS]  ◄── HAT
              GP8  ┤11 [DC]   ◄── HAT 11├
              GP7  ┤10                10├ GP6
               GND ┤8                  9├ GP5
              GP4  ┤6                  7├ GP5
              GP3  ┤5                  4├ GP2
              GP1  ┤2                  3├ GP0
               GND ┤1(GND)             │
                   └─────────────────────┘
```

---

## Software Setup

### 1 — Flash MicroPython

Download and flash the latest **Raspberry Pi Pico 2 W** MicroPython UF2 from:  
https://micropython.org/download/RPI_PICO2_W/

### 2 — Install Thonny (or use `mpremote`)

Thonny IDE: https://thonny.org  
Or install `mpremote`: `pip install mpremote`

### 3 — Configure the clock

Edit `src/config.py` and set:

```python
WIFI_SSID     = "your_network"
WIFI_PASSWORD = "your_password"
LATITUDE      = 40.7128    # your latitude
LONGITUDE     = -74.0060   # your longitude
TEMP_UNIT     = "fahrenheit"   # or "celsius"
TIME_FORMAT   = 12             # or 24
TIMEZONE_OFFSET = -5           # UTC offset (e.g. -5 for EST)
DST_OFFSET      = 1            # 1 during DST, 0 otherwise
```

### 4 — Upload files

Upload the entire `src/` directory to the Pico's root (`/`):

```bash
# Using mpremote:
mpremote connect /dev/ttyACM0 cp -r src/. :

# Or copy each file/folder manually in Thonny.
```

The Pico should start automatically on next boot.

---

## Project Structure

```
desk-clock/
├── README.md
├── .gitignore
└── src/
    ├── main.py              # Application entry point & main loop
    ├── config.py            # WiFi, location, timezone, pin config
    ├── display_manager.py   # Book-theme layout renderer
    ├── weather.py           # Open-Meteo weather API (no key required)
    ├── quotes.py            # ZenQuotes.io Quote of the Day (no key required)
    └── lib/
        └── epd4in26.py      # Waveshare 4.26" SSD1619A e-Paper driver
```

---

## APIs Used (free, no key required)

| Service | Endpoint |
|---|---|
| Weather | [Open-Meteo](https://open-meteo.com/) — no signup |
| Quotes  | [ZenQuotes.io](https://zenquotes.io/) — no signup |
| Time    | NTP (`pool.ntp.org`) via MicroPython `ntptime` |

---

## How It Works

1. **Boot** — initialises display, shows a splash screen, connects WiFi, and syncs the Pico's internal RTC via NTP.
2. **Every minute** — reads time from the Pico's internal RTC and redraws the display.
3. **Every 30 minutes** — fetches fresh weather from Open-Meteo.
4. **Once per day** — fetches a new Quote of the Day from ZenQuotes.
5. **WiFi offline** — continues using the Pico's current clock value plus cached/fallback data.

E-Paper retains the image indefinitely with zero power — ideal for a desk clock.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Blank / all-white display | Check SPI wiring (MOSI/SCK/CS/DC/RST/BUSY) |
| Time is wrong by ±1h | Adjust `DST_OFFSET` in `config.py` |
| No weather / quote | Check WiFi credentials and internet access |
| Display flickers | Normal — e-Paper full refresh takes ~3–5 s |

---

## License

MIT
