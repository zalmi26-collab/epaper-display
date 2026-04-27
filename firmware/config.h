// config.h — fill in WiFi credentials and the gh-pages URL once,
// then upload to the XIAO ESP32-C3.

#pragma once

// ── WiFi credentials ────────────────────────────────────────────────────────
#define WIFI_SSID     "YOUR_SSID"
#define WIFI_PASSWORD "YOUR_PASSWORD"

// ── Where to download the rendered BMP ──────────────────────────────────────
// After pushing the project to GitHub and enabling Pages on the gh-pages
// branch, this URL hosts the latest 800x480 1-bit BMP refreshed hourly.
#define IMAGE_URL "https://YOUR_USERNAME.github.io/YOUR_REPO/display.bmp"

// ── Time sync ───────────────────────────────────────────────────────────────
#define NTP_SERVER "pool.ntp.org"
// Israel timezone: standard +2, daylight saving last Friday before April
// 2nd / last Sunday in October.
#define TZ_INFO    "IST-2IDT,M3.4.4/26,M10.5.0"

// ── Schedule ────────────────────────────────────────────────────────────────
#define NIGHT_START_HOUR 23   // inclusive — switch to night mode
#define NIGHT_END_HOUR    5   // exclusive — wake into normal day mode

// ── Clock area on the panel (must match server/builder.py CLOCK_AREA) ──────
#define CLOCK_X       520
#define CLOCK_Y         0
#define CLOCK_W       280
#define CLOCK_H       120

// ── Pin assignments (XIAO ESP32-C3 → Waveshare 7.5" V2 e-paper) ─────────────
// Verify these against your wiring before first upload.
// XIAO labels are silk-screen pin numbers (D0..D10), GPIO numbers in comments.
#define EPD_CS    3   // D1  / GPIO3
#define EPD_DC    4   // D2  / GPIO4
#define EPD_RST   5   // D3  / GPIO5
#define EPD_BUSY  6   // D4  / GPIO6
// SPI hardware pins are fixed on the XIAO C3:
//   SCK  = D8  / GPIO8
//   MOSI = D10 / GPIO10
//   MISO = D9  / GPIO9 (unused by e-paper)

// ── Battery measurement ─────────────────────────────────────────────────────
// XIAO ESP32-C3 has no built-in battery divider — wire VBAT through a 1:2
// voltage divider (e.g. 100k / 100k) into A0/D0/GPIO2.
#define BATTERY_ADC_PIN 2   // GPIO2 (A0)
#define BATTERY_DIVIDER_RATIO 2.0f
#define BATTERY_VREF_MV       3300   // ESP32-C3 default reference (mV)
