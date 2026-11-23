/* M5Stack Cap CC1101 U219: RadioLib receiver-only instrumentation.
 * Source of GPIO & band logic: M5Stack Cap CC1101 Arduino quick start.
 * Read-only RF operations; no replay, brute force, jammer or continuous TX.
 */
#include "BlackDeck.h"
#if HAS_CC1101
#include <RadioLib.h>
#include <SPI.h>
#include <math.h>
#include "labos_link.h"

static CC1101 radio = new Module(CC1101_CS, CC1101_GDO0, RADIOLIB_NC, RADIOLIB_NC);
static bool ready = false;
static float freq = 433.92f;
static int16_t lastError = 0;

// RadioLib 8.x requires frequency in Hz (integer); the UI frequency is MHz.
// Do not use RADIOLIB_UNIT_MEGA(freq) for fractional MHz: that macro casts
// freq to uint32_t before multiplying, discarding .92 of 433.92 MHz.
static uint32_t mhzToHz(float mhz) {
    return static_cast<uint32_t>(static_cast<double>(mhz) * 1000000.0 + 0.5);
}

static bool selectBand(float mhz) {
    bool sw0, sw1;
    if (mhz >= 300.0f && mhz < 350.0f) { sw0 = false; sw1 = true; }
    else if (mhz >= 400.0f && mhz < 500.0f) { sw0 = true; sw1 = false; }
    else if (mhz >= 820.0f && mhz <= 960.0f) { sw0 = true; sw1 = true; }
    else return false;
    digitalWrite(CC1101_RF_SW0, sw0 ? HIGH : LOW);
    // CC1101 GDO2 drives second RF switch line on Cap U219.
    const uint8_t map = RADIOLIB_CC1101_GDOX_HW_TO_0 |
       (sw1 ? RADIOLIB_CC1101_GDO2_INV : RADIOLIB_CC1101_GDO2_NORM);
    lastError = radio.setDIOMapping(2, map);
    return lastError == RADIOLIB_ERR_NONE;
}

static bool initRf() {
    if (ready) return true;
    pinMode(CAP_POWER_EN, OUTPUT);
    digitalWrite(CAP_POWER_EN, HIGH);  // RF/NFC cap power gate
    pinMode(CAP_NFC_CS, OUTPUT);
    digitalWrite(CAP_NFC_CS, HIGH);   // deselect NFC on shared SPI bus
    pinMode(CC1101_CS, OUTPUT);
    digitalWrite(CC1101_CS, HIGH);
    pinMode(CC1101_RF_SW0, OUTPUT);
    SPI.begin(CC1101_SCK, CC1101_MISO, CC1101_MOSI, CC1101_CS);
    delay(25);
    // RadioLib 8.0+: CC1101::begin() accepts ConfigFSK_t only.
    // Keep the original modem configuration (2.4 kbps, 25.4 kHz deviation,
    // 58 kHz RX bandwidth, 0 dBm configured TX power, 16-bit preamble).
    // This firmware only uses receive and RSSI functions.
    ConfigFSK_t rfConfig;
    rfConfig.frequency = mhzToHz(freq);      // 433920000 Hz, NOT 433.92 Hz
    rfConfig.bitRate = 2400;                // bps
    rfConfig.frequencyDeviation = 25400;    // Hz
    rfConfig.receiverBandwidth = 58000;     // Hz
    rfConfig.power = 0;                     // dBm; no TX used in this app
    rfConfig.preambleLength = 16;           // bits
    lastError = radio.begin(rfConfig);
    if (lastError != RADIOLIB_ERR_NONE) return false;
    if (!selectBand(freq)) return false;
    ready = true;
    return true;
}

static bool startRx() {
    // Select the matching RF path before enabling the receiver.
    if (!selectBand(freq)) return false;
    lastError = radio.startReceive();
    return lastError == RADIOLIB_ERR_NONE;
}

static void reportError() {
    char msg[42];
    snprintf(msg, sizeof(msg), "RadioLib error: %d", (int)lastError);
    Serial.printf("[RF] %s\n", msg);
    uiMessage("CC1101 initialization", msg, 1900);
}

static void rssiMonitor() {
    if (!initRf() || !startRx()) { reportError(); return; }
    auto& d = M5Cardputer.Display;
    d.fillScreen(gTheme.bg);
    uiHeader("RF LIVE 433.92 MHz");
    uiStatusBar("RX only / key=back");
    // Mini oscilloscope: each point is a CC1101 RSSI reading, not an SDR waveform.
    const int left=9, top=62, width=220, height=51;
    d.drawRect(left,top,width,height,gTheme.muted);
    for(int j=1;j<4;j++)
        d.drawFastHLine(left+1,top+height*j/4,width-2,gTheme.panel);
    int prior=-1, n=0;
    unsigned long lastUi=0;
    while (true) {
        if (inputPoll().any) break;
        if (millis()-lastUi>=90) {
            lastUi=millis();
            const float rssi=radio.getRSSI();
            if (!isfinite(rssi)) { delay(2); continue; }
            const int level=constrain(int((rssi+115.0f)*2.0f),0,100);
            // Clear only the changing value region (less flicker than full-screen).
            d.fillRect(0,20,240,41,gTheme.bg);
            d.setTextSize(2);d.setTextColor(gTheme.accent);
            d.setCursor(12,24); d.printf("%5.1f dBm",rssi);
            d.fillRect(164,30,68,9,gTheme.panel);
            d.fillRect(164,30,68*level/100,9,gTheme.accent2);
            d.setTextColor(gTheme.muted); d.setTextSize(1);
            d.setCursor(164,44); d.print("REAL RSSI");
            // Sliding two-point line: fixed-size plot with no heap allocation.
            if(n>=width-3) {d.fillRect(left+1,top+1,width-2,height-2,gTheme.bg);n=0;prior=-1;}
            int y=top+height-2-(level*(height-4))/100;
            int x=left+1+n;
            if(prior>=0) d.drawLine(x-1,prior,x,y,gTheme.accent2);
            else d.drawPixel(x,y,gTheme.accent2);
            prior=y;n++;
            Serial.printf("[RF] RSSI,%.2f,%.1f\n",freq,rssi);
        }
        delay(7);
    }
    radio.standby();
}

static void localSpectrum() {
    if (!initRf()) { reportError(); return; }
    // One RF matching band only; 433 MHz antenna. Not a calibrated spectrum analyzer.
    constexpr int N = 28;
    float rssi[N];
    M5Cardputer.Display.fillScreen(gTheme.bg);
    uiHeader("433 MHz survey (RX)");
    Serial.println("[RF] freq_MHz,RSSI_dBm");
    for (int i = 0; i < N; ++i) {
        float f = 432.40f + 0.11f * i;
        radio.standby();  // change frequency outside active RX mode
        lastError = radio.setFrequency(mhzToHz(f));
        if (lastError != RADIOLIB_ERR_NONE) { rssi[i] = -120.0f; continue; }
        freq = f;
        if (!startRx()) { rssi[i] = -120.0f; continue; }
        delay(15);
        rssi[i] = radio.getRSSI();
        Serial.printf("[RF],%.3f,%.1f\n", f, rssi[i]);
    }
    radio.standby();
    for (int i = 0; i < N; ++i) {
        int h = constrain(int((rssi[i] + 115.f) * 1.1f), 1, 84);
        int x = 6 + i * 8;
        M5Cardputer.Display.fillRect(x, 111 - h, 6, h, h > 60 ? gTheme.accent2 : gTheme.accent);
    }
    uiStatusBar("432.4-435.4 MHz");
    while (true) { if (inputPoll().any) break; delay(10); }
    // Restore the local receiver's default channel; remote LAB5 samples choose
    // their own band independently. Never reference remote request variables here.
    freq = 433.92f;
    lastError = radio.setFrequency(mhzToHz(freq));
    if (lastError == RADIOLIB_ERR_NONE) selectBand(freq);
}
#endif

void appSubGhz() {
#if HAS_CC1101
    static const char* labels[] = {"RSSI 433.92 MHz", "433 MHz signal survey", "Hardware / error status"};
    int selected = 0;
    for (;;) {
        int r = uiMenu("Cap CC1101 RX", labels, 3, selected, nullptr);
        if (r < 0) return;
        selected = r;
        if (r == 0) rssiMonitor();
        else if (r == 1) localSpectrum();
        else {
            char msg[48];
            snprintf(msg, sizeof(msg), "CS=5 GDO0=15 err=%d", (int)lastError);
            uiMessage(ready ? "CC1101 initialized" : "CC1101 not initialized", msg, 1500);
        }
    }
#else
    uiMessage("CC1101 disabled", "HAS_CC1101=0", 1000);
#endif
}

void labosRfSample(uint32_t req, float targetMhz) {
#if HAS_CC1101
    if (!initRf()) {
        labosSend(req,"error",String("{\"code\":\"rf_init\",\"errno\":") + String(lastError) + "}");
        return;
    }
    // RX only. Install the matching 315/433/868/915 MHz antenna before scanning.
    radio.standby();
    if (!((targetMhz == 315.0f) || (targetMhz == 433.92f) || (targetMhz == 868.0f) || (targetMhz == 915.0f))) {
        labosSend(req,"error","{\"message\":\"unsupported_band\"}");return;
    }
    freq = targetMhz;
    lastError = radio.setFrequency(mhzToHz(freq));
    if (lastError != RADIOLIB_ERR_NONE || !startRx()) {
        labosSend(req,"error",String("{\"code\":\"rf_receive\",\"errno\":") + String(lastError) + "}");
        return;
    }
    labosSend(req,"begin","{\"kind\":\"rf\",\"frequency_hz\":"+String(mhzToHz(freq))+"}");
    for (int i=0;i<24;i++) {
        delay(60);
        String obj = "{\"frequency_hz\":"+String(mhzToHz(freq))+",\"rssi\":";
        obj += String(radio.getRSSI(), 2);
        obj += ",\"sample_index\":" + String(i) + "}";
        labosSend(req,"item",obj);
    }
    radio.standby();
    // Restore BOTH the tracked frequency and the CC1101 hardware registers.
    // Without this the next local 433 MHz RSSI view could actually monitor the prior band.
    freq = 433.92f;
    const int16_t restoreErr = radio.setFrequency(mhzToHz(freq));
    if (restoreErr != RADIOLIB_ERR_NONE || !selectBand(freq)) {
        ready = false;  // Reinitialize on next use instead of using stale RF state.
        Serial.printf("[RF] restore 433.92 MHz failed: %d\n", (int)restoreErr);
    }
    labosSend(req,"end","{\"count\":24}");
#else
    labosSend(req,"error","{\"message\":\"rf_disabled\"}");
#endif
}
