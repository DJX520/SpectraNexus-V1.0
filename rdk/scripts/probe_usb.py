#!/usr/bin/env python3
"""Manual USB smoke test. Never silently simulates connected hardware."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from labos.device import DeviceBridge,DeviceError

p=argparse.ArgumentParser()
p.add_argument('--port',default='auto',help='auto, /dev/ttyACM0, or /dev/serial/by-id/...')
p.add_argument('--command',choices=['hello','info','wifi','ble','rf','rf315','rf868','rf915','nfc'],default='hello')
a=p.parse_args()
try:
    d=DeviceBridge(a.port)
    result=d.hello() if a.command=='hello' else d.info() if a.command=='info' else d.measure(a.command)
    print(json.dumps(result,ensure_ascii=False,indent=2))
finally:
    try:d.close()
    except NameError:pass
