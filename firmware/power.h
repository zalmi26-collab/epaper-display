// power.h — battery sampling and deep-sleep helpers for XIAO ESP32-C3.

#pragma once

#include <stdint.h>

enum BatteryLevel {
  BATTERY_HIGH,
  BATTERY_MED,
  BATTERY_LOW,
  BATTERY_CRITICAL,
};

// Sample the battery via the configured ADC pin and divider ratio.
// Returns millivolts at the battery (post-divider). 0 on read failure.
uint32_t powerReadBatteryMv();

// Quantize a raw battery mV to one of four bands.
BatteryLevel powerClassify(uint32_t mv);

// Compute seconds to sleep so we wake very close to the next minute boundary.
// Returns at least min_seconds (clamped) and at most max_seconds.
uint32_t powerSecondsUntilNextMinute(uint32_t min_seconds, uint32_t max_seconds);

// Drop into deep sleep for the given number of seconds. Does not return.
[[noreturn]] void powerDeepSleep(uint32_t seconds);
