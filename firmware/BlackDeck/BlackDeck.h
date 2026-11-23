/*
 * BLACKDECK — 公共头文件：全局声明、模块接口、版本信息。
 */
#pragma once
#include <Arduino.h>
#include <M5Cardputer.h>
#include <vector>
#include "config.h"

/* ------------------------------------------------------------------ */
/* 输入事件（见 input.cpp）。边沿触发，每帧至多一个事件。               */
/* ------------------------------------------------------------------ */
struct InputEvent {
    bool up    = false;   // ';'
    bool down  = false;   // '.'
    bool left  = false;   // ','
    bool right = false;   // '/'
    bool enter = false;   // ENTER 或肩键
    bool esc   = false;   // '`' 或退格(菜单层)
    bool del   = false;   // 退格键
    bool fn    = false;
    bool shift = false;
    char ch    = 0;       // 可打印字符（含 . , ; / 等，供文本输入用）
    bool any   = false;   // 本帧是否有事件
};

/* ------------------------------------------------------------------ */
/* 主题（见 ui.cpp）。                                                  */
/* ------------------------------------------------------------------ */
struct Theme {
    const char* name;
    uint16_t bg;        // 背景
    uint16_t panel;     // 面板/卡片
    uint16_t accent;    // 主强调色（选中项、标题）
    uint16_t accent2;   // 次强调色
    uint16_t fg;        // 前景文字
    uint16_t muted;     // 弱化文字
    uint16_t danger;    // 警告/攻击红
    uint16_t ok;        // 成功绿
};

extern Theme gTheme;
extern const Theme kThemes[6];
extern const int kThemeCount;

/* ------------------------------------------------------------------ */
/* 模块接口                                                            */
/* ------------------------------------------------------------------ */
// 输入
void inputSetup();
InputEvent inputPoll();          // 每 loop 调用一次，返回本帧事件
bool inputIsAdv();               // true = TCA8418 (ADV) 键盘
void inputBeep(uint16_t freq = 2000, uint32_t ms = 30);

// 串口命令行（见 serial.cpp）
void serialPoll();

// UI
void uiInit();
void uiLoop();                   // 屏保/空闲处理（在 app 主循环里调用）
void uiHeader(const char* title);
void uiStatusBar(const char* right = nullptr);
int  uiMenu(const char* title, const char* const* labels, int count, int selected,
            const char* hotkeys = nullptr);   // 返回选中下标；返回 -1 = 返回
void uiMessage(const char* a, const char* b = nullptr, uint32_t ms = 1300);
bool uiConfirm(const char* prompt);
String uiReadString(const char* prompt, const String& initial = "", int maxLen = 60);
void uiDrawList(const char* title, const char* const* labels, int count, int selected);
int  uiPickDynamic(const char* title, std::vector<String>& items, int& selected);
void uiThemeNext();
void uiSetTheme(int idx);

// 应用（返回后回到主菜单）
void appMenu();
void appAi();
void appWifi();
void appBle();
void appIr();
void appBadUsb();
void appSubGhz();
void appNfc();
void appNrf24();
void appTools();
void appSettings();
void appShowroom();
void uiBootShow();

// 设置存储（见 settings.cpp）
void   settingsInit();
String settingsGet(const char* key, const String& def);
void   settingsSet(const char* key, const String& val);

// 离线 LLM 适配（见 ai_offline.cpp）
String aiOfflineGenerate(const String& prompt);
bool   aiOfflineReady();

// 网络（见 apps_wifi.cpp）
bool   netEnsureWifi();
String netSsid();
String netIp();

/* ------------------------------------------------------------------ */
/* 全局对象访问                                                         */
/* ------------------------------------------------------------------ */
// 统一使用 M5Cardputer 对象：M5Cardputer.Display / Power / Speaker / BtnA 等。
