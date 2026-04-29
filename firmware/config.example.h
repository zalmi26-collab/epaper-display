// config.example.h — template. Copy this file to config.h and fill in your
// WiFi credentials. config.h is gitignored so your password never reaches
// GitHub.
//
//   cp firmware/config.example.h firmware/config.h
//   # then edit firmware/config.h and set WIFI_SSID / WIFI_PASSWORD

#pragma once

// ── WiFi credentials ────────────────────────────────────────────────────────
#define WIFI_SSID     "YOUR_SSID"
#define WIFI_PASSWORD "YOUR_PASSWORD"

// ── Where to download the rendered BMP ──────────────────────────────────────
// After pushing the project to GitHub and enabling Pages on the gh-pages
// branch, this URL hosts the latest 800x480 1-bit BMP refreshed hourly.
#define IMAGE_URL "https://zalmi26-collab.github.io/epaper-display/display.bmp"

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

// ── Pin assignments (Seeed XIAO ePaper Driver Board V2 + 7.5" panel) ────────
// These are fixed by the carrier-board hardware and match the upstream
// Seeed/EpaperPix Arduino sketches. XIAO labels (D0..D10) shown with the
// matching GPIO numbers.
#define EPD_CS    3   // D1 / GPIO3
#define EPD_DC    5   // D3 / GPIO5
#define EPD_RST   2   // D0 / GPIO2
#define EPD_BUSY  4   // D2 / GPIO4
// SPI hardware pins are fixed on the XIAO C3:
//   SCK  = D8  / GPIO8
//   MOSI = D10 / GPIO10
//   MISO = D9  / GPIO9 (unused by e-paper)

// ── Battery measurement ─────────────────────────────────────────────────────
// The Seeed XIAO ePaper Driver Board does not expose a battery-voltage
// divider on any free GPIO — every ADC-capable pin (GPIO 2..5) is taken by
// the panel SPI signals above. With BATTERY_ADC_PIN < 0 the firmware skips
// the ADC read and the battery icon is always drawn as "high".
#define BATTERY_ADC_PIN       -1
#define BATTERY_DIVIDER_RATIO 2.0f
#define BATTERY_VREF_MV       3300
