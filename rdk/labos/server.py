"""Standard-library HTTP API with bounded input and local-only defaults."""
from __future__ import annotations
import argparse
import base64
import csv
import hashlib
import io
import json
import secrets
import os
import subprocess
import tempfile
import threading
import urllib.parse
from pathlib import Path
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from . import __version__
from .database import Store
from .device import DeviceBridge,DeviceError,KIND_COMMAND
from .protocol import ProtocolError
from .analytics import summarize,anomalies,profiles
from .reporting import render_report
from .import_analysis import pcap_summary,wifi_csv_summary,AnalysisError
from .assistant import answer
from .audio import normalize_wav,make_wav

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'static'
DB_PATH=Path(os.environ.get('LABOS_DATA_DIR',str(ROOT/'data'))).expanduser()/'labos5.sqlite'
MAX_JSON=12_000_000
SAMPLE_LIMIT=5000

class Application:
    def __init__(self,store=None,bridge=None):
        self.store=store or Store(DB_PATH)
        self.bridge=bridge or DeviceBridge()
        self._operation_lock=threading.Lock()
        salt_file=self.store.path.parent/'profile_salt.bin'
        if salt_file.exists():self.profile_salt=salt_file.read_bytes()
        else:
            self.profile_salt=secrets.token_bytes(32)
            with open(salt_file,'xb') as f:f.write(self.profile_salt)
            os.chmod(salt_file,0o600)

    def status(self):
        return {'version':__version__,'device':self.bridge.status(),
                'database':str(self.store.path),'sessions':len(self.store.sessions()),
                'source_policy':'ADV_USB=hardware; imported=user-file; simulated=demo-only',
                'ai_backend':os.getenv('LABOS_AI_BACKEND','none'),
                'asr_ready':self.asr_ready()}

    @staticmethod
    def asr_ready():
        return bool(Path(os.getenv('WHISPER_CLI','/opt/whisper.cpp/build/bin/whisper-cli')).is_file()
                    and Path(os.getenv('WHISPER_MODEL','/opt/whisper.cpp/models/ggml-base.bin')).is_file())

    def measure(self,kind,session_id=None):
        if kind not in KIND_COMMAND:raise ValueError('未知类型')
        saved_kind='rf' if kind.startswith('rf') else kind
        if not self._operation_lock.acquire(False):raise RuntimeError('正在执行其他硬件任务')
        try:
            result=self.bridge.measure(kind)
            rec=self.store.save_run(saved_kind,result['items'],'ADV_USB',session_id,
                                    meta={'port':result['port'],'begin':result['begin'],'end':result['end']})
            return {'measurement':rec,'result':result,'real_hardware':True}
        finally:
            self._operation_lock.release()

    def selftest(self):
        """Explicit, non-destructive USB self-test. Never starts RF/WiFi/BLE scans."""
        if not self._operation_lock.acquire(False):
            raise RuntimeError('正在执行其他硬件任务')
        try:
            hello=self.bridge.hello()
            info=self.bridge.info()
            return {'ok':True,'protocol':'LAB5','status':'hardware-response-verified',
                    'port':info['port'], 'hello_ms':hello['round_trip_ms'],
                    'info_ms':info['round_trip_ms'],
                    'firmware':info['items'][0].get('firmware'),
                    'board':info['items'][0].get('board'),
                    'flash_bytes':info['items'][0].get('flash_bytes'),
                    'free_heap':info['items'][0].get('free_heap'),
                    'psram':info['items'][0].get('psram'),
                    'note':'仅校验 LAB5 帧往返和设备信息；RF/NFC/WiFi/BLE 需分别实测'}
        finally:
            self._operation_lock.release()

    def import_data(self,filename,raw,session_id=None):
        name=Path(str(filename)).name[:100]
        if not name.lower().endswith(('.csv','.pcap')):raise ValueError('只接受 CSV 或传统 PCAP 文件')
        if not raw or len(raw)>8*1024*1024:raise ValueError('文件为空或超过 8 MiB')
        summary=wifi_csv_summary(raw) if name.lower().endswith('.csv') else pcap_summary(raw)
        digest=hashlib.sha256(raw).hexdigest()
        sid=self.store.record_import(name,digest,summary,session_id)
        # Raw input is not silently retained. Import summary is immutable and auditable.
        return {'source':'imported','session_id':sid,'sha256':digest,
                'filename':name,'analysis':summary,'raw_retained':False}

    def report(self,sid=None):
        rows=self.store.samples(sid,limit=SAMPLE_LIMIT)
        return {'generated_utc':datetime.now(timezone.utc).isoformat(),
                'session_id':sid,'summary':summarize(rows),'anomalies':anomalies(rows),
                'runs':self.store.runs(sid,100),'imports':self.store.imports(sid,50),'sample_count':len(rows),
                'caveat':'采集结果标明来源；测量没有自动完成校准或攻击归因。'}

    def voice(self,raw):
        exe=os.getenv('WHISPER_CLI','/opt/whisper.cpp/build/bin/whisper-cli')
        model=os.getenv('WHISPER_MODEL','/opt/whisper.cpp/models/ggml-base.bin')
        if not Path(exe).is_file() or not Path(model).is_file():
            raise ValueError('Whisper.cpp 尚未安装；请先配置 WHISPER_CLI 和 WHISPER_MODEL')
        pcm,seconds=normalize_wav(raw)
        with tempfile.TemporaryDirectory(prefix='labos5_asr_') as tmp:
            f=Path(tmp)/'voice.wav';f.write_bytes(make_wav(pcm))
            out=Path(tmp)/'speech'
            try:
                run=subprocess.run([exe,'-m',model,'-f',str(f),'-l','zh','-otxt','-of',str(out),'-nt'],
                                   capture_output=True,text=True,timeout=90)
            except subprocess.TimeoutExpired as exc:raise ValueError('语音识别超时') from exc
            text_file=Path(str(out)+'.txt')
            if run.returncode!=0 or not text_file.exists():raise ValueError('Whisper.cpp 识别失败：'+run.stderr[-200:])
            return {'text':text_file.read_text(encoding='utf-8',errors='replace')[:2000],
                    'seconds':round(seconds,2),'source':'uploaded_wav','backend':'whisper.cpp'}

class Handler(BaseHTTPRequestHandler):
    application:Application|None=None
    server_version=f'LabOS/{__version__}'

    def log_message(self,fmt,*args):
        if os.getenv('LABOS_VERBOSE')=='1':super().log_message(fmt,*args)

    @property
    def app(self):return self.application

    def send_payload(self,data,status=200,content_type='application/json; charset=utf-8',filename=None):
        if isinstance(data,(dict,list)):raw=json.dumps(data,ensure_ascii=False).encode('utf-8')
        elif isinstance(data,str):raw=data.encode('utf-8')
        else:raw=data
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers();self.wfile.write(raw)

    def read_json(self):
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:raise ValueError('请求长度错误')
        if size<1 or size>MAX_JSON:raise ValueError('请求体为空或过大')
        try:body=json.loads(self.rfile.read(size))
        except (json.JSONDecodeError,UnicodeDecodeError):raise ValueError('JSON 格式错误')
        if not isinstance(body,dict):raise ValueError('请求体必须为 JSON 对象')
        return body

    def _origin_ok(self):
        # localhost service; reject cross-origin unsafe browser requests.
        origin=self.headers.get('Origin')
        if not origin:return True
        host=self.headers.get('Host','')
        return origin in ('http://'+host,'https://'+host)

    def do_GET(self):
        try:self._get()
        except (ValueError,DeviceError,ProtocolError,AnalysisError) as exc:self.send_payload({'error':str(exc)},400)
        except Exception as exc:self.send_payload({'error':'内部处理失败','detail':str(exc)[:140]},500)

    def _get(self):
        p=urllib.parse.urlsplit(self.path);path=p.path;q=urllib.parse.parse_qs(p.query)
        sid=q.get('session',[''])[0] or None
        if sid and not (len(sid)==12 and sid.isalnum()):raise ValueError('会话 ID 格式错误')
        if path=='/api/status':return self.send_payload(self.app.status())
        if path=='/api/sessions':return self.send_payload(self.app.store.sessions())
        if path=='/api/runs':return self.send_payload(self.app.store.runs(sid,150))
        if path=='/api/profiles':return self.send_payload(profiles(self.app.store.samples(sid,4000),self.app.profile_salt))
        if path=='/api/imports':return self.send_payload(self.app.store.imports(sid,80))
        if path=='/api/samples':
            kind=q.get('kind',[''])[0] or None
            if kind and kind not in ('wifi','ble','rf','nfc','system'):raise ValueError('类型无效')
            return self.send_payload(self.app.store.samples(sid,limit=1500,kind=kind))
        if path=='/api/report':return self.send_payload(self.app.report(sid))
        if path=='/api/report.html':return self.send_payload(render_report(self.app.report(sid),sid),content_type='text/html; charset=utf-8')
        if path=='/api/export.json':
            rows=self.app.store.samples(sid,SAMPLE_LIMIT)
            return self.send_payload({'report':self.app.report(sid),'records':rows},filename='labos5_export.json')
        if path=='/api/export.csv':
            rows=self.app.store.samples(sid,SAMPLE_LIMIT)
            o=io.StringIO();wr=csv.writer(o);wr.writerow(['id','session_id','kind','source','utc','batch_id','seq','data_json'])
            for r in rows:
                wr.writerow([r['id'],r['session_id'],r['kind'],r['source'],r['stamp_utc'],r['batch_id'],r['seq'],json.dumps(r['data'],ensure_ascii=False)])
            return self.send_payload(o.getvalue(),content_type='text/csv; charset=utf-8',filename='labos5_export.csv')
        if path in ('/','/index.html'):name='index.html'
        elif path in ('/static/app.js','/static/style.css','/static/showcase.js','/static/showcase.css','/static/purple-gold.css'):name=path.split('/')[-1]
        else:return self.send_payload({'error':'页面不存在'},404)
        full=STATIC/name
        mime='text/html; charset=utf-8' if name.endswith('html') else ('text/javascript; charset=utf-8' if name.endswith('js') else 'text/css; charset=utf-8')
        return self.send_payload(full.read_bytes(),content_type=mime)

    def do_POST(self):
        if not self._origin_ok():return self.send_payload({'error':'跨来源请求已拒绝'},403)
        try:self._post()
        except (ValueError,DeviceError,ProtocolError,AnalysisError) as exc:self.send_payload({'error':str(exc)},400)
        except RuntimeError as exc:self.send_payload({'error':str(exc)},409)
        except Exception as exc:self.send_payload({'error':'内部处理失败','detail':str(exc)[:140]},500)

    def _post(self):
        p=urllib.parse.urlsplit(self.path).path
        body=self.read_json()
        if p=='/api/session/new':
            sid=self.app.store.create_session(body.get('name','实验会话'),body.get('notes',''))
            return self.send_payload({'session_id':sid})
        if p=='/api/session/end':
            self.app.store.end_session(str(body.get('session_id','')))
            return self.send_payload({'ok':True})
        if p=='/api/device/selftest':return self.send_payload(self.app.selftest())
        if p=='/api/device/hello':return self.send_payload(self.app.bridge.hello())
        if p=='/api/device/info':
            info=self.app.bridge.info()
            self.app.store.save_run('system',info['items'],'ADV_USB',body.get('session_id') or None)
            return self.send_payload(info)
        if p=='/api/device/scan':
            return self.send_payload(self.app.measure(str(body.get('kind','')),
                                                     body.get('session_id') or None))
        if p=='/api/import':
            filename=body.get('filename','');encoded=body.get('data_base64','')
            if not isinstance(encoded,str) or len(encoded)>MAX_JSON:raise ValueError('导入数据过大')
            try:raw=base64.b64decode(encoded,validate=True)
            except Exception:raise ValueError('Base64 数据无效')
            return self.send_payload(self.app.import_data(filename,raw,body.get('session_id') or None))
        if p=='/api/demo':
            # Explicit simulated data; always tagged. Never presented as hardware data.
            samples=[{'frequency_hz':433920000,'rssi':v,'sample_index':i}
                     for i,v in enumerate([-81,-80,-83,-82,-84,-81,-80,-78,-82,-81,-62,-80])]
            rec=self.app.store.save_run('rf',samples,'simulated',body.get('session_id') or None,
                                        meta={'note':'demo sample, not measured'})
            return self.send_payload({'measurement':rec,'simulated':True})
        if p=='/api/ask':
            rows=self.app.store.samples(body.get('session_id') or None,limit=500)
            return self.send_payload(answer(body.get('text',''),rows))
        if p=='/api/voice':
            value=body.get('data_base64','')
            if not isinstance(value,str) or len(value)>MAX_JSON:raise ValueError('音频过大')
            try:raw=base64.b64decode(value,validate=True)
            except Exception:raise ValueError('Base64 音频损坏')
            return self.send_payload(self.app.voice(raw))
        self.send_payload({'error':'未知 API'},404)

def make_handler(application):
    class ConfiguredHandler(Handler):
        pass
    ConfiguredHandler.application=application
    return ConfiguredHandler

def serve(host='127.0.0.1',port=8080,app=None):
    if host not in ('127.0.0.1','::1','localhost'):
        raise RuntimeError('安全限制：默认只允许 127.0.0.1；请通过 SSH 隧道访问')
    app=app or Application()
    with ThreadingHTTPServer((host,port),make_handler(app)) as server:
        print(f'LabOS V{__version__} http://{host}:{port} / data={app.store.path}',flush=True)
        server.serve_forever(poll_interval=0.5)

def main():
    parser=argparse.ArgumentParser(description='BlackDeck LabOS V5 local research station')
    parser.add_argument('--host',default=os.getenv('LABOS_BIND','127.0.0.1'))
    parser.add_argument('--port',type=int,default=int(os.getenv('LABOS_PORT','8080')))
    args=parser.parse_args()
    serve(args.host,args.port)

if __name__=='__main__':main()
