#include "BlackDeck.h"
#include "labos_link.h"
#include <WiFi.h>

// ASCII framing + per-item JSON avoids allocating large documents on ESP32-S3.
String labosQuote(const String& value) {
    String out = "\"";
    const size_t limit = value.length() < 90 ? value.length() : 90;
    for (size_t i = 0; i < limit;) {
        const unsigned char c = (unsigned char)value[i];
        // Copy only complete UTF-8 sequences, never a truncated character.
        size_t width = 1;
        if (c >= 0xF0 && c <= 0xF4) width = 4;
        else if (c >= 0xE0 && c <= 0xEF) width = 3;
        else if (c >= 0xC2 && c <= 0xDF) width = 2;
        if (i + width > limit) break;
        if (width > 1) {
            bool valid = true;
            for (size_t j=1; j<width; ++j) {
                if (((unsigned char)value[i+j] & 0xC0) != 0x80) { valid = false; break; }
            }
            if (!valid) { out += '?'; ++i; continue; }
            for (size_t j=0; j<width; ++j) out += value[i+j];
            i += width;
        } else {
            if (c == '"' || c == '\\') { out += '\\'; out += (char)c; }
            else if (c == '\n') out += "\\n";
            else if (c == '\r') out += "\\r";
            else if (c == '\t') out += "\\t";
            else if (c < 32 || c >= 128) out += '?';
            else out += (char)c;
            ++i;
        }
    }
    return out + "\"";
}
void labosSend(uint32_t req, const char* type, const String& json) {
    Serial.printf("LAB5|%lu|%s|", (unsigned long)req, type);
    Serial.println(json);
}
static void bad(uint32_t req,const char* reason) {
    labosSend(req, "error", String("{\"message\":") + labosQuote(reason) + "}");
}
static void info(uint32_t req) {
    String data = "{\"firmware\":\"";
    data += APP_VERSION;
    data += "\",\"board\":\"";
    data += inputIsAdv() ? "Cardputer-Adv" : "Cardputer";
    data += "\",\"flash_bytes\":" + String(ESP.getFlashChipSize());
    data += ",\"free_heap\":" + String(ESP.getFreeHeap());
    data += ",\"psram\":" + String(ESP.getPsramSize());
    data += ",\"battery_pct\":" + String(M5Cardputer.Power.getBatteryLevel());
    data += ",\"ai_offline\":" + String(AI_OFFLINE_LLM ? "true" : "false");
    data += ",\"uptime_ms\":" + String(millis());
    data += "}";
    labosSend(req,"item",data);
    labosSend(req,"end","{\"count\":1}");
}
void labosHandleCommand(const String& line) {
    if (!line.startsWith("L5|")) return;
    int a = line.indexOf('|', 3);
    if (a < 0 || a > 15) return;
    String idText = line.substring(3,a);
    if (!idText.length() || idText.length()>8) return;
    for (size_t i=0; i<idText.length(); ++i) { char c=idText[i]; if (c<'0' || c>'9') return; }
    uint32_t id = (uint32_t)idText.toInt();
    String command = line.substring(a+1);
    command.trim();
    if (command=="HELLO") {
        labosSend(id,"item","{\"protocol\":\"LAB5\",\"device\":\"blackdeck\",\"cap\":\"U219\"}");
        labosSend(id,"end","{\"count\":1}");
    } else if (command=="INFO") info(id);
    else if (command=="WIFI_SCAN") labosWifiScan(id);
    else if (command=="BLE_SCAN") labosBleScan(id);
    else if (command=="RF_SAMPLE") labosRfSample(id, 433.92f);
    else if (command=="RF_SAMPLE_315") labosRfSample(id, 315.0f);
    else if (command=="RF_SAMPLE_868") labosRfSample(id, 868.0f);
    else if (command=="RF_SAMPLE_915") labosRfSample(id, 915.0f);
    else if (command=="NFC_SCAN") labosNfcScan(id);
    else bad(id, "command_not_allowed");
}
