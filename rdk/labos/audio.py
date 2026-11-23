"""Short local PCM WAV validation and conversion for Whisper.cpp.
Pure Python 3.10+ (does not depend on removed audioop module).
"""
from __future__ import annotations
import io,struct,wave

MAX_AUDIO_BYTES=4*1024*1024

def normalize_wav(raw:bytes)->tuple[bytes,float]:
    if not raw or len(raw)>MAX_AUDIO_BYTES: raise ValueError('WAV 必须非空且小于 4MiB')
    try:
        with wave.open(io.BytesIO(raw),'rb') as w:
            channels=w.getnchannels();width=w.getsampwidth();rate=w.getframerate();frames=w.getnframes()
            if (w.getcomptype()!='NONE' or channels not in (1,2) or width!=2 or not 8000<=rate<=48000 or frames>rate*12):
                raise ValueError('仅接受 8–48kHz、16bit、单/双声道、最多12秒的 PCM WAV')
            pcm=w.readframes(frames)
    except (EOFError,wave.Error) as exc:raise ValueError('无法读取 WAV 文件') from exc
    if not pcm:raise ValueError('音频为空')
    if len(pcm)%(2*channels):raise ValueError('PCM 数据长度不完整')
    n=len(pcm)//(2*channels)
    if channels==1:
        source=list(struct.unpack('<%dh'%n,pcm))
    else:
        seq=struct.unpack('<%dh'%(n*2),pcm)
        source=[(seq[i*2]+seq[i*2+1])//2 for i in range(n)]
    if rate==16000:result=source
    else:
        length=max(1,len(source)*16000//rate)
        result=[]
        for i in range(length):
            x=i*rate/16000;j=int(x)
            if j>=len(source)-1:result.append(int(source[-1]));continue
            f=x-j
            result.append(int(source[j]*(1-f)+source[j+1]*f))
    out=struct.pack('<%dh'%len(result),*result)
    return out,len(out)/32000.0

def make_wav(pcm:bytes)->bytes:
    b=io.BytesIO()
    with wave.open(b,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(pcm)
    return b.getvalue()
