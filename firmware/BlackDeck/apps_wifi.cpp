/* Passive WiFi survey, channel histogram, local connection.
 * No forged frames, deauthentication, portal interception, or credential capture.
 */
#include "BlackDeck.h"
#include <WiFi.h>
#include <vector>
#include "labos_link.h"

struct ScanAP { String ssid; String bssid; int rssi; int ch; uint8_t auth; };
static std::vector<ScanAP> aps;

static void scanAPs() {
    aps.clear();
    WiFi.mode(WIFI_STA);
    WiFi.disconnect(false, false);
    delay(90);
    const int n = WiFi.scanNetworks(false, true, false, 220);
    if (n < 0) { Serial.printf("[WiFi] scan err %d\n", n); return; }
    Serial.println("[WiFi] SSID,RSSI_dBm,channel,auth");
    for (int i = 0; i < n && i < 64; ++i) {
        ScanAP ap{WiFi.SSID(i), WiFi.BSSIDstr(i), WiFi.RSSI(i), WiFi.channel(i), uint8_t(WiFi.encryptionType(i))};
        if (ap.ssid.isEmpty()) ap.ssid = "(hidden)";
        aps.push_back(ap);
        Serial.printf("[WiFi],%s,%d,%d,%u\n", labosQuote(ap.ssid).c_str(), ap.rssi, ap.ch, ap.auth);
    }
    WiFi.scanDelete();
}

static void scanList() {
    uiMessage("WiFi", "Passive scan...", 300);
    scanAPs();
    std::vector<String> lines;
    lines.reserve(aps.size());
    for (auto& a : aps) lines.push_back(a.ssid + "  " + String(a.rssi) + "dBm ch" + String(a.ch));
    int selected = 0;
    uiPickDynamic("WiFi APs", lines, selected);
}

static void channelView() {
    if (aps.empty()) scanAPs();
    uint8_t channels[15] = {0};
    for (auto& a : aps) if (a.ch >= 1 && a.ch <= 14 && channels[a.ch] < 255) ++channels[a.ch];
    M5Cardputer.Display.fillScreen(gTheme.bg);
    uiHeader("WiFi Channel Load");
    for (int i = 1; i <= 14; ++i) {
        int h = min(78, int(channels[i] * 7));
        int x = 4 + (i - 1) * 16;
        M5Cardputer.Display.fillRect(x, 108 - h, 11, h, gTheme.accent);
        M5Cardputer.Display.setTextColor(gTheme.muted);
        M5Cardputer.Display.setCursor(x, 111);
        M5Cardputer.Display.print(i);
    }
    uiStatusBar("2.4G AP count");
    Serial.println("[WiFi] channel,AP_count");
    for (int i = 1; i <= 14; ++i) Serial.printf("[WiFi],%d,%u\n", i, channels[i]);
    while (true) { if (inputPoll().any) break; delay(10); }
}

bool netEnsureWifi() {
    if (WiFi.status() == WL_CONNECTED) return true;
    String ssid = uiReadString("SSID", "", 32);
    if (!ssid.length()) return false;
    String pass = uiReadString("Password (local)", "", 63);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid.c_str(), pass.c_str());
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 12000) {
        if (inputPoll().esc) break;
        delay(50);
    }
    if (WiFi.status() != WL_CONNECTED) {
        WiFi.disconnect(false, true);
        uiMessage("WiFi", "Connect failed / canceled", 1200);
        return false;
    }
    uiMessage("WiFi connected", WiFi.localIP().toString().c_str(), 1000);
    return true;
}
String netSsid() { return WiFi.status() == WL_CONNECTED ? WiFi.SSID() : String(""); }
String netIp() { return WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : String(""); }

void appWifi() {
    static const char* labels[] = {"Passive AP scan", "Channel overview", "Connect (own AP)", "Connection info", "WiFi off"};
    int sel = 0;
    for (;;) {
        int r = uiMenu("WiFi observer", labels, 5, sel, nullptr);
        if (r < 0) return;
        sel = r;
        switch (r) {
            case 0: scanList(); break;
            case 1: channelView(); break;
            case 2: netEnsureWifi(); break;
            case 3: {
                if (WiFi.status() == WL_CONNECTED)
                    uiMessage(WiFi.SSID().c_str(), WiFi.localIP().toString().c_str(), 1700);
                else uiMessage("WiFi", "Not connected", 900);
                break;
            }
            case 4: WiFi.disconnect(true, true); uiMessage("WiFi radio", "disconnected", 700); break;
        }
    }
}

// Serial LabOS V5 structured measurement; uses the same scan routine as the UI.
void labosWifiScan(uint32_t req) {
    labosSend(req,"begin","{\"kind\":\"wifi\",\"source\":\"adv\"}");
    scanAPs();
    int count = 0;
    for (const auto& a : aps) {
        String obj = "{\"ssid\":" + labosQuote(a.ssid);
        obj += ",\"bssid\":" + labosQuote(a.bssid);
        obj += ",\"rssi\":" + String(a.rssi);
        obj += ",\"channel\":" + String(a.ch);
        obj += ",\"auth\":" + String(a.auth) + "}";
        labosSend(req,"item",obj);
        count++;
    }
    labosSend(req,"end","{\"count\":"+String(count)+"}");
}
