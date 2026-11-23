"""SQLite WAL experiment store; all data is tagged as real, imported, or demo."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json
import sqlite3
import threading
import time
import uuid

class Store:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        with self._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, opened_utc TEXT NOT NULL,
                    closed_utc TEXT, notes TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                    kind TEXT NOT NULL, source TEXT NOT NULL, stamp_utc TEXT NOT NULL,
                    batch_id TEXT NOT NULL, seq INTEGER NOT NULL, data_json TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS ix_measure_sid ON measurements(session_id,id);
                CREATE INDEX IF NOT EXISTS ix_measure_kind ON measurements(kind,id);
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, kind TEXT NOT NULL,
                    source TEXT NOT NULL, stamp_utc TEXT NOT NULL, count INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS imports (
                    id TEXT PRIMARY KEY, session_id TEXT, filename TEXT, sha256 TEXT,
                    stamp_utc TEXT, summary_json TEXT NOT NULL);
            ''')

    def _connect(self):
        db=sqlite3.connect(self.path,timeout=8)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA busy_timeout=4000')
        return db

    @staticmethod
    def stamp():return datetime.now(timezone.utc).isoformat(timespec='seconds')

    def create_session(self,name:str='实验会话',notes:str=''):
        sid=uuid.uuid4().hex[:12];name=str(name).strip()[:80] or '实验会话';notes=str(notes)[:500]
        with self.lock,self._connect() as db:
            db.execute('INSERT INTO sessions VALUES (?,?,?,?,?)',(sid,name,self.stamp(),None,notes))
        return sid

    def ensure_session(self,session_id=None):
        if session_id:
            with self.lock,self._connect() as db:
                row=db.execute('SELECT id,closed_utc FROM sessions WHERE id=?',(session_id,)).fetchone()
            if not row:raise ValueError('会话不存在')
            if row[1]:raise ValueError('会话已经结束')
            return session_id
        with self.lock,self._connect() as db:
            row=db.execute('SELECT id FROM sessions WHERE closed_utc IS NULL ORDER BY opened_utc DESC LIMIT 1').fetchone()
        return row[0] if row else self.create_session()

    def end_session(self,sid):
        with self.lock,self._connect() as db:
            c=db.execute('UPDATE sessions SET closed_utc=? WHERE id=? AND closed_utc IS NULL',(self.stamp(),sid))
        if not c.rowcount:raise ValueError('会话无效或已结束')

    def sessions(self):
        with self.lock,self._connect() as db:
            records=db.execute('SELECT id,name,opened_utc,closed_utc,notes FROM sessions ORDER BY opened_utc DESC LIMIT 150').fetchall()
        return [dict(zip(('id','name','opened_utc','closed_utc','notes'),r)) for r in records]

    def save_run(self,kind,items,source='ADV_USB',session_id=None,meta=None):
        if kind not in ('wifi','ble','rf','nfc','system','import'):
            raise ValueError('测量类型无效')
        if source not in ('ADV_USB','imported','simulated'):
            raise ValueError('测量来源无效')
        if not isinstance(items,list) or len(items)>128:
            raise ValueError('样本列表过大')
        sid=self.ensure_session(session_id)
        stamp=self.stamp();batch=uuid.uuid4().hex[:16]
        rows=[(sid,kind,source,stamp,batch,i,json.dumps(d,ensure_ascii=False,separators=(',',':')))
              for i,d in enumerate(items) if isinstance(d,dict)]
        with self.lock,self._connect() as db:
            db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?)',
                       (batch,sid,kind,source,stamp,len(rows),json.dumps(meta or {},ensure_ascii=False)))
            db.executemany('INSERT INTO measurements(session_id,kind,source,stamp_utc,batch_id,seq,data_json) VALUES (?,?,?,?,?,?,?)',rows)
        return {'batch_id':batch,'session_id':sid,'count':len(rows),'source':source,'kind':kind}

    def samples(self,session_id=None,limit=2000,kind=None):
        sql='SELECT id,session_id,kind,source,stamp_utc,batch_id,seq,data_json FROM measurements WHERE 1=1'
        args=[]
        if session_id:sql+=' AND session_id=?';args.append(session_id)
        if kind:sql+=' AND kind=?';args.append(kind)
        sql+=' ORDER BY id DESC LIMIT ?';args.append(max(1,min(5000,int(limit))))
        with self.lock,self._connect() as db:
            rows=db.execute(sql,args).fetchall()
        out=[]
        for r in reversed(rows):
            out.append(dict(id=r[0],session_id=r[1],kind=r[2],source=r[3],stamp_utc=r[4],batch_id=r[5],seq=r[6],data=json.loads(r[7])))
        return out

    def runs(self,session_id=None,limit=100):
        sql='SELECT id,session_id,kind,source,stamp_utc,count,metadata_json FROM runs'
        args=[]
        if session_id:sql+=' WHERE session_id=?';args.append(session_id)
        sql+=' ORDER BY stamp_utc DESC,id DESC LIMIT ?';args.append(max(1,min(300,int(limit))))
        with self.lock,self._connect() as db:rows=db.execute(sql,args).fetchall()
        return [dict(id=r[0],session_id=r[1],kind=r[2],source=r[3],utc=r[4],count=r[5],metadata=json.loads(r[6])) for r in rows]

    def record_import(self,filename,sha256,summary,session_id=None):
        sid=self.ensure_session(session_id)
        with self.lock,self._connect() as db:
            db.execute('INSERT INTO imports VALUES (?,?,?,?,?,?)',
                (uuid.uuid4().hex[:12],sid,str(filename)[:100],sha256,self.stamp(),json.dumps(summary,ensure_ascii=False)))
        return sid

    def imports(self,session_id=None,limit=80):
        sql='SELECT id,session_id,filename,sha256,stamp_utc,summary_json FROM imports'
        args=[]
        if session_id:sql+=' WHERE session_id=?';args.append(session_id)
        sql+=' ORDER BY stamp_utc DESC LIMIT ?';args.append(max(1,min(limit,100)))
        with self.lock,self._connect() as db:rows=db.execute(sql,args).fetchall()
        return [dict(id=r[0],session_id=r[1],filename=r[2],sha256=r[3],utc=r[4],
                     summary=json.loads(r[5]),source='imported') for r in rows]
