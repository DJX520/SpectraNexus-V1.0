"""Real USB CDC adapter. No synthetic hardware data or arbitrary serial pass-through."""
from __future__ import annotations
from glob import glob
from pathlib import Path
import os
import re
import threading
import time
from .protocol import encode_command,parse_frame,ProtocolError

try:
    import serial
except ImportError:
    serial = None

class DeviceError(RuntimeError):pass

PORT_RE=re.compile(r'^/dev/(?:ttyACM\d+|ttyUSB\d+|serial/by-id/[A-Za-z0-9_.:+-]+)$')
KIND_COMMAND={'wifi':'WIFI_SCAN','ble':'BLE_SCAN','rf':'RF_SAMPLE','rf315':'RF_SAMPLE_315','rf868':'RF_SAMPLE_868','rf915':'RF_SAMPLE_915','nfc':'NFC_SCAN'}

class DeviceBridge:
    def __init__(self,port: str | None = None, serial_factory=None):
        self.port=(port if port is not None else os.environ.get('LABOS_SERIAL','auto')).strip()
        if self.port!='auto' and not PORT_RE.fullmatch(self.port):
            raise DeviceError('串口只能位于 /dev/ttyACM*, /dev/ttyUSB* 或 /dev/serial/by-id/ 下')
        self.serial_factory=serial_factory
        self._serial=None
        self._lock=threading.RLock()
        self._seq=0
        self.last_seen=0.0
        self._verified=False
        self.last_rtt_ms=None
        self.last_error='尚未连接'
        self.connected_port=None
        self.diagnostic_lines=[]

    def _select_port(self):
        if self.port!='auto':return self.port
        choices=sorted(glob('/dev/serial/by-id/*')) + sorted(glob('/dev/ttyACM*')) + sorted(glob('/dev/ttyUSB*'))
        return next((s for s in choices if PORT_RE.fullmatch(s)), None)

    def _open(self):
        if self._serial is not None and getattr(self._serial,'is_open',True):return
        port=self._select_port()
        if not port:raise DeviceError('未找到 ADV USB 串口；请检查接线、USB CDC On Boot 与串口权限')
        if serial is None and self.serial_factory is None:
            raise DeviceError('缺少 pyserial，请安装 requirements.txt')
        factory=self.serial_factory or serial.Serial
        try:
            self._serial=factory(port,115200,timeout=0.15,write_timeout=2)
        except Exception as exc:
            self._serial=None
            raise DeviceError(f'无法打开串口 {port}: {exc}') from exc
        self.connected_port=port

    def close(self):
        with self._lock:
            old=self._serial;self._serial=None;self.connected_port=None
            self._verified=False
            if old:
                try:old.close()
                except Exception:pass

    def status(self):
        return {'port_setting':self.port,'connected_port':self.connected_port,
                'connected':bool(self._serial and getattr(self._serial,'is_open',True) and self._verified),
                'serial_open':bool(self._serial and getattr(self._serial,'is_open',True)),
                'handshake_verified':self._verified,'last_rtt_ms':self.last_rtt_ms,
                'last_seen':self.last_seen,'last_error':self.last_error,
                'protocol':'LAB5','source':'actual_usb'}

    def request(self,command:str,timeout:float=18.0):
        with self._lock:
            try:
                return self._request(command,timeout)
            except (DeviceError,ProtocolError,OSError) as exc:
                self.last_error=str(exc)
                self.close()
                raise DeviceError(str(exc)) from exc

    def _request(self,command,timeout):
        self._open()
        self._seq=(self._seq%99999998)+1
        rid=self._seq
        wire=encode_command(rid,command)
        t0=time.monotonic()
        try:
            self._serial.write(wire)
            self._serial.flush()
        except Exception as exc:raise DeviceError(f'USB 发送失败: {exc}') from exc
        items=[];started=False;begin={};finish={};errors=0
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try: raw=self._serial.readline()
            except Exception as exc:raise DeviceError(f'USB 读取失败: {exc}') from exc
            if not raw:continue
            if len(raw)>2048:raise ProtocolError('输入帧过长')
            frame=parse_frame(raw)
            if not frame:
                # Pre-existing BlackDeck log lines coexist with structured LAB5.
                if len(self.diagnostic_lines)>20:self.diagnostic_lines.pop(0)
                self.diagnostic_lines.append(raw[:120].decode('utf-8','replace').strip())
                continue
            if frame.request_id!=rid:continue
            if frame.kind=='error':raise DeviceError(str(frame.data.get('message') or frame.data.get('code') or '设备错误')[:150])
            if frame.kind=='begin':
                if started:raise ProtocolError('重复的 begin 帧')
                started=True;begin=frame.data
            elif frame.kind=='item':
                if len(items)>=128:raise ProtocolError('单次样本数过大')
                if command not in ('HELLO','INFO') and not started:raise ProtocolError('item 帧早于 begin 帧')
                items.append(frame.data)
            elif frame.kind=='end':
                if command not in ('HELLO','INFO') and not started:raise ProtocolError('缺少 begin 帧')
                finish=frame.data
                count=finish.get('count')
                if not isinstance(count,int) or count!=len(items):
                    raise ProtocolError(f'样本数量不一致: 设备声明 {count}，实际 {len(items)}')
                if command=='HELLO':
                    if len(items)!=1 or items[0].get('protocol')!='LAB5':
                        raise ProtocolError('设备协议不匹配（需要 LAB5）')
                if command=='INFO' and (len(items)!=1 or not items[0].get('firmware')):
                    raise ProtocolError('固件 INFO 数据缺失')
                self.last_seen=time.time();self.last_error=''
                self._verified=True
                self.last_rtt_ms=round((time.monotonic()-t0)*1000,1)
                return {'ok':True,'command':command,'items':items,'begin':begin,'end':finish,
                        'count':len(items),'port':self.connected_port,'source':'ADV_USB',
                        'round_trip_ms':self.last_rtt_ms}
        raise DeviceError(f'{command} 超时（{timeout:.0f}s）；检查 ADV 是否停留在耗时 AI 推理/扫描界面')

    def hello(self):return self.request('HELLO',timeout=6)
    def info(self):return self.request('INFO',timeout=8)
    def measure(self,kind):
        if kind not in KIND_COMMAND:raise DeviceError('不支持此种采集类型')
        return self.request(KIND_COMMAND[kind],timeout=32 if kind in ('wifi','ble') else 12)
