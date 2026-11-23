/* BLACKDECK: full original local language model and tokenizer.
 * Source files are included directly in the BlackDeck sketch folder.
 * Never assume larger flash partitions increase RAM. Firmware retains the
 * original model, and runtime alloc failure returns false/"[OOM]".
 */
#include "BlackDeck.h"

#if AI_OFFLINE_LLM
#include "llm.h"
#include <esp_system.h>

/* 由 model_data.cpp / tok_data.cpp 生成，存放在 .rodata（flash 零拷贝读取） */
extern "C" const uint8_t MODEL_DATA[];
extern "C" const size_t  MODEL_DATA_LEN;
extern "C" const uint8_t TOKENIZER_DATA[];
extern "C" const size_t  TOKENIZER_DATA_LEN;

static Transformer gT;
static Tokenizer   gTk;
static Sampler     gSmp;
static bool        gReady = false;

bool aiOfflineReady() {
    if (gReady) return true;

    // dim 在 CRDP 头字节 8..11；dim<=128 是 3M，否则 8M（KV 窗口按此选）
    int dim;
    memcpy(&dim, MODEL_DATA + 8, 4);
    int kv = (dim <= 128) ? 80 : 72;

    if (!llm_init_embedded(&gT, MODEL_DATA, MODEL_DATA_LEN, kv)) {
        return false;   // 头损坏或内存不足（OOM）
    }
    kv = gT.kv_seq_len;  // llm_init_embedded 会把窗口钳到模型 seq_len，读回实际值

    if (!llm_tokenizer_from_memory(&gTk, TOKENIZER_DATA, TOKENIZER_DATA_LEN,
                                   gT.config.vocab_size)) {
        return false;
    }
    if (gTk.vocab_size != gT.config.vocab_size) {
        return false;   // 模型与分词器不匹配
    }
    llm_build_sampler(&gSmp, gT.config.vocab_size, 0.8f, 0.9f, esp_random());
    gReady = true;
    return true;
}

String aiOfflineGenerate(const String& prompt) {
    if (!gReady) return "[not ready]";

    // 与 cardputer-ai 相同的指令格式（GPT-Neo / CTK2 分词器）
    String full = "User: " + prompt + "\nBot:";

    int budget = gT.kv_seq_len - 8;
    if (budget < 8) budget = 8;
    int* toks = (int*)malloc(sizeof(int) * (budget + 8));
    if (!toks) return "[OOM]";

    int n = 0;
    llm_encode(&gTk, full.c_str(), 0, 0, toks, &n);
    if (n > budget) n = budget;
    if (n < 1) { free(toks); return "[empty]"; }

    String out = "";
    char scratch[64];
    int token = toks[0];
    int max_gen = 128;
    int cap = gT.kv_seq_len - n;      // 剩余窗口留给生成（不做滑窗，保持简单）
    if (max_gen > cap) max_gen = cap;
    if (max_gen < 1) max_gen = 1;

    for (int step = 0; step < n + max_gen; step++) {
        float* logits = llm_forward(&gT, token, step);
        int next;
        if (step < n - 1) {
            next = toks[step + 1];               // prefill：用提示里的下一个 token
        } else {
            next = llm_sample(&gSmp, logits);
            if (next == gTk.eos_id) break;
            const char* piece = llm_decode(&gTk, token, next, scratch, sizeof(scratch));
            if (piece && *piece) out += piece;
            yield();                             // 让出调度，兼顾看门狗
        }
        token = next;
    }
    free(toks);
    return out;
}

#else
// Rules-based local assistant intentionally does not pretend to be an LLM.
bool aiOfflineReady() { return true; }
String aiOfflineGenerate(const String& prompt) {
    String q = prompt;
    q.trim(); q.toLowerCase();
    if (q.indexOf("help") >= 0 || q.indexOf("menu") >= 0)
        return "Use WiFi and BLE for passive discovery; RF for 433 MHz RSSI; Tools for diagnostics.";
    if (q.indexOf("wifi") >= 0)
        return "WiFi observer scans nearby APs, shows channels and RSSI. Scan output is on Serial 115200.";
    if (q.indexOf("ble") >= 0 || q.indexOf("bluetooth") >= 0)
        return "BLE scanning lists nearby advertisers. Names are unverified and can be spoofed.";
    if (q.indexOf("cc1101") >= 0 || q.indexOf("rf") >= 0)
        return "CC1101 on Cap U219: CS5 GDO0=15 RF_SW0=13 and GDO2 controls RF_SW1.";
    if (q.indexOf("nfc") >= 0)
        return "ST25R3916 shares SPI. This firmware has no active NFC reader driver yet.";
    if (q.indexOf("heap") >= 0 || q.indexOf("memory") >= 0)
        return "Free heap: " + String(ESP.getFreeHeap() / 1024) + " KB; PSRAM: " + String(ESP.getPsramSize() / 1024) + " KB.";
    if (q.indexOf("battery") >= 0)
        return "Battery: " + String(M5Cardputer.Power.getBatteryLevel()) + " percent.";
    return "Rule-based local helper only. Try help, wifi, ble, rf, nfc, memory, battery.";
}
#endif
