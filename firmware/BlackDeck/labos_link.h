#pragma once
#include <Arduino.h>

// ASCII commands: L5|<request_id>|HELLO / INFO / WIFI_SCAN / BLE_SCAN /
//                 RF_SAMPLE / NFC_SCAN
// ASCII responses: LAB5|<request_id>|begin|{...}
//                  LAB5|<request_id>|item|{...}
//                  LAB5|<request_id>|end|{...}
//                  LAB5|<request_id>|error|{...}
// Each line is <= 512 bytes. No arbitrary code execution or TX commands.
void labosHandleCommand(const String& line);
void labosSend(uint32_t req, const char* type, const String& json);
String labosQuote(const String& value);
void labosWifiScan(uint32_t req);
void labosBleScan(uint32_t req);
void labosRfSample(uint32_t req, float mhz = 433.92f);
void labosNfcScan(uint32_t req);
bool labosNfcProbe(String& uid, String& tagType, String& error, String* ndefText = nullptr);
