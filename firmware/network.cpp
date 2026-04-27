// network.cpp — WiFi, NTP, and HTTPS BMP download for the e-paper firmware.

#include "network.h"
#include "config.h"

#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>

bool networkConnectWifi(uint32_t timeout_ms) {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - started > timeout_ms) {
      Serial.println("[net] WiFi connect timeout");
      WiFi.disconnect(true);
      return false;
    }
    delay(200);
  }
  Serial.printf("[net] WiFi connected, IP=%s\n", WiFi.localIP().toString().c_str());
  return true;
}

void networkDisconnectWifi() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
}

bool networkSyncTime(uint32_t timeout_ms) {
  configTzTime(TZ_INFO, NTP_SERVER);
  const uint32_t started = millis();
  time_t now = 0;
  while (now < 1700000000) {  // ~2023-11-14 — anything earlier means NTP not done
    if (millis() - started > timeout_ms) {
      Serial.println("[net] NTP sync timeout");
      return false;
    }
    delay(200);
    time(&now);
  }
  struct tm t;
  localtime_r(&now, &t);
  Serial.printf("[net] NTP synced — local time %04d-%02d-%02d %02d:%02d:%02d\n",
                1900 + t.tm_year, t.tm_mon + 1, t.tm_mday,
                t.tm_hour, t.tm_min, t.tm_sec);
  return true;
}

uint8_t* networkDownloadBmp(const char* url, size_t* out_len) {
  *out_len = 0;

  WiFiClientSecure client;
  client.setInsecure();   // GitHub Pages cert chain isn't in our flash; trust the URL itself.

  HTTPClient http;
  if (!http.begin(client, url)) {
    Serial.println("[net] http.begin failed");
    return nullptr;
  }
  http.setTimeout(30 * 1000);

  const int code = http.GET();
  if (code != HTTP_CODE_OK) {
    Serial.printf("[net] HTTP %d\n", code);
    http.end();
    return nullptr;
  }

  const int content_len = http.getSize();
  if (content_len <= 0 || content_len > 200 * 1024) {
    Serial.printf("[net] suspicious content-length %d\n", content_len);
    http.end();
    return nullptr;
  }

  uint8_t* buf = (uint8_t*)malloc(content_len);
  if (!buf) {
    Serial.println("[net] malloc failed");
    http.end();
    return nullptr;
  }

  WiFiClient* stream = http.getStreamPtr();
  size_t total = 0;
  const uint32_t deadline = millis() + 60 * 1000;
  while (total < (size_t)content_len) {
    if (millis() > deadline) {
      Serial.println("[net] download timeout");
      free(buf);
      http.end();
      return nullptr;
    }
    const size_t avail = stream->available();
    if (avail == 0) {
      delay(10);
      continue;
    }
    const int read = stream->readBytes(buf + total, content_len - total);
    if (read <= 0) {
      delay(10);
      continue;
    }
    total += read;
  }
  http.end();

  Serial.printf("[net] downloaded %u bytes\n", (unsigned)total);
  *out_len = total;
  return buf;
}
