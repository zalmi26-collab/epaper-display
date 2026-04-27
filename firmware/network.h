// network.h — WiFi connection, NTP sync, and HTTPS BMP download.

#pragma once

#include <Arduino.h>
#include <stddef.h>
#include <stdint.h>

bool networkConnectWifi(uint32_t timeout_ms);
void networkDisconnectWifi();

// Blocking — returns true if NTP came back with a sane epoch.
bool networkSyncTime(uint32_t timeout_ms);

// Downloads the BMP into a heap buffer the caller must free().
// Returns nullptr on failure.
uint8_t* networkDownloadBmp(const char* url, size_t* out_len);
