import collections
import unittest
from labos.device import DeviceBridge,DeviceError

class FakeSerial:
    def __init__(self,*args,**kwargs):
        self.is_open=True
        self.q=collections.deque()
        self.mode='normal'
    def write(self,command):
        rid=int(command.decode().split('|')[1]);cmd=command.decode().split('|')[2].strip()
        self.q.append(b'[BD] heartbeat\n')
        if cmd=='HELLO':
            self.q.append(f'LAB5|{rid}|item|{{"protocol":"LAB5"}}\n'.encode())
            self.q.append(f'LAB5|{rid}|end|{{"count":1}}\n'.encode())
        elif cmd=='INFO':
            self.q.append(f'LAB5|{rid}|item|{{"firmware":"2.2-purplegold","board":"Cardputer-Adv","flash_bytes":8388608,"free_heap":220000,"psram":0}}\n'.encode())
            self.q.append(f'LAB5|{rid}|end|{{"count":1}}\n'.encode())
        elif cmd=='WIFI_SCAN':
            self.q.append(f'LAB5|{rid}|begin|{{"kind":"wifi"}}\n'.encode())
            self.q.append(f'LAB5|{rid}|item|{{"ssid":"lab","rssi":-70,"channel":6}}\n'.encode())
            self.q.append(f'LAB5|{rid}|end|{{"count":1}}\n'.encode())
        elif cmd=='RF_SAMPLE':
            self.q.append(f'LAB5|{rid}|begin|{{"kind":"rf"}}\n'.encode())
            self.q.append(f'LAB5|{rid}|end|{{"count":9}}\n'.encode())
    def readline(self):return self.q.popleft() if self.q else b''
    def flush(self):pass
    def close(self):self.is_open=False

class BridgeTests(unittest.TestCase):
    def test_hello_and_wifi(self):
        b=DeviceBridge('/dev/ttyACM0',serial_factory=FakeSerial)
        self.assertTrue(b.hello()['ok'])
        d=b.measure('wifi');self.assertEqual(d['items'][0]['ssid'],'lab')
        self.assertTrue(b.status()['connected'])
        b.close();self.assertFalse(b.status()['connected'])
    def test_mismatch_count(self):
        b=DeviceBridge('/dev/ttyACM0',serial_factory=FakeSerial)
        with self.assertRaises(DeviceError):b.measure('rf')
    def test_unknown_port(self):
        with self.assertRaises(DeviceError):DeviceBridge('/tmp/fake-device',serial_factory=FakeSerial)

class ErrorSerial(FakeSerial):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.variant='end_early'
    def write(self,command):
        rid=int(command.decode().split('|')[1])
        if self.variant=='end_early':
            self.q.append(f'LAB5|{rid}|end|{{"count":0}}\n'.encode())
        elif self.variant=='wrong_protocol':
            self.q.append(f'LAB5|{rid}|item|{{"protocol":"LAB4"}}\n'.encode())
            self.q.append(f'LAB5|{rid}|end|{{"count":1}}\n'.encode())

class ProtocolFaultTests(unittest.TestCase):
    def test_missing_begin(self):
        bridge=DeviceBridge('/dev/ttyACM0',serial_factory=ErrorSerial)
        with self.assertRaises(DeviceError):bridge.measure('wifi')
        self.assertFalse(bridge.status()['connected'])
    def test_wrong_firmware_protocol(self):
        def factory(*a,**kw):
            serial=ErrorSerial(*a,**kw);serial.variant='wrong_protocol';return serial
        bridge=DeviceBridge('/dev/ttyACM0',serial_factory=factory)
        with self.assertRaisesRegex(DeviceError,'协议不匹配'):bridge.hello()
    def test_verified_flag_only_after_response(self):
        bridge=DeviceBridge('/dev/ttyACM0',serial_factory=FakeSerial)
        self.assertFalse(bridge.status()['handshake_verified'])
        x=bridge.hello()
        self.assertTrue(x['ok'])
        self.assertTrue(bridge.status()['handshake_verified'])
        self.assertIsNotNone(bridge.status()['last_rtt_ms'])
        bridge.close()
        self.assertFalse(bridge.status()['handshake_verified'])
