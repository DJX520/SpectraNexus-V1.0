#include "BlackDeck.h"
void appMenu() {
    static const char* labels[] = {
        "AI Offline LLM", "WiFi Observer", "BLE Observer", "Infrared IR",
        "Sub-GHz Monitor", "NFC Tag Reader", "Tools", "Settings", "Showroom / FX"
    };
    static const char* hotkeys = "awbisntev";
    int sel = 0;
    for (;;) {
        int r = uiMenu("BLACKDECK V2.2", labels, 9, sel, hotkeys);
        if (r < 0) { uiMessage("BLACKDECK", "Hotkeys: A W B I S N T E V", 650); continue; }
        sel = r;
        switch (r) {
            case 0: appAi(); break;
            case 1: appWifi(); break;
            case 2: appBle(); break;
            case 3: appIr(); break;
            case 4: appSubGhz(); break;
            case 5: appNfc(); break;
            case 6: appTools(); break;
            case 7: appSettings(); break;
            case 8: appShowroom(); break;
        }
    }
}
