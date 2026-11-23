"""Text-only research advisor; model output is never a device command."""
from __future__ import annotations
import json
import os
import urllib.request
from .analytics import summarize

GUIDE = (
    'BlackDeck V2 持续保留 ADV 端离线小模型。RDK 本地分析支持 WiFi/BLE 扫描、'
    'CC1101 RSSI、NFC-A 标识、CSV/PCAP 导入与实验统计。'
    '建议先执行 HELLO/INFO，之后测量并核对 source=ADV_USB；'
    '离群点只反映统计偏离，不代表攻击。')

def answer(query, rows):
    query=str(query).strip()[:1800]
    if not query:raise ValueError('请输入问题')
    summary=summarize(rows)
    context={'count':summary['total'],'kinds':summary['kinds'],
             'rf':summary['rf'],'wifi':summary['wifi'],'ble':summary['ble'],
             'channel_counts':summary['wifi_channels']}
    backend=os.getenv('LABOS_AI_BACKEND','none').strip().lower()
    if backend=='ollama':
        model=os.getenv('OLLAMA_MODEL','qwen2.5:1.5b')
        url='http://127.0.0.1:11434/api/chat'
        messages=[{'role':'system','content':'你是无线实验数据顾问，只解释数据和协议。不会操作设备，不能将没有采样的数据说成实测。对任何异常只陈述统计证据和局限，不提供干扰或入侵指导。'},
                  {'role':'user','content':query+'\n近期数据概况（原样来源标识）：'+json.dumps(context,ensure_ascii=False)}]
        req=urllib.request.Request(url,json.dumps({'model':model,'stream':False,'messages':messages}).encode(),
                                   {'Content-Type':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=55) as response:
                raw=response.read(2_000_000)
            text=str(json.loads(raw)['message']['content'])[:11000]
            return {'backend':'ollama','answer':text,'source':'summary','executed':False}
        except Exception as exc:
            return {'backend':'rules','answer':f'本地 Ollama 未就绪：{str(exc)[:180]}\n\n'+GUIDE,
                    'source':'summary','executed':False}
    if 'rf' in query.lower() or '射频' in query or 'cc1101' in query.lower():
        v=summary['rf']; message=(f'已有 {v["count"]} 条 CC1101 RSSI 记录；'
        + (f'均值 {v["mean"]} dBm、标准差 {v["stdev"]} dB。' if v['count'] else '尚无 RF 测量。')
        + '请核对天线、频段与测试距离；RSSI 扫描不等于 SDR 频谱。')
    elif 'wifi' in query.lower() or '信道' in query or '无线' in query:
        message=f'WiFi 采样 {summary["wifi"]["count"]} 条，信道计数 {summary["wifi_channels"]}。扫描频率和采样环境会影响计数；不等于吞吐率。'
    elif '蓝牙' in query or 'ble' in query.lower():
        message=f'BLE 广播样本 {summary["ble"]["count"]} 条。名称/MAC 不足以证明设备真实身份，随机地址可发生变化。'
    elif 'nfc' in query.lower() or '标签' in query:
        message=f'NFC 类型分布：{summary["nfc_types"]}。当前驱动以 NFC-A 标签识别为主，不涵盖所有 NFC 协议。'
    else:
        message=f'{GUIDE}\n当前数据库可见记录：{summary["total"]} 条；来源分布 {summary["sources"]}。'
    return {'backend':'rules','answer':message,'source':'summary','executed':False}
