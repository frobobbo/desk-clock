#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include <cstdio>
#include <cstring>

#include "EPD.h"
#include "klyra_clock_font.h"

namespace {

#ifndef WIFI_SSID
#define WIFI_SSID ""
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif

#ifndef CONFIG_API_URL
#define CONFIG_API_URL "https://deskclock.johnsons.casa"
#endif

constexpr char kWifiSsid[] = WIFI_SSID;
constexpr char kWifiPassword[] = WIFI_PASSWORD;
constexpr char kConfigApiUrl[] = CONFIG_API_URL;
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
constexpr int kClockRegionH = 250;

uint8_t ImageBW[27200];
uint8_t PreviousImageBW[27200];

struct DisplayContent {
  bool weather_enabled = true;
  bool quote_enabled = true;
  char weather_temperature[16] = "72F";
  char weather_temp_high[16] = "";
  char weather_temp_low[16] = "";
  char weather_condition[48] = "Partly Cloudy";
  char weather_location[48] = "Rochester Hills";
  char quote_source[32] = "daily_psalm";
  char quote_title[48] = "Daily Psalm";
  char quote_text[220] = "The Lord is my shepherd; I shall not want.";
  char quote_author[64] = "Psalm 23:1";
};

struct AppState {
  bool time_synced = false;
  bool display_initialized = false;
  unsigned long boot_millis = 0;
  time_t boot_epoch = 0;
  int last_minute = -1;
  int last_hour = -1;
  unsigned long last_config_fetch_ms = 0;
  uint16_t refresh_minutes = 30;
  DisplayContent content;
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

void copyText(char* dest, size_t dest_len, const char* value, const char* fallback)
{
  const char* source = (value && strlen(value) > 0) ? value : fallback;
  snprintf(dest, dest_len, "%s", source);
}

void drawWrappedCenteredText(int center_x, int y, const char* text, uint16_t size, uint16_t color, int max_chars, int max_lines, int line_gap)
{
  char buffer[240];
  copyText(buffer, sizeof(buffer), text, "");

  const char* cursor = buffer;
  int line = 0;
  while (*cursor && line < max_lines) {
    while (*cursor == ' ') {
      ++cursor;
    }
    if (!*cursor) {
      break;
    }

    const char* line_start = cursor;
    const char* best_break = nullptr;
    int count = 0;
    while (*cursor && count < max_chars) {
      if (*cursor == ' ') {
        best_break = cursor;
      }
      ++cursor;
      ++count;
    }

    const char* line_end = cursor;
    if (*cursor && best_break && best_break > line_start) {
      line_end = best_break;
      cursor = best_break + 1;
    }

    char line_text[80];
    const size_t len = min(static_cast<size_t>(line_end - line_start), sizeof(line_text) - 1);
    memcpy(line_text, line_start, len);
    line_text[len] = '\0';
    drawCenteredText(center_x, y + line * line_gap, line_text, size, color);
    ++line;
  }
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

void drawKlyraDateTextCentered(int center_x, int y, const char* text, uint16_t color)
{
  int total_w = 0;
  for (const char* p = text; *p; ++p) {
    uint8_t width = 0;
    uint8_t height = 0;
    klyraDateGlyph(*p, &width, &height);
    total_w += width;
    if (*(p + 1)) total_w += 3;
  }

  int x = center_x - total_w / 2;
  for (const char* p = text; *p; ++p) {
    uint8_t width = 0;
    uint8_t height = 0;
    const uint8_t* data = klyraDateGlyph(*p, &width, &height);
    if (data && width && height) {
      drawBitmapGlyph(x, y, data, width, height, color);
    }
    x += width;
    if (*(p + 1)) x += 3;
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

bool fetchDisplayConfig()
{
  state.last_config_fetch_ms = millis();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Config API skipped: WiFi is not connected");
    return false;
  }

  char url[160];
  snprintf(url, sizeof(url), "%s/api/displays/elecrow", kConfigApiUrl);

  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.setTimeout(8000);
  if (!http.begin(client, url)) {
    Serial.println("Config API begin failed");
    return false;
  }

  const int status = http.GET();
  if (status != HTTP_CODE_OK) {
    Serial.printf("Config API GET failed: %d\n", status);
    http.end();
    return false;
  }

  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, http.getStream());
  http.end();
  if (error) {
    Serial.printf("Config API JSON parse failed: %s\n", error.c_str());
    return false;
  }

  JsonObject weather = doc["weather"];
  JsonObject quote = doc["quote"];

  state.content.weather_enabled = weather["enabled"] | true;
  copyText(state.content.weather_temperature, sizeof(state.content.weather_temperature),
           weather["temperature"] | nullptr, "72F");
  copyText(state.content.weather_temp_high, sizeof(state.content.weather_temp_high),
           weather["temp_high"] | nullptr, "");
  copyText(state.content.weather_temp_low, sizeof(state.content.weather_temp_low),
           weather["temp_low"] | nullptr, "");
  copyText(state.content.weather_condition, sizeof(state.content.weather_condition),
           weather["condition"] | nullptr, "Partly Cloudy");
  copyText(state.content.weather_location, sizeof(state.content.weather_location),
           weather["location_label"] | nullptr, "Rochester Hills");

  state.content.quote_enabled = quote["enabled"] | true;
  copyText(state.content.quote_source, sizeof(state.content.quote_source),
           quote["source"] | nullptr, "daily_psalm");
  copyText(state.content.quote_title, sizeof(state.content.quote_title),
           quote["title"] | nullptr, "Daily Psalm");
  copyText(state.content.quote_text, sizeof(state.content.quote_text),
           quote["text"] | nullptr, "The Lord is my shepherd; I shall not want.");
  copyText(state.content.quote_author, sizeof(state.content.quote_author),
           quote["author"] | nullptr, "Psalm 23:1");

  state.refresh_minutes = doc["refresh_minutes"] | 30;
  if (state.refresh_minutes == 0) {
    state.refresh_minutes = 30;
  }
  Serial.println("Config API updated Elecrow display content");
  return true;
}

void refreshDisplayConfigIfDue(bool force = false)
{
  const unsigned long interval_ms = static_cast<unsigned long>(state.refresh_minutes) * 60UL * 1000UL;
  if (!force && state.last_config_fetch_ms != 0 && millis() - state.last_config_fetch_ms < interval_ms) {
    return;
  }
  fetchDisplayConfig();
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
  drawKlyraDateTextCentered(kCardX + kCardW / 2, 230, weekday, WHITE);
  drawKlyraDateTextCentered(kCardX + kCardW / 2, 286, month_day, WHITE);
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
  if (!state.content.weather_enabled) {
    return;
  }

  const int content_center_x = kCardX + kCardW / 2;
  const int icon_width = 62;
  const int gap = 14;
  const int temp_width = textWidth(state.content.weather_temperature, 24);
  const int total_width = icon_width + gap + temp_width;
  const int row_left = content_center_x - total_width / 2;

  const bool has_hl = strlen(state.content.weather_temp_high) > 0
                   || strlen(state.content.weather_temp_low) > 0;

  drawDividerOrnament(352);
  drawCloudIcon(row_left, 374);
  EPD_ShowString(row_left + icon_width + gap, 380, state.content.weather_temperature, 24, WHITE);
  if (has_hl) {
    char hl[32];
    snprintf(hl, sizeof(hl), "H:%s L:%s",
             state.content.weather_temp_high,
             state.content.weather_temp_low);
    drawCenteredText(content_center_x, 412, hl, 16, WHITE);
    drawCenteredText(content_center_x, 442, state.content.weather_condition, 24, WHITE);
  } else {
    drawCenteredText(content_center_x, 430, state.content.weather_condition, 24, WHITE);
  }
}

void drawQuoteSection()
{
  if (!state.content.quote_enabled) {
    return;
  }

  const int center_x = kCardX + kCardW / 2;

  drawDividerOrnament(500);
  drawCenteredText(center_x, 528, state.content.quote_title, 24, WHITE);
  if (strlen(state.content.quote_author) > 0) {
    drawCenteredText(center_x, 568, state.content.quote_author, 16, WHITE);
  }
  drawWrappedCenteredText(center_x, 610, state.content.quote_text, 24, WHITE, 18, 4, 32);
  drawDividerOrnament(744);
}

void renderFullLayout(const tm& now)
{
  drawStaticChrome();
  drawClockRegion(now);
  drawWeatherSection();
  drawQuoteSection();
}

void fullRefresh(const tm& now)
{
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
  drawQuoteSection();

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
  refreshDisplayConfigIfDue(true);
  fullRefresh(now);
  Serial.println("setup complete");
}

void loop()
{
  delay(1000);
  const tm now = currentLocalTime();

  const unsigned long interval_ms = static_cast<unsigned long>(state.refresh_minutes) * 60UL * 1000UL;
  if (state.last_config_fetch_ms == 0 || millis() - state.last_config_fetch_ms >= interval_ms) {
    if (fetchDisplayConfig()) {
      state.last_hour = now.tm_hour;
      state.last_minute = now.tm_min;
      fullRefresh(now);
      return;
    }
  }

  if (now.tm_hour != state.last_hour) {
    state.last_hour = now.tm_hour;
    state.last_minute = now.tm_min;
    refreshDisplayConfigIfDue(true);
    fullRefresh(now);
    return;
  }

  if (now.tm_min != state.last_minute) {
    state.last_minute = now.tm_min;
    partialClockRefresh(now);
  }
}
