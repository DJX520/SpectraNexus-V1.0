/* BLACKDECK V1.3 FullAI — Cardputer-Adv + M5Stack Cap CC1101
 * Arduino-ESP32 / M5Cardputer 1.1+; no USB injection, RF jamming, or WiFi disruption.
 */
#include "BlackDeck.h"

void setup() {
    Serial.begin(SERIAL_BAUD);
    auto cfg = M5.config();
    M5Cardputer.begin(cfg, true); // official library owns both keyboard types
    M5Cardputer.Display.setRotation(1);
    settingsInit();
    inputSetup();
    uiInit();
    uiBootShow(); // all animation assets are generated; no extra bitmap files
    Serial.printf("[BD] boot=%s, freeheap=%u, flash=%u\n",
                  APP_VERSION, ESP.getFreeHeap(), ESP.getFlashChipSize());
}

void loop() { appMenu(); }
