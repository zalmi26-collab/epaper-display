// display.h — thin wrapper over GxEPD2 for the Waveshare 7.5" 800x480 V2 panel.
//
// Public API:
//   displayInit()                   — once per boot before any draw call
//   displayDrawBmp(buf, len)        — full refresh from a 1-bit BMP buffer
//   displayDrawClockArea(buf, w, h) — partial refresh of the top-right clock
//   displayHibernate()              — power-down the panel before deep sleep

#pragma once

#include <Arduino.h>
#include <stddef.h>
#include <stdint.h>

void displayInit();
bool displayDrawBmp(const uint8_t* bmp, size_t len);
void displayDrawClockArea(const uint8_t* bitmap, int w, int h);
void displayHibernate();
