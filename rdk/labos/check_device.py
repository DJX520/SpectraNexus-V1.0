"""CLI USB check: no scan or transmission unless user explicitly requests one."""
import argparse
import json
import sys
from .device import DeviceBridge,DeviceError,KIND_COMMAND

def main(argv=None):
    p=argparse.ArgumentParser(description='BlackDeck LAB5 USB 通信检测')
    p.add_argument('--port',default='auto',help='auto 或 /dev/serial/by-id/xxx 或 /dev/ttyACM0')
    p.add_argument('--scan',choices=list(KIND_COMMAND),help='明确指定后执行一次指定的只读采集')
    args=p.parse_args(argv)
    try:
        bridge=DeviceBridge(port=args.port)
        hello=bridge.hello()
        info=bridge.info()
        result={'ok':True,'protocol':'LAB5','port':info['port'],
                'hello_ms':hello['round_trip_ms'],'info_ms':info['round_trip_ms'],
                'device':info['items'][0],'scan':None,
                'warning':'通信检查成功并不代表射频、NFC、BLE 功能均已实物验收'}
        if args.scan:
            result['scan']=bridge.measure(args.scan)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        bridge.close()
        return 0
    except DeviceError as exc:
        print('通信失败：'+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
