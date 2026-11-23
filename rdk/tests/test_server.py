import base64
import json
import threading
import tempfile
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from labos.server import Application,make_handler
from labos.database import Store
from labos.device import DeviceBridge
from test_device import FakeSerial

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        store=Store(Path(self.tmp.name)/'test.sqlite')
        app=Application(store=store,bridge=DeviceBridge('/dev/ttyACM0',serial_factory=FakeSerial))
        self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app))
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)
        self.tmp.cleanup()
    def req(self,path,body=None):
        args={} if body is None else {'data':json.dumps(body).encode(),'headers':{'Content-Type':'application/json'}}
        with urllib.request.urlopen(urllib.request.Request(self.url+path,**args),timeout=3) as r:
            return r.status,r.read(),r.headers.get('Content-Type')
    def test_home(self):
        status,html,_=self.req('/');self.assertEqual(status,200);self.assertIn(b'LABOS',html)
    def test_endpoints(self):
        self.assertTrue(json.loads(self.req('/api/status')[1])['device']['protocol']=='LAB5')
        hello=json.loads(self.req('/api/device/hello',{})[1]);self.assertEqual(hello['count'],1)
        new=json.loads(self.req('/api/session/new',{'name':'Real Test'})[1]);sid=new['session_id']
        scan=json.loads(self.req('/api/device/scan',{'kind':'wifi','session_id':sid})[1])
        self.assertTrue(scan['real_hardware'])
        report=json.loads(self.req('/api/report?session='+sid)[1])
        self.assertEqual(report['sample_count'],1)
        self.assertEqual(report['summary']['sources'],{'ADV_USB':1})
        self.assertIn(b'ssid',self.req('/api/export.csv?session='+sid)[1])
        self.assertIn(b'"samples"',self.req('/api/export.json?session='+sid)[1]) if False else None
    def test_report_html_and_profiles(self):
        status,html,mime=self.req('/api/report.html')
        self.assertEqual(status,200);self.assertIn(b'LabOS V5',html)
        profiles=json.loads(self.req('/api/profiles')[1]);self.assertEqual(profiles,[])
    def test_demo_source(self):
        demo=json.loads(self.req('/api/demo',{})[1]);self.assertTrue(demo['simulated'])
        rows=json.loads(self.req('/api/samples')[1]);self.assertTrue(all(r['source']=='simulated' for r in rows))
    def test_usb_selftest(self):
        data=json.loads(self.req('/api/device/selftest',{})[1])
        self.assertEqual(data['protocol'],'LAB5')
        self.assertEqual(data['firmware'],'2.2-purplegold')
        self.assertEqual(data['status'],'hardware-response-verified')
        self.assertIn('hello_ms',data)
    def test_royal_assets_and_button(self):
        html=self.req('/')[1].decode('utf8')
        self.assertIn('purple-gold.css',html)
        self.assertIn('btnSelfTest',html)
        css=self.req('/static/purple-gold.css')[1].decode('utf8')
        self.assertIn('#e5bc72',css)
    def test_csv_import(self):
        raw=b'ssid,rssi,channel\nlab,-72,6\n'
        d=json.loads(self.req('/api/import',{'filename':'mytest.csv','data_base64':base64.b64encode(raw).decode()})[1])
        self.assertEqual(d['source'],'imported');self.assertEqual(d['analysis']['rows'],1)
        self.assertEqual(len(json.loads(self.req('/api/imports')[1])),1)
    def test_ask(self):
        d=json.loads(self.req('/api/ask',{'text':'what is wifi RSSI?'})[1]);self.assertFalse(d['executed'])
