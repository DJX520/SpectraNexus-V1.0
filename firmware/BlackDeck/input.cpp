/* Single input path for Cardputer / Cardputer-Adv.
 * M5Cardputer >= 1.1 owns TCA8418 IRQ, I2C, key mapping, and matrix scanning.
 * Never directly init TCA8418 a second time (can corrupt the library state).
 */
#include "BlackDeck.h"
#include <ctype.h>

static String prevWord;
static bool prevDel = false, prevEnter = false;
static bool gAdv = false;

static char shifted(char c) {
    switch (c) {
        case '`': return '~'; case '1': return '!'; case '2': return '@';
        case '3': return '#'; case '4': return '$'; case '5': return '%';
        case '6': return '^'; case '7': return '&'; case '8': return '*';
        case '9': return '('; case '0': return ')'; case '-': return '_';
        case '=': return '+'; case '[': return '{'; case ']': return '}';
        case '\\': return '|'; case ';': return ':'; case '\'': return '"';
        case ',': return '<'; case '.': return '>'; case '/': return '?';
        default: return c >= 'a' && c <= 'z' ? char(c - 'a' + 'A') : c;
    }
}

void inputSetup() {
    gAdv = (M5.getBoard() == m5::board_t::board_M5CardputerADV);
    prevWord = "";
    Serial.printf("[BD] keyboard=%s\n", gAdv ? "TCA8418 via M5Cardputer" : "matrix via M5Cardputer");
}

bool inputIsAdv() { return gAdv; }

InputEvent inputPoll() {
    InputEvent e;
    M5Cardputer.update();  // Official update() required for ADV and classic
    serialPoll();
    if (M5Cardputer.BtnA.wasPressed()) { e.any = true; e.enter = true; }
    if (!M5Cardputer.Keyboard.isChange()) return e;
    const auto ks = M5Cardputer.Keyboard.keysState();
    String word;
    for (auto c : ks.word) word += (char)c;
    for (size_t i = 0; i < word.length(); ++i) {
        char c = word[i];
        if (prevWord.indexOf(c) >= 0) continue;
        // The library already provides the normalized character map. Do not
        // double-shift capitalized symbols; only fix lower case when needed.
        if (ks.shift && c >= 'a' && c <= 'z') c = shifted(c);
        e.ch = c;
        e.any = true;
        if (c == ';') e.up = true;
        if (c == '.') e.down = true;
        if (c == ',') e.left = true;
        if (c == '/') e.right = true;
        if (c == '`') e.esc = true;
    }
    if (ks.del && !prevDel) { e.del = true; e.any = true; }
    if (ks.enter && !prevEnter) { e.enter = true; e.any = true; }
    e.fn = ks.fn;
    e.shift = ks.shift;
    prevWord = word;
    prevDel = ks.del;
    prevEnter = ks.enter;
    return e;
}
