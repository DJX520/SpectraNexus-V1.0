"""Checked, line-oriented LAB5 protocol. Never evaluates payload contents."""
from __future__ import annotations
import json
import re
from dataclasses import dataclass

LINE_LIMIT = 2048
ALLOWED_TYPES = {'begin','item','end','error'}
COMMANDS = {'HELLO','INFO','WIFI_SCAN','BLE_SCAN','RF_SAMPLE','RF_SAMPLE_315','RF_SAMPLE_868','RF_SAMPLE_915','NFC_SCAN'}

class ProtocolError(ValueError):
    pass

@dataclass(frozen=True)
class Frame:
    request_id: int
    kind: str
    data: dict

def encode_command(request_id: int, command: str) -> bytes:
    if not (1 <= request_id <= 99999999) or command not in COMMANDS:
        raise ProtocolError('无效请求编号或不允许的命令')
    return f'L5|{request_id}|{command}\n'.encode('ascii')

def parse_frame(line: bytes | str) -> Frame | None:
    if isinstance(line,bytes):
        if len(line)>LINE_LIMIT: raise ProtocolError('响应帧过长')
        try: line=line.decode('utf-8').strip()
        except UnicodeDecodeError as exc:raise ProtocolError('响应帧 UTF-8 非法') from exc
    if len(line)>LINE_LIMIT: raise ProtocolError('响应帧过长')
    if not line.startswith('LAB5|'):return None
    parts=line.split('|',3)
    if len(parts)!=4 or not re.fullmatch(r'[0-9]{1,8}',parts[1]):
        raise ProtocolError('帧头格式错误')
    rid=int(parts[1]);kind=parts[2]
    if kind not in ALLOWED_TYPES:raise ProtocolError('未知数据帧类型')
    try: payload=json.loads(parts[3])
    except json.JSONDecodeError as exc:raise ProtocolError('JSON 损坏') from exc
    if not isinstance(payload,dict):raise ProtocolError('负载必须是对象')
    return Frame(rid,kind,payload)
