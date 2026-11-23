/* IR transmitter for user-owned devices; ESP32 Arduino core 3.x LEDC 38kHz.
 * Only one explicitly entered NEC code is sent, no mass power-off broadcast.
 */
#include "BlackDeck.h"
static bool irReady = false;
static void irSetup() {
    if (irReady) return;
    irReady = ledcAttach(PIN_IR_TX, 38000, 8);
    if (irReady) ledcWrite(PIN_IR_TX, 0);
}
static void mark(uint32_t us) { ledcWrite(PIN_IR_TX, 128); delayMicroseconds(us); }
static void space(uint32_t us) { ledcWrite(PIN_IR_TX, 0); delayMicroseconds(us); }
static void nec32(uint32_t data) {
    mark(9000); space(4500);
    for (uint8_t i = 0; i < 32; ++i) {
        mark(560); space((data & (1UL << i)) ? 1690 : 560);
    }
    mark(560); space(5000);
}
void appIr() {
    irSetup();
    if (!irReady) { uiMessage("IR PWM", "LEDC attach failed", 1000); return; }
    static const char* labels[] = {"Send my NEC code", "IR hardware info"};
    int selected = 0;
    for (;;) {
        int r = uiMenu("Infrared IR", labels, 2, selected, nullptr);
        if (r < 0) return;
        selected = r;
        if (r == 1) { uiMessage("IR GPIO44", "38kHz LEDC carrier", 1300); continue; }
        String hex = uiReadString("NEC hex 8 digits", "", 10);
        if (!hex.length()) continue;
        const char* p = hex.c_str();
        if (hex.startsWith("0x") || hex.startsWith("0X")) p += 2;
        if (strlen(p) != 8) { uiMessage("NEC", "Enter 8 hex digits", 1300); continue; }
        char* end = nullptr;
        uint32_t code = uint32_t(strtoul(p, &end, 16));
        if (!end || *end) { uiMessage("NEC", "Invalid hex code", 1300); continue; }
        if (!uiConfirm("Send code to OWN device?")) continue;
        nec32(code);
        Serial.printf("[IR] NEC,0x%08lX\n", (unsigned long)code);
        uiMessage("NEC sent", hex.c_str(), 1000);
    }
}
