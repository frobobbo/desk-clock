"""DS3231 RTC driver for MicroPython"""

DS3231_ADDR = 0x68

_REG_SECONDS = 0x00


def _bcd2dec(b):
    return (b >> 4) * 10 + (b & 0x0F)


def _dec2bcd(d):
    return ((d // 10) << 4) | (d % 10)


class DS3231:
    def __init__(self, i2c):
        self.i2c = i2c

    def get_datetime(self):
        """Return (year, month, day, hour, minute, second, weekday_0mon)"""
        d = self.i2c.readfrom_mem(DS3231_ADDR, _REG_SECONDS, 7)

        second  = _bcd2dec(d[0] & 0x7F)
        minute  = _bcd2dec(d[1] & 0x7F)

        h = d[2]
        if h & 0x40:                         # 12-hour mode
            hour = _bcd2dec(h & 0x1F)
            if h & 0x20:                     # PM bit
                hour = hour + 12 if hour != 12 else 12
            else:
                hour = 0 if hour == 12 else hour
        else:                                # 24-hour mode
            hour = _bcd2dec(h & 0x3F)

        weekday = _bcd2dec(d[3] & 0x07) - 1  # convert 1-7 to 0-6 (Mon=0)
        day     = _bcd2dec(d[4] & 0x3F)
        month   = _bcd2dec(d[5] & 0x1F)
        year    = _bcd2dec(d[6]) + 2000

        return (year, month, day, hour, minute, second, weekday)

    def set_datetime(self, year, month, day, hour, minute, second, weekday=0):
        """Set RTC. weekday: 0=Monday … 6=Sunday"""
        data = bytes([
            _dec2bcd(second),
            _dec2bcd(minute),
            _dec2bcd(hour),          # always write in 24-hour mode
            _dec2bcd(weekday + 1),   # DS3231 uses 1-7
            _dec2bcd(day),
            _dec2bcd(month),
            _dec2bcd(year - 2000),
        ])
        self.i2c.writeto_mem(DS3231_ADDR, _REG_SECONDS, data)

    def temperature(self):
        """Return chip temperature in °C (±3 °C accuracy)"""
        d = self.i2c.readfrom_mem(DS3231_ADDR, 0x11, 2)
        t = d[0] if not (d[0] & 0x80) else d[0] - 256
        return t + (d[1] >> 6) * 0.25
