import tempfile
import unittest
from pathlib import Path
from labos.database import Store
from labos.analytics import summarize,anomalies

class DBTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory();self.store=Store(Path(self.dir.name)/'d.sqlite')
    def tearDown(self):self.dir.cleanup()
    def test_session_and_run(self):
        sid=self.store.create_session('Lab','distance 1m')
        rec=self.store.save_run('wifi',[{'ssid':'test','rssi':-55,'channel':6}],session_id=sid)
        rows=self.store.samples(sid)
        self.assertEqual(rows[0]['data']['channel'],6)
        self.assertEqual(rec['source'],'ADV_USB')
        self.assertEqual(summarize(rows)['wifi']['mean'],-55.0)
        self.store.end_session(sid)
        with self.assertRaises(ValueError):self.store.save_run('wifi',[],session_id=sid)
    def test_source(self):
        with self.assertRaises(ValueError):self.store.save_run('wifi',[],source='fabricated')
    def test_anomalies(self):
        values=[-80,-81,-82,-79,-81,-82,-80,-79,-80,-35]
        self.store.save_run('rf',[{'rssi':v} for v in values],source='simulated')
        flags=anomalies(self.store.samples())
        self.assertEqual(len(flags),1)
        self.assertEqual(flags[0]['value'],-35)

class ProfileTests(unittest.TestCase):
    def test_pseudonymous_profiles(self):
        from labos.analytics import profiles
        rows=[{'kind':'ble','source':'ADV_USB','data':{'address':'aa:bb:cc','rssi':-64},'stamp_utc':'2026-11-22','batch_id':'ab','id':1},
              {'kind':'wifi','source':'ADV_USB','data':{'bssid':'aa:bb:cc','rssi':-55},'stamp_utc':'2026-11-22','batch_id':'cd','id':2}]
        p=profiles(rows,b'salt')
        self.assertEqual(len(p),2)
        self.assertTrue(all('aa:bb:cc' not in str(x) for x in p))
