"""V5.1 showcase static assets are served by the local HTTP app."""
import tempfile,threading,unittest,urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer
from labos.server import Application,make_handler
from labos.database import Store
from labos.device import DeviceBridge
from test_device import FakeSerial

class ShowcaseAssets(unittest.TestCase):
    def test_page_and_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'labos.sqlite')
            app=Application(store=store,bridge=DeviceBridge('/dev/ttyACM0',serial_factory=FakeSerial))
            server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(app))
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                base=f'http://127.0.0.1:{server.server_port}'
                for path,marker in [
                    ('/','id="showcaseStage"'),
                    ('/static/showcase.js','SIMULATED'),
                    ('/static/showcase.css','.showcase-stage'),
                ]:
                    with urllib.request.urlopen(base+path,timeout=3) as r:
                        self.assertEqual(r.status,200)
                        self.assertIn(marker,r.read().decode('utf8'))
                        self.assertEqual(r.headers.get('X-Content-Type-Options'),'nosniff')
            finally:
                server.shutdown();server.server_close();worker.join(timeout=2)
