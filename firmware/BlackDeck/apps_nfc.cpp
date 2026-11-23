/* Read-only ISO14443A tag inventory for personal, authorized test tags.
 * M5Stack Cap CC1101 U219 ST25R3916 driver integration.
 * Use M5UnitUnifiedNFC >= version in official Cardputer-Adv example.
 * No key guessing, tag emulation, or writing.
 */
#include "BlackDeck.h"
#include "labos_link.h"

#if LABOS_NFC_ENABLED
#include <M5Unified.h>
#include <M5UnitUnified.h>
#include <M5UnitUnifiedNFC.h>
#include <M5Utility.h>
#include <wiring/m5_unit_unified_wiring.hpp>

static m5::unit::UnitUnified gNfcBus;
static m5::unit::CapCC1101NFC gNfcUnit;
static m5::nfc::NFCLayerA gNfcA{gNfcUnit};
static bool gNfcInitialized = false;
static bool gNfcFailed = false;

static bool nfcInit() {
    if (gNfcInitialized) return true;
    if (gNfcFailed) return false;
    pinMode(CAP_POWER_EN, OUTPUT);
    digitalWrite(CAP_POWER_EN, HIGH);
    pinMode(CC1101_CS, OUTPUT);
    digitalWrite(CC1101_CS, HIGH);
    pinMode(CAP_NFC_CS, OUTPUT);
    digitalWrite(CAP_NFC_CS, HIGH);
    delay(30);
    // Official Cap example: 10 MHz SPI, mode 1. Shared bus with CC1101.
    gNfcInitialized = m5::unit::wiring::addSPI(gNfcBus, gNfcUnit, 10000000, 1)
                      && gNfcBus.begin();
    gNfcFailed = !gNfcInitialized;
    return gNfcInitialized;
}
#endif

bool labosNfcProbe(String& uid, String& tagType, String& error, String* ndefText) {
    uid.clear(); tagType.clear(); error.clear();
    if (ndefText) ndefText->clear();
#if LABOS_NFC_ENABLED
    if (!nfcInit()) { error = "nfc_driver_init_failed"; return false; }
    gNfcBus.update();
    m5::nfc::a::PICC picc{};
    if (!gNfcA.detect(picc)) { error = "no_tag"; return false; }
    if (!gNfcA.identify(picc) || !gNfcA.reactivate(picc)) {
        error = "tag_identification_failed";
        return false;
    }
    uid = String(picc.uidAsString().c_str());
    tagType = String(picc.typeAsString().c_str());
    if (ndefText && picc.supportsNDEF()) {
        bool valid = false;
        if (gNfcA.ndefIsValidFormat(valid) && valid) {
            m5::nfc::ndef::TLV message{};
            if (gNfcA.ndefRead(message) && message.isMessageTLV()) {
                for (auto&& record : message.records()) {
                    if (ndefText->length() >= 160) break;
                    String typeName = String(record.type());
                    String payload = String(record.payloadAsString().c_str());
                    // NDEF is untrusted text. Do not automatically open URLs.
                    *ndefText += typeName + ":" + payload.substring(0, 80) + "; ";
                }
            }
        }
    }
    gNfcA.deactivate();
    return true;
#else
    error = "nfc_library_disabled";
    return false;
#endif
}

void labosNfcScan(uint32_t req) {
    String uid, tagType, error, ndef;
    labosSend(req, "begin", "{\"kind\":\"nfc\",\"source\":\"adv\"}");
    // A tap must be presented before issuing this one-shot command.
    if (labosNfcProbe(uid, tagType, error, &ndef)) {
        labosSend(req, "item", "{\"uid\":" + labosQuote(uid) +
                  ",\"tag_type\":" + labosQuote(tagType) +
                  ",\"ndef\":" + labosQuote(ndef) + "}");
        labosSend(req, "end", "{\"count\":1}");
    } else {
        // A missing tag is a legitimate empty result, not an imaginary tag.
        labosSend(req, "end", "{\"count\":0,\"reason\":" + labosQuote(error) + "}");
    }
}

void appNfc() {
    static const char* labels[] = {"Read NFC-A tag", "Hardware description"};
    int selected = 0;
    for (;;) {
        int r = uiMenu("NFC U219 / READ", labels, 2, selected, nullptr);
        if (r < 0) return;
        selected = r;
        if (r == 1) {
            uiMessage("ST25R3916", "SPI CS6 IRQ4 / 13.56MHz", 1500);
            continue;
        }
        uiMessage("NFC scan", "Put test tag nearby", 400);
        String uid, type, error;
        if (labosNfcProbe(uid, type, error, nullptr)) {
            M5Cardputer.Display.fillScreen(gTheme.bg);
            uiHeader("NFC-A detected");
            M5Cardputer.Display.setTextColor(gTheme.fg);
            M5Cardputer.Display.setCursor(5, 34);
            M5Cardputer.Display.print("UID: ");
            M5Cardputer.Display.println(uid);
            M5Cardputer.Display.print("Type: ");
            M5Cardputer.Display.println(type);
            uiStatusBar("press any key");
            Serial.printf("[NFC] detected type=%s uid=%s\n", type.c_str(),uid.c_str());
            while (!inputPoll().any) delay(10);
        } else {
            uiMessage("NFC", error.c_str(), 1300);
        }
    }
}
