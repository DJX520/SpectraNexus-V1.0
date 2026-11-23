# BlackDeck LabOS V5.2 · 紫金主题

> **BlackDeck V2.2 固件（Cardputer-Adv）+ LabOS V5.2 上位机（RDK X5）**
>
> 紫罗兰深色 × 香槟金统一视觉主题，面向 **M5Stack Cardputer-Adv（K132-Adv）+ Cap CC1101 U219（14 针扩展帽）** 的一体化无线信号观测实验台，内置**完全离线的端侧 LLM**，配套 **RDK X5（Ubuntu 22.04）本地 Web 上位机**。

---

## 核心特性

- **只收不发**：WiFi/BLE 被动扫描、Sub-GHz 四频段 RSSI 接收（CC1101）、NFC-A 只读（ST25R3916），无主动发射/攻击指令
- **离线端侧 AI**：8M 参数 Q4 量化模型，权重与分词器已编译进固件，无网络依赖即可对话
- **LAB5 串口协议**：纯 ASCII 帧、逐行 ≤ 512 字节、无任意代码执行，USB-CDC 即插即用
- **紫金主题 Web 上位机**：6 页页面覆盖采集、分析、实验管理、AI 助手、演示驾驶舱、部署诊断
- **SQLite 本地数据库**：自动存储会话、信号样本、实验记录；CSV/JSON/PDF 报告一键导出
- **SSH 隧道安全访问**：上位机默认只监听 127.0.0.1，无公网暴露风险
- **26/26 单元测试通过**：Python PTY 回环、LAB5 协议帧、HTTP 路由、数据库事务、前端资源校验

---

## 系统架构

```
┌───────────────────────────┐   USB-CDC    ┌─────────────────────┐  HTTP (SSH 隧道)  ┌──────────────┐
│  Cardputer-Adv (ESP32-S3) │──────────────▶│  RDK X5 (Ubuntu 22.04)│──────────────────▶│  浏览器       │
│  BlackDeck 固件 V2.2       │  LAB5 协议   │  LabOS 后端 V5.2     │                   │  紫金主题 UI  │
│                            │              │                     │                   │              │
│  · 离线 AI / WiFi 扫描     │   115200     │  · SQLite 数据库     │     localhost     │  01~06 页面   │
│  · BLE / IR / CC1101 RF   │              │  · 信号图表 / 报告   │    8080 端口       │              │
│  · NFC 只读 / BadUSB 预留  │              │  · AI 助手 / 自检    │                   │              │
└───────────────────────────┘              └─────────────────────┘                   └──────────────┘
         ▲                                          ▲
         │ Cap CC1101 U219 扩展帽                    │ 可选
         │ 315/433/868/915 MHz                      │ Whisper.cpp / Ollama
```

### LAB5 串口协议（固件 ↔ 上位机）

纯 ASCII，行式，≤ 512 字节/行。请求带自增 `request_id`，响应原样回传用于匹配。

**请求格式**：`L5|<request_id>|<command> [args]`

| 命令 | 说明 | 响应 |
|---|---|---|
| `HELLO` | 握手 | `begin` → `item` → `end` |
| `INFO` | 设备信息（固件版本、硬件板型、Flash 容量） | `begin` → `item` → `end` |
| `WIFI_SCAN` | WiFi 被动扫描 | `begin` → N×`item` → `end` |
| `BLE_SCAN` | BLE 被动扫描 | `begin` → N×`item` → `end` |
| `RF_SAMPLE <mhz>` | 单频段 RSSI 采样（mhz: 315.0 / 433.92 / 868.95 / 915.0） | `begin` → N×`item` → `end` |
| `NFC_SCAN` | NFC-A 只读（UID / 类型 / 可选 NDEF） | `begin` → `item` → `end` |

**响应格式**：

| 类型 | 内容 | 说明 |
|---|---|---|
| `LAB5|<id>\|begin\|{json}` | 帧起始 | 必须在每条 item 之前出现 |
| `LAB5|<id>\|item\|{json}` | 数据项 | 扫描结果逐条返回 |
| `LAB5|<id>\|end\|{json}` | 帧结束 | 带完整统计（数量、耗时等） |
| `LAB5|<id>\|error\|{json}` | 错误 | 通信层或硬件层异常 |

**安全约束**：LAB5 协议只暴露只读观测命令，无 TX/发射/任意代码执行通道。

---

## 固件功能（BlackDeck V2.2，Cardputer-Adv 主菜单热键）

| 热键 | 模块 | 说明 |
|---|---|---|
| `A` | AI Offline LLM | 完全离线端侧对话；8M 参数 Q4 量化模型，权重/分词器已编译进固件 |
| `W` | WiFi Observer | 被动扫描周边 2.4GHz WiFi（SSID / BSSID / RSSI / Channel / Encryption） |
| `B` | BLE Observer | 被动扫描 BLE 广播设备（MAC / RSSI / Advertised Service UUID） |
| `I` | Infrared IR | 红外发射（NEC / TV-B-Gone 预存码库）；接收与录制 |
| `S` | Sub-GHz Monitor | CC1101 四频段（315 / 433 / 868 / 915 MHz）RSSI 实时接收 |
| `N` | NFC Tag Reader | ST25R3916 NFC-A 只读；返回 UID / 类型 / 可选 NDEF 文本 |
| `T` | Tools | 主题切换 / 手电筒 / 随机 MAC / 系统信息 / 重启 |
| `E` | Settings | 亮度调节 / 恢复默认 / 串口命令（调试用） |
| `V` | Showroom / FX | 展示与特效页面 |
| `BadUSB` | 预留 | 代码存在（`apps_badusb.cpp`），但 `config.h: BADUSB_HID=0` 默认禁用 |
| `NRF24` | 预留 | 代码存在（`apps_nrf24.cpp`），但 `config.h: HAS_NRF24=0` 默认禁用 |

**离线 AI 模型规格**：8M 参数 Q4 量化（`dot_q4_pie.S` + `llm.cpp` + `model_data.cpp` + `tok_data.cpp`），运行于 Cardputer-Adv 512 KB SRAM；Flash 分区上限 8,257,536 B。

---

## RDK 上位机功能（LabOS V5.2，6 页 Web 控制台）

| 页面 | 功能 |
|---|---|
| **01 总览与采集** | 读取设备状态；一键 WiFi / BLE / RF 四频段 / NFC 采集；原始数据表格 |
| **02 无线数据分析** | 折线图（RSSI vs 时间 / Frequency vs Count）；信号统计；档案检索 |
| **03 实验管理** | 会话创建/归档；SQLite 存储；CSV / JSON 导出；PDF 报告打印 |
| **04 AI 分析助手** | 规则分析引擎；可选 Whisper.cpp 语音转写；可选 Ollama 本地模型 |
| **05 全屏演示驾驶舱** | Signal Theater：数据库回放 + 视觉模拟动效；**模拟数据不写库** |
| **06 部署与诊断** | USB 一键通信自检（HELLO + INFO + 响应耗时）；串口路径自动发现 |

### RDK 后端模块（`rdk/labos/`）

| 模块 | 职责 |
|---|---|
| `server.py` | HTTP 路由与紫金主题静态页服务（纯 Python 标准库，无 Flask） |
| `protocol.py` | LAB5 协议帧编解码、校验、状态机 |
| `device.py` | 串口管理、命令下发、结果组装 |
| `database.py` | SQLite 会话/样本/实验记录 CRUD |
| `analytics.py` | RSSI 折线数据、信号统计 |
| `assistant.py` | 规则分析 + 可选 LLM 助手 |
| `audio.py` | 可选 Whisper.cpp 封装 |
| `import_analysis.py` | CSV/JSON 导入与分析 |
| `reporting.py` | PDF 报告生成 |
| `check_device.py` | 独立 CLI：`.venv/bin/python -m labos.check_device --port auto`（无损握手+INFO） |

---

## 硬件与引脚（Cap CC1101 U219）

引脚来源：M5Stack Cap U219 官方引脚图 + `firmware/BlackDeck/config.h`。**不要套用散件 CC1101 的接线。**

| 功能 | GPIO | 备注 |
|---|---|---|
| Cap 电源使能 `CAP_POWER_EN` | 3 | 高电平开启扩展帽 |
| NFC CS `CAP_NFC_CS` | 6 | ST25R3916 SPI 片选 |
| NFC IRQ `CAP_NFC_IRQ` | 4 | ST25R3916 中断输入 |
| CC1101 SCK | 40 | SPI 时钟 |
| CC1101 MISO | 39 | SPI 主入 |
| CC1101 MOSI | 14 | SPI 主出 |
| CC1101 CS | 5 | SPI 片选 |
| CC1101 GDO0 | 15 | 通用数据输出 0 |
| CC1101 RF_SW0 | 13 | RF 开关控制 0；RF_SW1 由 CC1101 GDO2 寄存器驱动，无 MCU GPIO |
| 红外发射 `PIN_IR_TX` | 44 | Cardputer-Adv 板载 IR LED |

NFC 为 **NFC-A 只读**，不覆盖全部卡类型。

---

## 目录结构

```
BlackDeck_LabOS_V5_2_PurpleGold/
├── README.md                         本文件
├── SHA256SUMS.txt                    全包文件 SHA-256 校验
│
├── docs/
│   ├── 01_部署步骤_正式版.md            从零部署与验收
│   ├── 02_功能与测试结果.md             功能清单与验证范围
│   ├── BlackDeck_LabOS_客户使用手册.pdf   客户上手/操作手册
│   ├── BlackDeck_LabOS_客户使用手册_可打印.html
│   ├── 紫金主题_总览预览.png
│   ├── 紫金主题_展示驾驶舱.png
│   ├── 紫金主题_手机预览.png
│   └── 紫金主题_离线网页预览.html          离线静态预览（模拟数据，不可操作硬件）
│
├── firmware/
│   └── BlackDeck/                     完整 Arduino 工程（用 Arduino IDE 打开 BlackDeck.ino）
│       ├── BlackDeck.ino              主程序入口（键盘事件循环 + 主菜单分发）
│       ├── BlackDeck.h / config.h      全局头文件 + 硬件配置（引脚/启用开关/分区常量）
│       ├── menu.cpp                   主菜单渲染与层级导航
│       ├── ui.cpp / input.cpp         UI 绘制 + 键盘/旋钮输入
│       ├── serial.cpp / settings.cpp  串口命令 + 设置持久化
│       │
│       ├── apps_wifi.cpp              WiFi 被动扫描（wifi.scan 只读）
│       ├── apps_ble.cpp               BLE 被动扫描（NimBLE-Arduino 广播监听）
│       ├── apps_subghz.cpp            CC1101 四频段 RSSI 采样
│       ├── apps_nfc.cpp               ST25R3916 NFC-A 只读（UID + NDEF 可选）
│       ├── apps_ir.cpp                NEC / TV-B-Gone 红外发射
│       ├── apps_system.cpp            系统信息 / 重启 / 随机 MAC
│       ├── apps_showroom.cpp          Showroom 特效
│       ├── apps_ai.cpp                端侧离线 AI 入口（热键 A）
│       ├── apps_badusb.cpp            BadUSB（代码存在，config.h 默认禁用）
│       ├── apps_nrf24.cpp             NRF24（代码存在，config.h 默认禁用）
│       │
│       ├── ai_offline.cpp             离线 AI 推理入口
│       ├── llm.cpp / llm.h            小型 Q4 量化推理引擎
│       ├── model_data.cpp             8M 参数 Q4 权重（编译进固件）
│       ├── tok_data.cpp               分词器词表（编译进固件）
│       ├── dot_q4_pie.S               模型代码段（汇编）
│       │
│       ├── labos_link.cpp / .h        LAB5 USB 串口协议（固件 ↔ 上位机通信层）
│       └── partitions.csv             分区表：0x10000 ~ 0x7F0000 为 APP（上限 8,257,536 B）
│
└── rdk/                               LabOS V5.2 上位机（Ubuntu 22.04）
    ├── install_rdk.sh                 一键创建 venv + 装 pyserial
    ├── run_rdk.sh                     读取 config.env，启动 Web 服务
    ├── config.env.example             端口 / 串口 / 数据目录 / 可选 Whisper / Ollama
    ├── requirements.txt               pyserial>=3.5,<4（唯一依赖）
    ├── UPSTREAM_LICENSE.txt           MIT 协议
    │
    ├── labos/
    │   ├── server.py                  HTTP 路由 + 紫金主题静态页
    │   ├── protocol.py                LAB5 帧编解码 / 校验 / 状态机
    │   ├── device.py                  串口管理 / 命令下发 / 结果组装
    │   ├── check_device.py            CLI：python -m labos.check_device --port auto
    │   ├── database.py                SQLite 会话/样本/实验 CRUD
    │   ├── analytics.py               RSSI 折线 / 信号统计
    │   ├── import_analysis.py          CSV / JSON 导入
    │   ├── assistant.py               规则分析 + 可选 Ollama
    │   ├── audio.py                   可选 Whisper.cpp 封装
    │   └── reporting.py               PDF 报告生成
    │
    ├── static/                        紫金主题前端资源
    │   ├── index.html
    │   ├── purple-gold.css            主主题（紫 #6B3FA0 / 金 #D4A853）
    │   ├── style.css
    │   ├── showcase.css / showcase.js 05 驾驶舱视觉模拟
    │   └── app.js
    │
    ├── scripts/
    │   ├── probe_usb.py               USB 探针（LAB5 HELLO 测试）
    │   ├── install_user_service.sh    systemd --user 开机自启
    │   └── 本地运行说明.txt
    │
    └── tests/
        ├── test_protocol.py           LAB5 帧拼接 / 缺帧检测
        ├── test_device.py             串口命令组装
        ├── test_pty_transport.py      Linux PTY 字节回环（HELLO/INFO/WIFI_SCAN/NFC 空数据）
        ├── test_server.py             HTTP 路由 / 错误响应
        ├── test_database_analytics.py SQLite 事务 + 分析
        └── test_showcase_assets.js    前端资源 node --check 语法验证
```

---

## 快速开始

### A. Windows 烧录 BlackDeck 固件到 Cardputer-Adv

1. **解压本包**，用 Arduino IDE 2.3.x 打开 `firmware/BlackDeck/BlackDeck.ino`（**不要**只打开某个 .cpp）
2. **Arduino 库管理器**安装依赖：
   - `M5Cardputer`（官方 M5Stack Cardputer-Adv Core）
   - `M5Unified`（显示/触摸驱动）
   - `M5UnitUnifiedNFC`（含 `UnitNFC` 依赖）
   - `RadioLib 8.x`（CC1101 驱动）
   - `NimBLE-Arduino 2.x`（BLE 被动扫描）
3. **Arduino IDE 开发板选择**：
   - Board：`ESP32S3 Dev Module`
   - Flash Size：`8MB`
   - PSRAM：`Disabled`
   - USB CDC On Boot：`Enabled`
   - Partition Scheme：选 `Custom`（从 `BlackDeck/partitions.csv` 读取）
   - 如需分区显示修正，把 `firmware/boards.local.txt` 合并到 Arduino Core 同级 `boards.local.txt` 后重启 IDE
4. **先「验证」编译**：确认程序体积 < 8,257,536 B（IDE 可能显示 16MB Maximum，不要信那个）
5. **下载模式上传**：ADV 关机 → 按住 G0 键 → 插 USB → 松开 G0 → 点击上传
6. **烧录成功后**：ADV 自动重启，主菜单显示 BlackDeck 固件界面

### B. 安装 Cap CC1101 U219 扩展帽

- 关机后插入 14 针扩展帽，确认方向与接触可靠，**不要热插拔**
- 按测量频段装配匹配天线（315 / 433 / 868 / 915 MHz），换天线前先关闭射频采集

### C. RDK X5 安装与启动

```bash
# 1) 把 rdk 目录复制到 RDK（假设 ~/Desktop/BlackDeck_LabOS_V5_2/rdk）
#    Windows 上传示例: scp -r rdk/ sunrise@<RDK_IP>:~/Desktop/BlackDeck_LabOS_V5_2/

cd ~/Desktop/BlackDeck_LabOS_V5_2/rdk

# 2) 基础依赖 + Python venv（唯一必需依赖是 pyserial）
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
bash install_rdk.sh

# 3) 单元测试（自检测试全绿应 26/26）
.venv/bin/python -m unittest discover -s tests -v

# 4) 串口权限
sudo usermod -aG dialout "$USER"   # 之后注销重新登录生效

# 5) 独立 CLI 自检（不启动 Web，只做握手 + INFO，不扫描）
.venv/bin/python -m labos.check_device --port auto

# 6) 启动 Web 服务（默认绑定 127.0.0.1:8080）
bash run_rdk.sh
```

**访问方式**：

| 位置 | 地址 | 说明 |
|---|---|---|
| RDK 本机 | `http://127.0.0.1:8080` | 直接访问 |
| Windows 浏览器（SSH 隧道） | `ssh -L 8080:127.0.0.1:8080 用户名@<RDK_IP>` → 浏览器开 `http://127.0.0.1:8080` | 隧道窗口保持打开；关闭 Arduino 串口监视器 / minicom / screen 等占用串口的程序 |

### D. 可选：Whisper.cpp + Ollama

```bash
# Whisper.cpp（语音转写）
cd ~ && git clone https://github.com/ggerganov/whisper.cpp && cd whisper.cpp
make -j4 && ./models/download-ggml-model.sh tiny   # 74MB，中文 90%+
export PATH=$PATH:~/whisper.cpp

# Ollama（本地 LLM）
ollama pull qwen2.5:1.5b

# 修改 config.env 并重启 RDK 服务
cp -n config.env.example config.env
nano config.env
# 反注释并填入:
#   WHISPER_CLI="$HOME/whisper.cpp/build/bin/whisper-cli"
#   WHISPER_MODEL="$HOME/whisper.cpp/models/ggml-tiny.bin"
#   LABOS_AI_BACKEND=ollama
#   OLLAMA_MODEL=qwen2.5:1.5b
bash run_rdk.sh   # 重启生效
```

### E. 开机自启动（运行稳定后再配置）

```bash
cd ~/Desktop/BlackDeck_LabOS_V5_2/rdk
bash scripts/install_user_service.sh
systemctl --user status labos-rdk.service --no-pager
journalctl --user -u labos-rdk.service -f

# 如需用户未登录时自动运行:
sudo loginctl enable-linger sunrise
```

---

## 首次联机验收

按顺序执行，每步都应有明确成功判据。

```bash
cd ~/Desktop/BlackDeck_LabOS_V5_2/rdk

# 1) 确认串口存在
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null

# 2) 独立 CLI 自检（无 Web 服务时也能跑）
.venv/bin/python -m labos.check_device --port auto
# 成功: ok:true, protocol:LAB5, 显示 firmware/board/flash_bytes

# 3) 启动 Web 服务
bash run_rdk.sh &

# 4) LAB5 HELLO 握手
curl -sS http://127.0.0.1:8080/api/status; echo
curl -sS -X POST http://127.0.0.1:8080/api/usb_status; echo
# 成功: ok:true, protocol:"LAB5"

# 5) 设备 INFO
curl -sS -X POST http://127.0.0.1:8080/api/usb/info -H 'Content-Type: application/json' -d '{}'; echo
# 成功: firmware/board/flash_bytes 匹配 Cardputer-Adv + BlackDeck V2.2

# 6) WiFi 扫描（30s 超时）
curl --max-time 35 -sS -X POST http://127.0.0.1:8080/api/usb/scan \
  -H 'Content-Type: application/json' -d '{}'; echo
# 成功: status:"completed", networks:[...] （空列表也合法，取决于现场环境）

# 7) RF 四频段
for mhz in 315.0 433.92 868.95 915.0; do
  curl --max-time 10 -sS -X POST http://127.0.0.1:8080/api/usb/rf \
    -H 'Content-Type: application/json' -d "{\"mhz\":$mhz}"; echo
done

# 8) NFC 只读（靠近卡片）
curl --max-time 10 -sS -X POST http://127.0.0.1:8080/api/usb/nfc \
  -H 'Content-Type: application/json' -d '{}'; echo

# 9) RDK Web 控制台
# RDK 浏览器或 SSH 隧道浏览器打开 http://127.0.0.1:8080
# → 06 部署与诊断 → 一键 USB 自检
# → 01 总览与采集 → 点 WiFi / BLE / RF / NFC 按钮
# → 03 实验管理 → 新建会话 → 采集 → 导出 CSV → 打印 PDF
# → 05 全屏演示驾驶舱 → 点「视觉模拟演示」（模拟数据，不写库）
```

---

## 部署架构详解

```
Cardputer-Adv                              RDK X5                           浏览器
┌─────────────────────┐    USB-CDC     ┌──────────────────────────┐   HTTP(SSH隧道)  ┌───────────┐
│ BlackDeck V2.2       │──────────────▶│ LabOS V5.2 HTTP Server    │────────────────▶│ 紫金主题 UI│
│ · LAB5 协议实现      │   115200       │ · 127.0.0.1:8080         │                  │ 6 页面     │
│ · WiFi/BLE/CC1101/NFC│                │ · SQLite (./data)         │                  │           │
│ · 离线 AI 8M Q4      │                │ · 紫金主题静态资源        │                  │           │
│ · IR 发射            │                │ · 可选 Whisper/Ollama    │                  │           │
└─────────────────────┘                └──────────────────────────┘                  └───────────┘
        ▲                                        ▲
        │                                        │
        └──── Cap CC1101 U219 ────────────────┘
             (315/433/868/915 MHz)
```

**端口策略**：上位机默认 `127.0.0.1:8080`，不绑定 0.0.0.0。远程访问通过 SSH 隧道。

**固件分区**：`0x10000` 起 0x7E0000 为 APP 分区（8,257,536 B），`0x7F0000 ~ 0x800000` 为 SPIFFS。

**固件版本**：`firmware/BlackDeck/config.h: #define APP_VERSION "2.2-purplegold"`

**测试覆盖**（26/26 通过）：
- LAB5 协议帧拼接 / 缺帧检测 / UTF-8 SSID 转义
- PTY 字节回环：HELLO / INFO / 中文 SSID / NFC 空数据 / 断线离线
- HTTP 路由 200/400/500 响应 + 错误帧处理
- SQLite 事务完整性 + 分析函数
- 前端 `node --check` 语法验证 + 响应式布局（1440 / 768 / 390 px 无溢出）

---

## 常见问题

| 现象 | 处理 |
|---|---|
| 自检提示无串口 | 换数据线；查 `/dev/ttyACM*`；确认 Arduino IDE 已选 **USB CDC On Boot = Enabled** |
| `Permission denied` 打开串口 | `sudo usermod -aG dialout "$USER"` 后注销重新登录 |
| USB 被其他进程占用 | 关闭 Arduino 串口监视器、minicom、screen、旧版 LabOS |
| 自检 `protocol:LAB5` 不匹配 | 确认 ADV 烧的是本包 BlackDeck V2.2，不是其他固件 |
| WiFi / BLE 扫描结果为空 | 现场确实没信号；不是硬件错误 |
| CC1101 RF RSSI 异常 | 核对扩展帽方向 + 天线匹配频段（换天线前先关射频） |
| NFC 读不到 | 确认是 **NFC-A** 标签并靠近天线；本版只读 |
| Arduino IDE 显示 16MB Maximum | 忽略这个数字，实际上限 8,257,536 B（见 `partitions.csv`） |
| 离线 AI 卡顿 / 内存溢出 | Flash 通过 ≠ SRAM 通过。记录 Heap 后定位；模型与 512 KB SRAM 的匹配是硬约束 |
| Windows 浏览器麦克风权限 | 通过 SSH 隧道访问 `127.0.0.1` 属于安全上下文，可获得麦克风权限 |
| RF 采集后 433.92 MHz 频率漂移 | V2.2 已修复 `apps_subghz.cpp` 频段同步恢复 |

---

## 合规与安全

- **只收不发**：LAB5 协议无任何 TX/发射指令，固件 BadUSB/NRF24 代码存在但默认禁用
- 数据来源标识：`ADV_USB`（USB 返回真实采集）/ `imported`（文件导入）/ `simulated`（演示模拟），模拟/导入数据不代表真实测量
- 所有无线扫描仅监听被动信号，不产生任何网络干扰
- 请在自有或获授权设备上使用，遵守当地法律法规
- 上位机默认监听 127.0.0.1，不暴露公网；远程访问走 SSH 隧道
- Whisper.cpp 与 Ollama 为可选离线本地服务，不涉及任何云端上传

---

## License

- RDK 上位机（`rdk/`）：MIT License，详见 `rdk/UPSTREAM_LICENSE.txt`
- 固件整合了 `cardputer-ai`（MIT）等开源项目，相关授权与致谢见各自上游仓库；本包中 `firmware/BlackDeck/` 的新增代码采用 MIT 许可证
- **不包含** BlackDeck 原始固件的完整第三方依赖源码，使用 Arduino IDE 库管理器安装官方依赖即可完成编译

---

## 进一步参考

- [docs/01_部署步骤_正式版.md](docs/01_部署步骤_正式版.md) — 从零部署（含烧录细节、验收命令、systemd 配置）
- [docs/02_功能与测试结果.md](docs/02_功能与测试结果.md) — 功能清单、26/26 单元测试结果、需现场验收项
- [docs/BlackDeck_LabOS_客户使用手册.pdf](docs/BlackDeck_LabOS_客户使用手册.pdf) — 客户上手/操作手册
- [docs/紫金主题_离线网页预览.html](docs/紫金主题_离线网页预览.html) — 纯前端静态预览（模拟数据，浏览器直接打开）
