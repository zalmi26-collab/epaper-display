// epaper_display.ino — XIAO ESP32-C3 firmware for the family e-paper display.
//
// Wake schedule
//   • every minute (HH:MM:00) → partial refresh of just the clock window
//   • every hour  (HH:00:00) → WiFi up, download fresh BMP, full refresh, clock,
//                              update battery + error icons, WiFi down
//   • night (23:00 → 05:00)   → after the 23:00 full refresh, sleep ~6 hours
//                              continuously instead of waking every minute
//
// State that survives deep sleep is held in RTC slow memory (RTC_DATA_ATTR).

#include "config.h"
#include "clock.h"
#include "display.h"
#include "indicators.h"
#include "network.h"
#include "power.h"

#include <Arduino.h>
#include <esp_sleep.h>
#include <time.h>

// ─── Persistent counters across deep sleep ──────────────────────────────────
RTC_DATA_ATTR int      g_consecutive_dl_failures   = 0;
RTC_DATA_ATTR uint32_t g_last_successful_refresh   = 0;   // epoch seconds
RTC_DATA_ATTR int      g_last_full_refresh_hour    = -1;

// ─── Forward declarations ───────────────────────────────────────────────────
static bool isNightHour(int hour);
static uint32_t secondsUntilDayWake(time_t now);
static void doHourlyRefresh(time_t* now_inout);
static void doMinuteClockUpdate(time_t now);
static bool errorIndicatorRequired(time_t now);

// ─── Setup-only firmware (deep sleep wakes invoke setup() afresh) ───────────
void setup() {
  Serial.begin(115200);
  delay(50);
  Serial.println();
  Serial.println("=== epaper boot ===");

  // Determine wake reason — anything other than TIMER counts as cold boot.
  const esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
  const bool is_cold_boot = (cause != ESP_SLEEP_WAKEUP_TIMER);

  // Initialize the panel up-front so all draw calls below can use it.
  displayInit();

  // Read RTC time. After cold boot it's epoch zero; after a wake it's correct.
  time_t now = time(nullptr);
  bool time_known = (now > 1700000000);

  // Heuristic for whether this wake is the "top of the hour" boundary.
  bool is_hourly_boot;
  if (is_cold_boot || !time_known) {
    is_hourly_boot = true;  // first boot — treat as hourly
  } else {
    struct tm t;
    localtime_r(&now, &t);
    is_hourly_boot = (t.tm_min == 0);
  }

  if (is_hourly_boot) {
    doHourlyRefresh(&now);
    time_known = (now > 1700000000);
  } else {
    doMinuteClockUpdate(now);
  }

  displayHibernate();

  // ── Plan the next wake ──
  uint32_t sleep_secs;
  if (!time_known) {
    // We failed to learn the time — try again in a minute.
    sleep_secs = 60;
  } else {
    struct tm t;
    localtime_r(&now, &t);
    if (isNightHour(t.tm_hour)) {
      sleep_secs = secondsUntilDayWake(now);
    } else {
      // Aim for the next minute boundary, with sane bounds.
      sleep_secs = powerSecondsUntilNextMinute(30, 70);
    }
  }
  powerDeepSleep(sleep_secs);
}

void loop() {
  // never reached — setup() always ends in deep sleep
}

// ─── Hourly path ────────────────────────────────────────────────────────────
static void doHourlyRefresh(time_t* now_inout) {
  if (!networkConnectWifi(30000)) {
    g_consecutive_dl_failures++;
    Serial.printf("[main] WiFi failed (%d in a row)\n", g_consecutive_dl_failures);
    return;
  }

  // First boot or unsynced clock — get the time before doing anything else.
  if (*now_inout < 1700000000) {
    if (!networkSyncTime(15000)) {
      networkDisconnectWifi();
      g_consecutive_dl_failures++;
      return;
    }
    time(now_inout);
  }

  size_t bmp_len = 0;
  uint8_t* bmp = networkDownloadBmp(IMAGE_URL, &bmp_len);
  networkDisconnectWifi();

  bool drew = false;
  if (bmp != nullptr) {
    drew = displayDrawBmp(bmp, bmp_len);
    free(bmp);
  }

  if (drew) {
    g_consecutive_dl_failures = 0;
    g_last_successful_refresh = (uint32_t)*now_inout;
    struct tm t;
    localtime_r(now_inout, &t);
    g_last_full_refresh_hour = t.tm_hour;
  } else {
    g_consecutive_dl_failures++;
    Serial.printf("[main] download/draw failed (%d in a row)\n", g_consecutive_dl_failures);
  }

  // Always overlay clock + indicators on top of whatever is now on the panel.
  if (*now_inout > 1700000000) {
    struct tm t;
    localtime_r(now_inout, &t);
    if (!isNightHour(t.tm_hour)) {
      clockDrawTime(t.tm_hour, t.tm_min);
    }
  }

  const uint32_t mv = powerReadBatteryMv();
  const BatteryLevel level = powerClassify(mv);
  const bool show_error = errorIndicatorRequired(*now_inout);
  Serial.printf("[main] battery=%u mV (level=%d) show_error=%d\n",
                (unsigned)mv, (int)level, show_error);
  indicatorsDraw(level, show_error);
}

// ─── Minute path ────────────────────────────────────────────────────────────
static void doMinuteClockUpdate(time_t now) {
  if (now < 1700000000) return;  // unsynced — refuse to draw
  struct tm t;
  localtime_r(&now, &t);
  if (isNightHour(t.tm_hour)) return;  // shouldn't happen — we sleep through nights
  clockDrawTime(t.tm_hour, t.tm_min);
}

// ─── Helpers ────────────────────────────────────────────────────────────────
static bool isNightHour(int hour) {
  return (hour >= NIGHT_START_HOUR) || (hour < NIGHT_END_HOUR);
}

static uint32_t secondsUntilDayWake(time_t now) {
  struct tm t;
  localtime_r(&now, &t);
  t.tm_sec = 0;
  t.tm_min = 0;
  if (t.tm_hour >= NIGHT_START_HOUR) {
    // Late evening — wake at tomorrow's NIGHT_END_HOUR
    t.tm_mday += 1;
  }
  // (else: early morning hours of today — wake at today's NIGHT_END_HOUR)
  t.tm_hour = NIGHT_END_HOUR;
  const time_t target = mktime(&t);
  if (target <= now) return 60;
  return (uint32_t)(target - now);
}

static bool errorIndicatorRequired(time_t now) {
  if (g_consecutive_dl_failures >= 3) return true;
  if (g_last_successful_refresh == 0) return true;  // never refreshed yet
  if ((uint32_t)now - g_last_successful_refresh > 2 * 60 * 60) return true;  // >2 hrs stale
  return false;
}
