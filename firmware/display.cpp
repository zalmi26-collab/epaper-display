// display.cpp — GxEPD2 wrapper for Waveshare 7.5" 800x480 V2 panel.

#include "display.h"
#include "config.h"

#include <GxEPD2_BW.h>

// Driver class for Waveshare 7.5" V2 (UC8179 controller, 800x480).
// If you have V3 instead, swap to GxEPD2_750_T7_V2 in this typedef.
GxEPD2_BW<GxEPD2_750_T7, GxEPD2_750_T7::HEIGHT> display(
    GxEPD2_750_T7(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY)
);

void displayInit() {
  display.init(115200, /*initial=*/true, /*reset_duration=*/10, /*pulldown=*/false);
}

void displayHibernate() {
  display.hibernate();
}

// ─── BMP parsing helpers ────────────────────────────────────────────────────

static uint16_t readU16(const uint8_t* p) {
  return uint16_t(p[0]) | (uint16_t(p[1]) << 8);
}

static uint32_t readU32(const uint8_t* p) {
  return uint32_t(p[0]) | (uint32_t(p[1]) << 8)
       | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

bool displayDrawBmp(const uint8_t* bmp, size_t len) {
  if (len < 62 || bmp[0] != 'B' || bmp[1] != 'M') {
    Serial.println("[display] not a BMP");
    return false;
  }
  const uint32_t pixel_offset = readU32(bmp + 10);
  const int32_t  width        = (int32_t)readU32(bmp + 18);
  const int32_t  height_raw   = (int32_t)readU32(bmp + 22);
  const uint16_t bpp          = readU16(bmp + 28);

  const bool    flip_y = height_raw > 0;       // positive height = bottom-up
  const int32_t height = flip_y ? height_raw : -height_raw;

  if (bpp != 1 || width != 800 || height != 480) {
    Serial.printf("[display] unexpected BMP %ldx%ld@%ubpp\n", width, height, bpp);
    return false;
  }

  const int32_t row_size = ((width + 31) / 32) * 4;  // 4-byte padded
  if (pixel_offset + row_size * height > len) {
    Serial.println("[display] truncated BMP");
    return false;
  }

  const uint8_t* pixels = bmp + pixel_offset;

  display.setFullWindow();
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    for (int y = 0; y < height; y++) {
      const int bmp_row = flip_y ? (height - 1 - y) : y;
      const uint8_t* row = pixels + bmp_row * row_size;
      for (int x = 0; x < width; x++) {
        const uint8_t byte = row[x >> 3];
        const bool bit_set = (byte >> (7 - (x & 7))) & 1;
        // Pillow mode '1' BMPs encode 0 = black, 1 = white.
        if (!bit_set) {
          display.drawPixel(x, y, GxEPD_BLACK);
        }
      }
    }
  } while (display.nextPage());

  return true;
}

void displayDrawClockArea(const uint8_t* bitmap, int w, int h) {
  // Partial refresh updates just the clock window every minute.
  display.setPartialWindow(CLOCK_X, CLOCK_Y, CLOCK_W, CLOCK_H);
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    if (bitmap != nullptr) {
      const int x0 = CLOCK_X + (CLOCK_W - w) / 2;
      const int y0 = CLOCK_Y + (CLOCK_H - h) / 2;
      display.drawBitmap(x0, y0, bitmap, w, h, GxEPD_BLACK);
    }
  } while (display.nextPage());
}
