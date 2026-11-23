/* BLACKDECK AI interface. Full offline LLM remains built into the firmware.
 * ESP32-S3FN8 has no PSRAM; inference may report OOM. Flash partition only
 * solves image size limits, not memory limits.
 */
#include "BlackDeck.h"
#include <vector>

/* 把长文本按屏幕宽度切成显示行 */
static std::vector<String> wrapLines(const String& s, int maxW) {
    std::vector<String> out;
    M5Cardputer.Display.setTextSize(1);
    String cur = "";
    for (unsigned i = 0; i < s.length(); i++) {
        char ch = s[i];
        if (ch == '\n') { out.push_back(cur); cur = ""; continue; }
        String t = cur + ch;
        if (M5Cardputer.Display.textWidth(t.c_str()) > maxW) { out.push_back(cur); cur = String(ch); }
        else cur = t;
    }
    out.push_back(cur);
    return out;
}

void appAi() {
    if (!aiOfflineReady()) {
        uiMessage("Offline model unavailable", "AI mode: optional model", 1800);
        return;
    }

    std::vector<String> hist;
    String input = "";

    auto addMsg = [&](const String& text) {
        auto ls = wrapLines(text, 232);
        for (auto& l : ls) hist.push_back(l);
        while (hist.size() > 200) hist.erase(hist.begin());
    };

    auto render = [&](const char* status) {
        M5Cardputer.Display.fillScreen(gTheme.bg);
        uiHeader("AI Assistant");
        int y = 22, lh = 11;
        int maxLines = (135 - 11 - 24) / lh;
        int start = hist.size() > (size_t)maxLines ? hist.size() - maxLines : 0;
        for (size_t i = start; i < hist.size(); i++) {
            M5Cardputer.Display.setTextColor(gTheme.fg);
            M5Cardputer.Display.setTextSize(1);
            M5Cardputer.Display.setCursor(4, y);
            M5Cardputer.Display.print(hist[i]);
            y += lh;
        }
        int iy = 135 - 22;
        M5Cardputer.Display.fillRect(0, iy, 240, 22, gTheme.panel);
        M5Cardputer.Display.setTextColor(gTheme.accent);
        M5Cardputer.Display.setCursor(4, iy + 3);
        M5Cardputer.Display.print("> " + input + "_");
        uiStatusBar(status);
    };

    addMsg("Offline LLM ready. ENTER send, ` exit.");
    render("AI");

    while (true) {
        InputEvent e = inputPoll();
        if (e.any) {
            if (e.esc) { inputBeep(1400, 25); break; }
            else if (e.enter) {
                if (input.length() == 0) continue;
                String q = input;
                input = "";
                addMsg("You: " + q);
                addMsg("AI: ...");
                render("thinking...");   // 生成前先显示思考中
                M5Cardputer.Speaker.tone(1200, 20);
                String resp = aiOfflineGenerate(q);   // 阻塞，约 5 tok/s
                hist.pop_back();                      // 去掉 "AI: ..."
                addMsg("AI: " + resp);
                render("AI");
            } else if (e.del) {
                if (input.length()) input.remove(input.length() - 1);
                render("AI");
            } else if (e.ch >= 0x20 && e.ch < 0x7F) {
                if (input.length() < 120) input += e.ch;
                render("AI");
            }
        }
        delay(5);
    }
}
