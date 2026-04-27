// indicators.h — battery icon and error X drawn in the bottom-left corner.

#pragma once

#include "power.h"

// Partial refresh of just the indicators region (bottom-left corner).
// Pass show_error = true to draw the X mark next to the battery.
void indicatorsDraw(BatteryLevel level, bool show_error);
