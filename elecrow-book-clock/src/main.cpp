#include <Arduino.h>
#include <WiFi.h>
#include <time.h>
#include <cstdio>
#include <cstring>

#include "EPD.h"
#include "klyra_clock_font.h"

namespace {

constexpr char kWifiSsid[] = "";
constexpr char kWifiPassword[] = "";
constexpr char kTimezoneTz[] = "EST5EDT,M3.2.0/2,M11.1.0/2";
constexpr char kNtpServer[] = "pool.ntp.org";

constexpr int kVisibleWidth = 272;
constexpr int kVisibleHeight = 792;
constexpr int kCardX = 0;
constexpr int kCardY = 0;
constexpr int kCardW = 271;
constexpr int kCardH = 791;
constexpr int kInnerX = 24;
constexpr int kClockRegionY = 88;
constexpr int kClockRegionH = 230;

uint8_t ImageBW[27200];
uint8_t PreviousImageBW[27200];

struct WeatherData {
  int temperature_f;
  const char* condition;
};

struct PsalmReading {
  const char* reference;
  const char* line1;
  const char* line2;
  const char* line3;
};

const WeatherData kHourlyWeatherCycle[] = {
  {72, "Cloudy"},
  {71, "Partly Cloudy"},
  {69, "Rain Later"},
  {68, "Cloudy"},
};

const PsalmReading kDailyPsalms[] = {
  {"Psalm 23:1", "The Lord is my", "shepherd; I shall", "not want."},
  {"Psalm 46:10", "Be still, and know", "that I am God.", ""},
  {"Psalm 118:24", "This is the day", "which the Lord", "hath made."},
  {"Psalm 27:1", "The Lord is my", "light and my", "salvation."},
  {"Psalm 121:2", "My help cometh", "from the Lord,", "maker of heaven."},
  {"Psalm 19:14", "Let the words of", "my mouth be", "acceptable."},
  {"Psalm 91:2", "He is my refuge", "and my fortress:", "my God."},
};

struct AppState {
  bool time_synced = false;
  bool display_initialized = false;
  unsigned long boot_millis = 0;
  time_t boot_epoch = 0;
  int last_minute = -1;
  int last_hour = -1;
  size_t weather_index = 0;
  WeatherData weather = kHourlyWeatherCycle[0];
} state;

void epdPowerOn()
{
  EPD_GPIOInit();
  pinMode(7, OUTPUT);
  digitalWrite(7, HIGH);
  delay(100);
}

void initCanvas(uint16_t color)
{
  Paint_NewImage(ImageBW, EPD_W, EPD_H, Rotation, color);
  Paint_Clear(color);
}

void rememberDisplayedFrame()
{
  memcpy(PreviousImageBW, ImageBW, sizeof(ImageBW));
}

int textWidth(const char* text, uint16_t size)
{
  return static_cast<int>(strlen(text)) * static_cast<int>(size / 2);
}

void drawCenteredText(int center_x, int y, const char* text, uint16_t size, uint16_t color)
{
  EPD_ShowString(center_x - textWidth(text, size) / 2, y, text, size, color);
}

void drawHorizontalRule(int x0, int y, int x1, uint16_t color)
{
  EPD_DrawLine(x0, y, x1, y, color);
  EPD_DrawLine(x0 + 8, y + 3, x1 - 8, y + 3, color);
}

void drawCorner(int x, int y, int sx, int sy)
{
  EPD_DrawLine(x, y + 10 * sy, x, y, WHITE);
  EPD_DrawLine(x, y, x + 10 * sx, y, WHITE);
  EPD_DrawLine(x + 2 * sx, y + 8 * sy, x + 8 * sx, y + 2 * sy, WHITE);
}

void drawBookIcon(int center_x, int y)
{
  const int left = center_x - 18;
  const int right = center_x + 18;
  EPD_DrawLine(left - 26, y + 8, left - 6, y + 8, WHITE);
  EPD_DrawLine(right + 6, y + 8, right + 26, y + 8, WHITE);

  EPD_DrawLine(left, y + 3, left, y + 26, WHITE);
  EPD_DrawLine(center_x - 1, y, center_x - 1, y + 26, WHITE);
  EPD_DrawLine(center_x + 1, y, center_x + 1, y + 26, WHITE);
  EPD_DrawLine(right, y + 3, right, y + 26, WHITE);

  EPD_DrawLine(left, y + 3, center_x - 1, y, WHITE);
  EPD_DrawLine(left, y + 26, center_x - 1, y + 20, WHITE);
  EPD_DrawLine(right, y + 3, center_x + 1, y, WHITE);
  EPD_DrawLine(right, y + 26, center_x + 1, y + 20, WHITE);

  EPD_DrawLine(left + 10, y + 6, left + 10, y + 22, WHITE);
  EPD_DrawLine(right - 10, y + 6, right - 10, y + 22, WHITE);
}

void drawDividerOrnament(int y)
{
  const int cx = kCardX + kCardW / 2;
  EPD_DrawLine(kInnerX + 8, y, cx - 18, y, WHITE);
  EPD_DrawLine(cx + 18, y, kCardX + kCardW - 26, y, WHITE);
  EPD_DrawCircle(cx, y, 4, WHITE, 0);
  EPD_DrawCircle(cx - 10, y, 2, WHITE, 0);
  EPD_DrawCircle(cx + 10, y, 2, WHITE, 0);
}

void drawCloudIcon(int x, int y)
{
  EPD_DrawCircle(x + 14, y + 10, 10, WHITE, 1);
  EPD_DrawCircle(x + 30, y + 8, 12, WHITE, 1);
  EPD_DrawCircle(x + 46, y + 12, 9, WHITE, 1);
  EPD_DrawRectangle(x + 8, y + 12, x + 54, y + 23, WHITE, 1);
}

void drawBitmapGlyph(int x, int y, const uint8_t* data, uint8_t width, uint8_t height, uint16_t color)
{
  for (uint8_t row = 0; row < height; ++row) {
    for (uint8_t col = 0; col < width; ++col) {
      if (pgm_read_byte(data + row * width + col)) {
        Paint_SetPixel(x + col, y + row, color);
      }
    }
  }
}

void drawKlyraTextCentered(int center_x, int y, const char* text, bool large, uint16_t color)
{
  int total_w = 0;
  for (const char* p = text; *p; ++p) {
    uint8_t width = 0;
    uint8_t height = 0;
    if (large) {
      klyraLargeGlyph(*p, &width, &height);
    } else {
      klyraSmallGlyph(*p, &width, &height);
    }
    total_w += width;
    if (*(p + 1)) {
      total_w += large ? 8 : 4;
    }
  }

  int x = center_x - total_w / 2;
  for (const char* p = text; *p; ++p) {
    uint8_t width = 0;
    uint8_t height = 0;
    const uint8_t* data = large ? klyraLargeGlyph(*p, &width, &height) : klyraSmallGlyph(*p, &width, &height);
    if (data && width && height) {
      drawBitmapGlyph(x, y, data, width, height, color);
      x += width;
    }
    if (*(p + 1)) {
      x += large ? 8 : 4;
    }
  }
}

void connectWifiAndTime()
{
  if (strlen(kWifiSsid) == 0) {
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(kWifiSsid, kWifiPassword);
  Serial.printf("Connecting to WiFi SSID '%s'\n", kWifiSsid);
  for (int i = 0; i < 30 && WiFi.status() != WL_CONNECTED; ++i) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi unavailable, using elapsed-time fallback");
    return;
  }

  configTzTime(kTimezoneTz, kNtpServer);
  struct tm now_tm;
  for (int i = 0; i < 30; ++i) {
    if (getLocalTime(&now_tm, 500)) {
      state.time_synced = true;
      Serial.println("NTP time synchronized");
      return;
    }
  }
  Serial.println("NTP sync failed, using elapsed-time fallback");
}

int monthIndex(const char* mon)
{
  static const char* kMonths[] = {
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
  };
  for (int i = 0; i < 12; ++i) {
    if (strncmp(mon, kMonths[i], 3) == 0) {
      return i;
    }
  }
  return 0;
}

time_t compileTimeEpoch()
{
  char mon[4] = {};
  int day = 1;
  int year = 2026;
  int hour = 0;
  int minute = 0;
  int second = 0;
  sscanf(__DATE__, "%3s %d %d", mon, &day, &year);
  sscanf(__TIME__, "%d:%d:%d", &hour, &minute, &second);

  struct tm tm_value = {};
  tm_value.tm_year = year - 1900;
  tm_value.tm_mon = monthIndex(mon);
  tm_value.tm_mday = day;
  tm_value.tm_hour = hour;
  tm_value.tm_min = minute;
  tm_value.tm_sec = second;
  tm_value.tm_isdst = -1;
  return mktime(&tm_value);
}

tm currentLocalTime()
{
  time_t now = 0;
  if (state.time_synced) {
    time(&now);
  } else {
    const unsigned long elapsed = (millis() - state.boot_millis) / 1000UL;
    now = state.boot_epoch + elapsed;
  }

  struct tm out = {};
  localtime_r(&now, &out);
  return out;
}

void updateWeatherForHour(int hour)
{
  state.weather_index = static_cast<size_t>(hour) % (sizeof(kHourlyWeatherCycle) / sizeof(kHourlyWeatherCycle[0]));
  state.weather = kHourlyWeatherCycle[state.weather_index];
}

void formatTimeStrings(const tm& now, char* hhmm, size_t hhmm_len, char* ampm, size_t ampm_len)
{
  int hour = now.tm_hour % 12;
  if (hour == 0) {
    hour = 12;
  }
  snprintf(hhmm, hhmm_len, "%d:%02d", hour, now.tm_min);
  snprintf(ampm, ampm_len, "%s", now.tm_hour >= 12 ? "PM" : "AM");
}

void formatDateStrings(const tm& now, char* weekday, size_t weekday_len, char* month_day, size_t month_day_len)
{
  strftime(weekday, weekday_len, "%A", &now);
  strftime(month_day, month_day_len, "%b %d", &now);
}

void clearClockRegion()
{
  EPD_DrawRectangle(kInnerX + 4, kClockRegionY, kCardX + kCardW - 21, kClockRegionY + kClockRegionH, BLACK, 1);
}

void drawClockRegion(const tm& now)
{
  char hhmm[16];
  char ampm[8];
  char weekday[20];
  char month_day[20];
  formatTimeStrings(now, hhmm, sizeof(hhmm), ampm, sizeof(ampm));
  formatDateStrings(now, weekday, sizeof(weekday), month_day, sizeof(month_day));

  clearClockRegion();
  drawKlyraTextCentered(kCardX + kCardW / 2, 94, hhmm, true, WHITE);
  drawKlyraTextCentered(kCardX + kCardW / 2, 176, ampm, false, WHITE);
  drawHorizontalRule(kInnerX + 16, 218, kCardX + kCardW - 34, WHITE);
  drawCenteredText(kCardX + kCardW / 2, 248, weekday, 24, WHITE);
  drawCenteredText(kCardX + kCardW / 2, 286, month_day, 24, WHITE);
}

void drawStaticChrome()
{
  initCanvas(BLACK);
  EPD_DrawRectangle(kCardX + 4, kCardY + 4, kCardX + kCardW - 4, kCardY + kCardH - 4, WHITE, 0);
  EPD_DrawRectangle(kCardX + 10, kCardY + 10, kCardX + kCardW - 10, kCardY + kCardH - 10, WHITE, 0);

  drawCorner(kCardX + 6, kCardY + 6, 1, 1);
  drawCorner(kCardX + kCardW - 6, kCardY + 6, -1, 1);
  drawCorner(kCardX + 6, kCardY + kCardH - 6, 1, -1);
  drawCorner(kCardX + kCardW - 6, kCardY + kCardH - 6, -1, -1);
  drawBookIcon(kCardX + kCardW / 2, 30);
}

void drawWeatherSection()
{
  char temp[16];
  snprintf(temp, sizeof(temp), "%dF", state.weather.temperature_f);
  const int content_center_x = kCardX + kCardW / 2;
  const int icon_width = 62;
  const int gap = 14;
  const int temp_width = textWidth(temp, 24);
  const int total_width = icon_width + gap + temp_width;
  const int row_left = content_center_x - total_width / 2;

  drawDividerOrnament(372);
  drawCloudIcon(row_left, 394);
  EPD_ShowString(row_left + icon_width + gap, 400, temp, 24, WHITE);
  drawCenteredText(content_center_x, 450, state.weather.condition, 24, WHITE);
}

void drawPsalmSection(const tm& now)
{
  const size_t psalm_count = sizeof(kDailyPsalms) / sizeof(kDailyPsalms[0]);
  const PsalmReading& psalm = kDailyPsalms[static_cast<size_t>(now.tm_yday) % psalm_count];
  const int center_x = kCardX + kCardW / 2;

  drawDividerOrnament(520);
  drawCenteredText(center_x, 548, "Daily Psalm", 24, WHITE);
  drawCenteredText(center_x, 588, psalm.reference, 16, WHITE);
  drawCenteredText(center_x, 630, psalm.line1, 16, WHITE);
  drawCenteredText(center_x, 658, psalm.line2, 16, WHITE);
  if (strlen(psalm.line3) > 0) {
    drawCenteredText(center_x, 686, psalm.line3, 16, WHITE);
  }
  drawDividerOrnament(744);
}

void renderFullLayout(const tm& now)
{
  drawStaticChrome();
  drawClockRegion(now);
  drawWeatherSection();
  drawPsalmSection(now);
}

void fullRefresh(const tm& now)
{
  updateWeatherForHour(now.tm_hour);
  renderFullLayout(now);

  Serial.printf("full refresh %02d:%02d\n", now.tm_hour, now.tm_min);
  epdPowerOn();
  if (!state.display_initialized) {
    Serial.println("display cold init");
    EPD_FastMode1Init();
    EPD_Display_Clear();
    EPD_Update();
    EPD_Clear_R26A6H();
    state.display_initialized = true;
  } else {
    Serial.println("display fast init");
    EPD_FastMode1Init();
  }

  EPD_Display(ImageBW);
  EPD_PartUpdate();
  EPD_DeepSleep();
  rememberDisplayedFrame();
}

void partialClockRefresh(const tm& now)
{
  drawStaticChrome();
  drawClockRegion(now);
  drawWeatherSection();
  drawPsalmSection(now);

  Serial.printf("partial clock refresh %02d:%02d\n", now.tm_hour, now.tm_min);
  epdPowerOn();
  EPD_FastMode1Init();
  EPD_Display_Partial(ImageBW, PreviousImageBW);
  EPD_PartUpdate();
  EPD_DeepSleep();
  rememberDisplayedFrame();
}

} // namespace

void setup()
{
  Serial.begin(115200);
  delay(200);
  Serial.println("ELECROW 5.79 live book clock");

  state.boot_millis = millis();
  state.boot_epoch = compileTimeEpoch();

  connectWifiAndTime();

  const tm now = currentLocalTime();
  state.last_minute = now.tm_min;
  state.last_hour = now.tm_hour;
  fullRefresh(now);
  Serial.println("setup complete");
}

void loop()
{
  delay(1000);
  const tm now = currentLocalTime();

  if (now.tm_hour != state.last_hour) {
    state.last_hour = now.tm_hour;
    state.last_minute = now.tm_min;
    fullRefresh(now);
    return;
  }

  if (now.tm_min != state.last_minute) {
    state.last_minute = now.tm_min;
    partialClockRefresh(now);
  }
}
