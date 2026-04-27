// clock.cpp — composes "HH:MM" from PROGMEM glyphs and writes it to the
// e-paper's reserved clock window via partial refresh.

#include "clock.h"
#include "config.h"
#include "display.h"
#include "fonts/clock_font.h"

#include <Arduino.h>
#include <pgmspace.h>
#include <stdio.h>
#include <string.h>

// Composed buffer: 5 glyphs side by side, 56 px each → 280 px wide × 100 px high.
constexpr int N_CHARS = 5;
constexpr int CLOCK_BMP_W = CLOCK_GLYPH_W * N_CHARS;          // 280
constexpr int CLOCK_BMP_H = CLOCK_GLYPH_H;                     // 100
constexpr int CLOCK_BMP_ROW_BYTES = CLOCK_GLYPH_ROW_BYTES * N_CHARS;  // 35
constexpr int CLOCK_BMP_BYTES = CLOCK_BMP_ROW_BYTES * CLOCK_BMP_H;    // 3500

static uint8_t composed_bitmap[CLOCK_BMP_BYTES];

void clockDrawTime(int hour, int minute) {
  if (hour < 0) hour = 0;
  if (hour > 23) hour = 23;
  if (minute < 0) minute = 0;
  if (minute > 59) minute = 59;

  char text[6];
  snprintf(text, sizeof(text), "%02d:%02d", hour, minute);

  memset(composed_bitmap, 0, CLOCK_BMP_BYTES);

  for (int g = 0; g < N_CHARS; g++) {
    const uint8_t* glyph = clockGlyphFor(text[g]);
    if (glyph == nullptr) continue;
    for (int row = 0; row < CLOCK_GLYPH_H; row++) {
      uint8_t* dst = composed_bitmap
                   + row * CLOCK_BMP_ROW_BYTES
                   + g * CLOCK_GLYPH_ROW_BYTES;
      // glyph data lives in PROGMEM — copy with memcpy_P.
      memcpy_P(dst, glyph + row * CLOCK_GLYPH_ROW_BYTES, CLOCK_GLYPH_ROW_BYTES);
    }
  }

  displayDrawClockArea(composed_bitmap, CLOCK_BMP_W, CLOCK_BMP_H);
}
