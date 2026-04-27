// indicators.cpp — draws battery + error icons in the bottom-left corner via
// a small partial refresh window.

#include "indicators.h"
#include "config.h"

#include <Arduino.h>
#include <GxEPD2_BW.h>

// Forward-declare the global panel object owned by display.cpp.
extern GxEPD2_BW<GxEPD2_750_T7, GxEPD2_750_T7::HEIGHT> display;

// Region geometry — the bottom-left 80×20 corner.
static constexpr int INDICATORS_X = 8;
static constexpr int INDICATORS_Y = 456;
static constexpr int INDICATORS_W = 96;
static constexpr int INDICATORS_H = 20;

static constexpr int BATTERY_BODY_W = 26;
static constexpr int BATTERY_BODY_H = 12;
static constexpr int BATTERY_NUB_W  = 3;
static constexpr int BATTERY_NUB_H  = 6;

static int batteryFillWidth(BatteryLevel level) {
  switch (level) {
    case BATTERY_HIGH:     return BATTERY_BODY_W - 4;  // ~22 px filled
    case BATTERY_MED:      return 14;
    case BATTERY_LOW:      return 7;
    case BATTERY_CRITICAL: return 2;
  }
  return 0;
}

static void drawBattery(int x, int y, BatteryLevel level) {
  display.drawRect(x, y, BATTERY_BODY_W, BATTERY_BODY_H, GxEPD_BLACK);
  // Terminal nub on the right side
  display.fillRect(
    x + BATTERY_BODY_W,
    y + (BATTERY_BODY_H - BATTERY_NUB_H) / 2,
    BATTERY_NUB_W,
    BATTERY_NUB_H,
    GxEPD_BLACK
  );
  // Inner fill — leave 2 px padding inside the body
  const int fill_w = batteryFillWidth(level);
  if (fill_w > 0) {
    display.fillRect(x + 2, y + 2, fill_w, BATTERY_BODY_H - 4, GxEPD_BLACK);
  }
}

static void drawErrorX(int x, int y) {
  // 14×14 X composed of two pairs of lines for thickness.
  for (int o = 0; o <= 1; o++) {
    display.drawLine(x + o,        y,             x + 13,     y + 13 - o, GxEPD_BLACK);
    display.drawLine(x,            y + o,         x + 13 - o, y + 13,     GxEPD_BLACK);
    display.drawLine(x + 13 - o,   y,             x,          y + 13 - o, GxEPD_BLACK);
    display.drawLine(x + 13,       y + o,         x + o,      y + 13,     GxEPD_BLACK);
  }
}

void indicatorsDraw(BatteryLevel level, bool show_error) {
  display.setPartialWindow(INDICATORS_X, INDICATORS_Y, INDICATORS_W, INDICATORS_H);
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    drawBattery(INDICATORS_X + 2, INDICATORS_Y + 4, level);
    if (show_error) {
      drawErrorX(INDICATORS_X + 2 + BATTERY_BODY_W + BATTERY_NUB_W + 8,
                 INDICATORS_Y + 3);
    }
  } while (display.nextPage());
}
