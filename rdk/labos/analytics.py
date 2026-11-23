"""Transparent descriptive statistics and lightweight anomaly screening, not an attack detector."""
from __future__ import annotations
from collections import Counter,defaultdict
import math
import statistics

def summarize(rows:list[dict])->dict:
    types=Counter(r['kind'] for r in rows)
    sources=Counter(r['source'] for r in rows)
    rf=[];wifi=[];ble=[];nfc=[];channels=Counter()
    for r in rows:
        d=r['data'];kind=r['kind'];raw=d.get('rssi')
        if kind in ('wifi','ble','rf') and isinstance(raw,(int,float)) and math.isfinite(raw):
            if kind=='rf':rf.append(float(raw))
            elif kind=='wifi':wifi.append(float(raw))
            else:ble.append(float(raw))
        if kind=='wifi':channels[str(d.get('channel','?'))]+=1
        if kind=='nfc':nfc.append(d.get('tag_type','unknown'))
    def signal(x):
        if not x:return {'count':0,'mean':None,'min':None,'max':None,'stdev':None}
        return {'count':len(x),'mean':round(statistics.mean(x),2),
                'min':round(min(x),2),'max':round(max(x),2),
                'stdev':round(statistics.stdev(x),2) if len(x)>1 else 0.0}
    return {'total':len(rows),'kinds':dict(types),'sources':dict(sources),
            'rf':signal(rf),'wifi':signal(wifi),'ble':signal(ble),
            'wifi_channels':dict(channels),'nfc_types':dict(Counter(nfc)),
            'limitations':['RSSI 强度不是频谱功率校准值','WiFi/BLE 扫描并不代表流量吞吐或丢包测量',
                           '异常检测仅为统计筛选，不等同于攻击归因']}

def anomalies(rows:list[dict]):
    """Flag only outliers in a homogeneous RF batch with >=8 values."""
    groups=defaultdict(list)
    for r in rows:
        if r['kind']=='rf' and isinstance(r['data'].get('rssi'),(float,int)):
            groups[r['batch_id']].append(r)
    flags=[]
    for batch,rr in groups.items():
        if len(rr)<8:continue
        values=[float(r['data']['rssi']) for r in rr]
        center=statistics.median(values)
        mad=statistics.median(abs(x-center) for x in values)
        if mad<0.5:continue
        for row,x in zip(rr,values):
            robust_z=0.6745*(x-center)/mad
            if abs(robust_z)>=3.5:
                flags.append({'batch_id':batch,'sample_id':row['id'],'value':x,
                              'median':round(center,2),'robust_z':round(robust_z,2),
                              'finding':'仅显示统计离群值，不判断攻击来源'})
    return flags[:100]

def profiles(rows:list[dict], salt:bytes):
    """Pseudonymous observed identifiers, never infer cross-radio device identity."""
    import hashlib
    grouped={}
    for r in rows:
        d=r['data'];kind=r['kind']
        key=(d.get('bssid') if kind=='wifi' else d.get('address') if kind=='ble'
             else d.get('uid') if kind=='nfc' else None)
        if not isinstance(key,str) or not key or len(key)>90:continue
        digest=hashlib.sha256(salt+kind.encode()+key.encode('utf-8')).hexdigest()[:12]
        uid=f'{kind}:{digest}'
        item=grouped.setdefault(uid,{'profile_id':uid,'protocol':kind,'observations':0,
                                     'last_seen':r['stamp_utc'],'last_rssi':None,
                                     'warning':'仅表示相同可观测标识，不证明物理设备身份'})
        item['observations']+=1
        item['last_seen']=r['stamp_utc']
        if isinstance(d.get('rssi'),(int,float)):item['last_rssi']=d['rssi']
    return sorted(grouped.values(),key=lambda item:(-item['observations'],item['profile_id']))[:150]
