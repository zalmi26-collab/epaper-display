// power.cpp — ADC battery sampling and deep-sleep utilities.

#include "power.h"
#include "config.h"

#include <Arduino.h>
#include <esp_sleep.h>
#include <time.h>

uint32_t powerReadBatteryMv() {
  // Take 10 samples and average; the ADC on ESP32-C3 is noisy.
  analogReadResolution(12);
  analogSetPinAttenuation(BATTERY_ADC_PIN, ADC_11db);  // up to ~3.3 V on the pin

  uint32_t sum = 0;
  const int samples = 10;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(BATTERY_ADC_PIN);
    delay(2);
  }
  const uint32_t mean = sum / samples;
  if (mean == 0) return 0;

  // Convert ADC counts (0..4095) → mV at the pin → mV at the battery.
  const uint32_t mv_at_pin = (mean * BATTERY_VREF_MV) / 4095;
  return (uint32_t)(mv_at_pin * BATTERY_DIVIDER_RATIO);
}

BatteryLevel powerClassify(uint32_t mv) {
  if (mv >= 3900) return BATTERY_HIGH;
  if (mv >= 3700) return BATTERY_MED;
  if (mv >= 3500) return BATTERY_LOW;
  return BATTERY_CRITICAL;
}

uint32_t powerSecondsUntilNextMinute(uint32_t min_seconds, uint32_t max_seconds) {
  time_t now = time(nullptr);
  struct tm t;
  localtime_r(&now, &t);
  uint32_t to_next = 60 - t.tm_sec;
  if (to_next == 0) to_next = 60;
  if (to_next < min_seconds) to_next = min_seconds;
  if (to_next > max_seconds) to_next = max_seconds;
  return to_next;
}

[[noreturn]] void powerDeepSleep(uint32_t seconds) {
  Serial.printf("[power] sleeping for %u seconds\n", (unsigned)seconds);
  Serial.flush();
  esp_sleep_enable_timer_wakeup((uint64_t)seconds * 1000000ULL);
  esp_deep_sleep_start();
  // Unreachable
  while (true) {}
}
