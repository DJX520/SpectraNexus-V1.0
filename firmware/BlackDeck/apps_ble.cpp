/* NimBLE-Arduino 2.x passive discovery. getResults(duration_ms) is blocking.
 * Advertiser name heuristics must NOT be used to assert tracker identity.
 */
#include "BlackDeck.h"
#include <NimBLEDevice.h>
#include <vector>
#include "labos_link.h"

static void bleScan() {
    NimBLEDevice::init("BLACKDECK");
    NimBLEScan* scan = NimBLEDevice::getScan();
    scan->setActiveScan(false);
    scan->setInterval(96);
    scan->setWindow(60);
    uiMessage("BLE", "Scanning 6s...", 400);
    // NimBLE 2.x takes duration in milliseconds. No custom callbacks required.
    NimBLEScanResults results = scan->getResults(6000, false);
    std::vector<String> entries;
    int count = results.getCount();
    if (count > 40) count = 40;
    Serial.println("[BLE] address,rssi_dBm,name");
    for (int i = 0; i < count; ++i) {
        const NimBLEAdvertisedDevice* d = results.getDevice(i);
        if (!d) continue;
        String name = String(d->getName().c_str());
        if (!name.length()) name = "(unnamed)";
        String addr = String(d->getAddress().toString().c_str());
        const int rssi = d->getRSSI();
        entries.push_back(name + " " + String(rssi) + "dBm " + addr.substring(9));
        Serial.printf("[BLE],%s,%d,\"%s\"\n", addr.c_str(), rssi, labosQuote(name).c_str());
    }
    int sel = 0;
    uiPickDynamic("BLE advertisers", entries, sel);
    scan->clearResults();
    NimBLEDevice::deinit(true);
}

void appBle() {
    static const char* labels[] = {"Scan BLE advertisements", "About BLE data"};
    int sel = 0;
    for (;;) {
        int r = uiMenu("BLE observer", labels, 2, sel, nullptr);
        if (r < 0) return;
        sel = r;
        if (r == 0) bleScan();
        else uiMessage("BLE", "Names are not identity proof", 1400);
    }
}

// Passive advertisements only. Avoid mixing local UI with remote requests.
void labosBleScan(uint32_t req) {
    labosSend(req,"begin","{\"kind\":\"ble\",\"source\":\"adv\"}");
    NimBLEDevice::init("BLACKDECK");
    NimBLEScan* scan = NimBLEDevice::getScan();
    scan->setActiveScan(false);
    scan->setInterval(96);
    scan->setWindow(60);
    NimBLEScanResults results = scan->getResults(4000, false);
    int count = 0;
    for (int i = 0; i < results.getCount() && i < 32; ++i) {
        const NimBLEAdvertisedDevice* d = results.getDevice(i);
        if (!d) continue;
        String obj = "{\"address\":" + labosQuote(String(d->getAddress().toString().c_str()));
        obj += ",\"name\":" + labosQuote(String(d->getName().c_str()));
        obj += ",\"rssi\":" + String(d->getRSSI()) + "}";
        labosSend(req,"item",obj);
        ++count;
    }
    scan->clearResults();
    NimBLEDevice::deinit(true);
    labosSend(req,"end","{\"count\":"+String(count)+"}");
}
