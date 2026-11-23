"""Real OS pseudo-terminal round-trip, without claiming any physical Cardputer was used."""
import os
import select
import threading
import tty
import unittest
from labos.device import DeviceBridge

class PTYSerial:
    def __init__(self,path,baud,timeout=0.15,write_timeout=2):
        self.fd=os.open(path,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
        self.timeout=timeout
        self.is_open=True
        self.buffer=bytearray()
    def write(self,b):
        return os.write(self.fd,b)
    def flush(self):pass
    def readline(self):
        ready,_,_=select.select([self.fd],[],[],self.timeout)
        if ready:
            try:self.buffer.extend(os.read(self.fd,4096))
            except BlockingIOError:pass
        index=self.buffer.find(b'\n')
        if index<0:return b''
        result=bytes(self.buffer[:index+1])
        del self.buffer[:index+1]
        return result
    def close(self):
        self.is_open=False
        os.close(self.fd)

class PTYTransportTests(unittest.TestCase):
    def test_wire_hello_info_wifi_and_nfc(self):
        master,slave=os.openpty()
        tty.setraw(slave)
        slave_name=os.ttyname(slave)
        stop=threading.Event()
        def worker():
            pending=b''
            while not stop.is_set():
                readable,_,_=select.select([master],[],[],0.1)
                if not readable:continue
                try:pending+=os.read(master,4096)
                except OSError:break
                while b'\n' in pending:
                    line,pending=pending.split(b'\n',1)
                    fields=line.decode('ascii').split('|')
                    if len(fields)!=3 or fields[0]!='L5':continue
                    rid,cmd=fields[1:]
                    if cmd=='HELLO':
                        items=['{"protocol":"LAB5","device":"test-emulator"}'];begin=''
                    elif cmd=='INFO':
                        items=['{"firmware":"test-2.2","board":"Cardputer-Adv","flash_bytes":8388608}'];begin=''
                    elif cmd=='WIFI_SCAN':
                        items=['{"ssid":"实验路由器","channel":6,"rssi":-63}'];begin='{"kind":"wifi"}'
                    elif cmd=='NFC_SCAN':
                        items=[];begin='{"kind":"nfc"}'
                    else:items=[];begin=''
                    lines=[]
                    if begin:lines.append(f'LAB5|{rid}|begin|{begin}\n')
                    for item in items:lines.append(f'LAB5|{rid}|item|{item}\n')
                    lines.append(f'LAB5|{rid}|end|{{"count":{len(items)}}}\n')
                    os.write(master,(''.join(lines)).encode('utf-8'))
        thread=threading.Thread(target=worker,daemon=True);thread.start()
        try:
            bridge=DeviceBridge('/dev/ttyACM0',serial_factory=PTYSerial)
            bridge._select_port=lambda:slave_name
            self.assertEqual(bridge.hello()['items'][0]['protocol'],'LAB5')
            self.assertEqual(bridge.info()['items'][0]['flash_bytes'],8388608)
            self.assertEqual(bridge.measure('wifi')['items'][0]['ssid'],'实验路由器')
            self.assertEqual(bridge.measure('nfc')['count'],0)
            self.assertTrue(bridge.status()['connected'])
            bridge.close()
        finally:
            stop.set();thread.join(timeout=2)
            os.close(master);os.close(slave)
