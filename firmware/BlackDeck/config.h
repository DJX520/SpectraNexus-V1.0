/* BLACKDECK V1.3.1 FullAI — Cardputer-Adv K132-Adv + Cap CC1101 U219
 * Safe, receive-first firmware. Pins are sourced from M5Stack Cap U219 pin map.
 */
#pragma once
#include <Arduino.h>
#define APP_VERSION      "2.2-purplegold"
#define APP_NAME         "BLACKDECK"
#define SERIAL_BAUD      115200
#define DEFAULT_THEME    0
#define BRIGHTNESS       128
#define UI_IDLE_MS       0

// Original offline LLM weights + tokenizer are bundled and compiled by default.
// Large app partition: BlackDeck/partitions.csv and boards_support/boards.local.txt.
#define AI_OFFLINE_LLM   1
#define LABOS_NFC_ENABLED 1  // requires M5UnitUnifiedNFC from official M5Stack library
#define HAS_CC1101      1
#define HAS_NRF24       0
#define HAS_LORA        0
#define BADUSB_HID      0

// Cardputer-Adv integrated peripherals
#define PIN_IR_TX       44
#define CAP_POWER_EN    3
#define CAP_NFC_CS      6
#define CAP_NFC_IRQ     4

// M5Stack Cap CC1101 U219 — do NOT use wiring for loose CC1101 boards
#define CC1101_SCK       40
#define CC1101_MISO      39
#define CC1101_MOSI      14
#define CC1101_CS        5
#define CC1101_GDO0      15
#define CC1101_RF_SW0    13
// RF_SW1 is driven by the CC1101 GDO2 register, NOT another MCU GPIO.
// Valid bands use RF switch table from M5Stack current online Arduino example.
#define SD_MOUNT_POINT  "/sd"
