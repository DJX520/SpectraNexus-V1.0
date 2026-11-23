#include "BlackDeck.h"
#include <Preferences.h>

static void sysInfo() {
    M5Cardputer.Display.fillScreen(gTheme.bg);
    uiHeader("Diagnostics");
    M5Cardputer.Display.setTextSize(1);
    M5Cardputer.Display.setTextColor(gTheme.fg);
    M5Cardputer.Display.setCursor(6, 24);
    M5Cardputer.Display.printf("Chip:  %s\n", ESP.getChipModel());
    M5Cardputer.Display.printf("Board: %s\n", inputIsAdv() ? "ADV" : "Classic");
    M5Cardputer.Display.printf("Flash: %u KB\n", ESP.getFlashChipSize()/1024);
    M5Cardputer.Display.printf("PSRAM: %u KB\n", ESP.getPsramSize()/1024);
    M5Cardputer.Display.printf("Heap:  %u KB\n", ESP.getFreeHeap()/1024);
    M5Cardputer.Display.printf("Min:   %u KB\n", ESP.getMinFreeHeap()/1024);
    M5Cardputer.Display.printf("Batt:  %d%%\n", M5Cardputer.Power.getBatteryLevel());
    uiStatusBar("any key");
    while (true) { if (inputPoll().any) break; delay(10); }
}

void appTools() {
    static const char* labels[] = {"Device diagnostics", "LCD full white test", "Keyboard hint", "Reboot"};
    int sel = 0;
    while (true) {
        int r = uiMenu("Tools", labels, 4, sel, nullptr);
        if (r < 0) return;
        sel = r;
        switch (r) {
            case 0: sysInfo(); break;
            case 1: {
                M5Cardputer.Display.fillScreen(0xFFFF);
                while (!inputPoll().any) delay(10);
                M5Cardputer.Display.setBrightness(settingsGet("brightness", String(BRIGHTNESS)).toInt());
                break;
            }
            case 2: uiMessage("Key guide", "; . move  ENTER choose", 1400); break;
            case 3: if (uiConfirm("Reboot device?")) ESP.restart(); break;
        }
    }
}

void appSettings() {
    static const char* labels[] = {"Theme", "Brightness", "Erase settings"};
    static const char* themes[] = {"VIOLET", "CYBER", "MATRIX", "E-INK", "SYNTHWAVE", "BLOOD"};
    static const char* values[] = {"32", "64", "128", "192", "255"};
    static const uint8_t v[] = {32,64,128,192,255};
    int sel = 0;
    while (true) {
        int r = uiMenu("Settings", labels, 3, sel, nullptr);
        if (r < 0) return;
        sel = r;
        if (r == 0) {
            int idx = uiMenu("Theme", themes, 6, 0, nullptr);
            if (idx >= 0) { uiSetTheme(idx); settingsSet("theme", String(idx)); }
        } else if (r == 1) {
            int idx = uiMenu("Brightness", values, 5, 2, nullptr);
            if (idx >= 0) {
                M5Cardputer.Display.setBrightness(v[idx]);
                settingsSet("brightness", String(v[idx]));
            }
        } else if (uiConfirm("Erase settings / reboot?")) {
            Preferences p;
            p.begin("blackdeck", false); p.clear(); p.end();
            ESP.restart();
        }
    }
}
