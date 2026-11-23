import unittest
from labos.protocol import encode_command,parse_frame,ProtocolError

class ProtocolTests(unittest.TestCase):
    def test_hello(self):self.assertEqual(encode_command(21,'HELLO'),b'L5|21|HELLO\n')
    def test_reject_commands(self):
        for command in ('TX','DEAUTH','SHOW','INFO\nL5|5|TX'):
            with self.assertRaises(ProtocolError):encode_command(1,command)
    def test_parse(self):
        p=parse_frame(b'LAB5|91|item|{"rssi":-83,"ssid":"Test"}\n')
        self.assertEqual((p.request_id,p.kind,p.data['rssi']),(91,'item',-83))
    def test_logs_are_not_frames(self):self.assertIsNone(parse_frame(b'[BD] boot=ok\n'))
    def test_json_invalid(self):
        with self.assertRaises(ProtocolError):parse_frame('LAB5|2|item|{notjson}')
    def test_len_limit(self):
        with self.assertRaises(ProtocolError):parse_frame('LAB5|'+'x'*3000)
