#include <Arduino.h>
#include <pgmspace.h>

#include "book_background.h"

// Copy ELECROW's official 5.79" display driver files into src/ or lib/.
// Their Arduino tutorial examples expose this API.
#include "EPD.h"

namespace {

constexpr uint16_t kScreenW = BOOK_BACKGROUND_WIDTH;
constexpr uint16_t kScreenH = BOOK_BACKGROUND_HEIGHT;

// ELECROW's dual-controller driver uses an 800 x 272 internal canvas. The
// visible panel is 792 x 272; the extra 8 columns account for the controller gap.
uint8_t ImageBW[27200];

void drawBackground()
{
  Paint_Clear(WHITE);
  EPD_ShowPicture(0, 0, kScreenW, kScreenH, BOOK_BACKGROUND_BITS, WHITE);
}

void drawHeader()
{
  EPD_ShowString(242, 20, "THE DAILY CHRONICLE", 24, BLACK);
  EPD_DrawLine(32, 54, 760, 54, BLACK);
  EPD_DrawLine(36, 58, 756, 58, BLACK);
}

void drawClockFace()
{
  EPD_ShowString(95, 92, "10:42 PM", 32, BLACK);
  EPD_ShowString(112, 142, "Thursday", 20, BLACK);
  EPD_ShowString(86, 174, "April 23, 2026", 20, BLACK);

  EPD_DrawLine(72, 218, 316, 218, BLACK);

  EPD_ShowString(88, 232, "72F  Partly Cloudy", 16, BLACK);
}

void drawQuote()
{
  EPD_ShowString(510, 84, "QUOTE OF THE DAY", 20, BLACK);
  EPD_DrawLine(486, 118, 720, 118, BLACK);
  EPD_ShowString(480, 146, "\"A room without books", 16, BLACK);
  EPD_ShowString(480, 172, "is like a body without", 16, BLACK);
  EPD_ShowString(480, 198, "a soul.\"", 16, BLACK);
  EPD_ShowString(600, 232, "- Cicero", 16, BLACK);
}

void drawFooter()
{
  EPD_ShowString(172, 252, "page 042", 16, BLACK);
  EPD_ShowString(590, 252, "page 043", 16, BLACK);
}

void renderBookClock()
{
  Paint_NewImage(ImageBW, EPD_W, EPD_H, Rotation, WHITE);
  drawBackground();

  drawHeader();
  drawClockFace();
  drawQuote();
  drawFooter();
}

void refreshDisplay()
{
  EPD_GPIOInit();

  // ELECROW examples power the display rail from IO7.
  pinMode(7, OUTPUT);
  digitalWrite(7, HIGH);

  EPD_FastMode1Init();
  EPD_Display_Clear();
  EPD_Update();
  EPD_Clear_R26A6H();

  renderBookClock();
  EPD_Display(ImageBW);
  EPD_PartUpdate();
  EPD_DeepSleep();
}

} // namespace

void setup()
{
  Serial.begin(115200);
  delay(200);
  Serial.println("ELECROW 5.79 book clock sample");
  refreshDisplay();
}

void loop()
{
  delay(60000);
}
