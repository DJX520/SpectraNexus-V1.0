"""Offline summaries of PCAP (802.11) and Wi-Fi RSSI CSV.
No injection, network capture, password recovery, or decryption.
Uses only Python standard library.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import csv,io,struct,math

MAX_FILE=8*1024*1024
MAX_PACKETS=50000

class AnalysisError(ValueError): pass

def _bytes(raw):
    if not raw or len(raw)>MAX_FILE:
        raise AnalysisError('文件为空或超过 8 MiB')
    return raw

def pcap_summary(raw:bytes) -> dict:
    raw=_bytes(raw)
    if len(raw)<24: raise AnalysisError('文件不足 PCAP 头部长度')
    magic=raw[:4]
    end={b'\xd4\xc3\xb2\xa1':'<',b'\xa1\xb2\xc3\xd4':'>',
         b'\x4d\x3c\xb2\xa1':'<',b'\xa1\xb2\x3c\x4d':'>'}.get(magic)
    if not end:raise AnalysisError('仅支持传统 .pcap 格式（不支持 pcapng）')
    try:
        _,_,_,_,_,link=struct.unpack(end+'HHIIII',raw[4:24])
    except struct.error as e: raise AnalysisError('PCAP 全局头损坏') from e
    if link not in (105,127):
        raise AnalysisError(f'仅支持 IEEE 802.11 (105) / Radiotap (127)，实际链路类型 {link}')
    pos=24; total=0; sampled=0; malformed=0; counters=Counter(); buckets=defaultdict(Counter); first=None
    while pos+16<=len(raw) and total<MAX_PACKETS:
        try: sec,sub,incl,original=struct.unpack(end+'IIII',raw[pos:pos+16])
        except struct.error: break
        pos+=16
        if incl>len(raw)-pos:
            malformed+=1;break
        pkt=raw[pos:pos+incl];pos+=incl;total+=1
        if incl<2:malformed+=1;continue
        if link==127:
            if len(pkt)<8:malformed+=1;continue
            rtlen=int.from_bytes(pkt[2:4],'little')
            if rtlen<8 or rtlen+2>len(pkt):malformed+=1;continue
            frame=pkt[rtlen:]
        else:frame=pkt
        if len(frame)<2:malformed+=1;continue
        fc=frame[0]|(frame[1]<<8)
        typ=(fc>>2)&3;subtype=(fc>>4)&15
        if typ!=0: category='other'
        elif subtype==12: category='deauth'
        elif subtype==10: category='disassoc'
        elif subtype==8: category='beacon'
        elif subtype in (4,5):category='probe'
        else: category='other_mgmt'
        counters[category]+=1;sampled+=1
        if first is None:first=sec
        bucket=max(0,int(sec-first))//5
        if bucket<1440:buckets[bucket][category]+=1
    if pos!=len(raw) and total<MAX_PACKETS:malformed+=1
    events=sum(counters[k] for k in ('deauth','disassoc'))
    timeline=[{'t':b*5,'deauth':buckets[b]['deauth'],'disassoc':buckets[b]['disassoc'],
               'beacon':buckets[b]['beacon']} for b in sorted(buckets)][:360]
    return {'format':'pcap','linktype':link,'packets':total,'parsed':sampled,'malformed':malformed,
            'counts':dict(counters),'management_events':events,'timeline':timeline,
            'finding':'存在去认证/去关联管理帧事件，不能仅凭计数判断恶意行为。' if events else '本次样本未观察到 Deauth/Dissoc 管理帧。',
            'truncated':total>=MAX_PACKETS}

def wifi_csv_summary(raw:bytes)->dict:
    raw=_bytes(raw)
    try: s=raw.decode('utf-8-sig')
    except UnicodeDecodeError as e:raise AnalysisError('CSV 请使用 UTF-8 编码') from e
    reader=csv.DictReader(io.StringIO(s))
    if not reader.fieldnames:raise AnalysisError('CSV 需要表头')
    fields={name.strip().lower():name for name in reader.fieldnames if name}
    rcol=next((fields[k] for k in ('rssi','signal','signal_dbm','rssi_dbm') if k in fields),None)
    ccol=next((fields[k] for k in ('channel','ch','wifi_channel') if k in fields),None)
    scol=next((fields[k] for k in ('ssid','name','network') if k in fields),None)
    if not rcol:raise AnalysisError('缺少 RSSI 列，支持：rssi、signal、rssi_dbm')
    rows=[];channels=Counter();n=0
    for row in reader:
        n+=1
        if n>10000:break
        try:r=float(str(row.get(rcol,'')).replace('dBm','').strip())
        except (ValueError,TypeError):continue
        if not math.isfinite(r) or not -130<=r<=0:continue
        ch=str(row.get(ccol,'')).strip() if ccol else ''
        ssid=str(row.get(scol,'')).strip()[:50] if scol else ''
        rows.append({'rssi':round(r,1),'channel':ch,'ssid':ssid})
        if ch:channels[ch]+=1
    if not rows:raise AnalysisError('没有有效 RSSI 数据（期望 -130 至 0 dBm）')
    hist=[{'band':f'{lo}~-{abs(hi)}','count':sum(lo<=row['rssi']<hi for row in rows)}
          for lo,hi in [(-130,-90),(-90,-80),(-80,-70),(-70,-60),(-60,-50),(-50,-40),(-40,1)]]
    return {'format':'csv','rows':len(rows),'mean_rssi':round(sum(x['rssi'] for x in rows)/len(rows),1),
            'min_rssi':min(x['rssi'] for x in rows),'max_rssi':max(x['rssi'] for x in rows),
            'channels':[{'channel':c,'count':v} for c,v in channels.most_common(12)],
            'histogram':hist,'samples':rows[-120:],
            'finding':'RSSI 是信号强度指标，不能单凭它判定攻击或破解网络。'}
