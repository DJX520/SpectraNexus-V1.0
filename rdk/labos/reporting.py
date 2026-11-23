"""Printable HTML report, with all user-origin fields escaped."""
import html
import json

def render_report(rep,sid=None):
    h=lambda value:html.escape(str(value),quote=True)
    titles=['UTC','类型','来源','批次','数量']
    header='<tr>'+''.join('<th>'+h(x)+'</th>' for x in titles)+'</tr>'
    rows=''.join('<tr>'+''.join('<td>'+h(v)+'</td>' for v in
                (r['utc'],r['kind'],r['source'],r['id'],r['count']))+'</tr>'
                for r in rep['runs'])
    summary=h(json.dumps(rep['summary'],ensure_ascii=False,indent=2))
    imports=h(json.dumps(rep.get('imports',[]),ensure_ascii=False,indent=2))
    flags=h(json.dumps(rep['anomalies'],ensure_ascii=False,indent=2))
    return ('''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>LabOS V5 Experiment Report</title>
<style>body{font:15px/1.65 sans-serif;margin:45px auto;max-width:900px;color:#24323a}
header{border-bottom:3px solid #087e72;padding-bottom:15px}h1{color:#0b554f}table{border-collapse:collapse;width:100%}
th,td{padding:7px 10px;border:1px solid #cad9d9;text-align:left;word-break:break-all}
pre{white-space:pre-wrap;word-break:break-word;background:#f1f5f5;padding:12px}
@media print{button{display:none}}</style></head><body>'''
+'<header><h1>LabOS V5 · 实验摘要</h1><p>浏览器 Ctrl+P 可保存为 PDF</p></header>'
+f'<p>会话：{h(sid or "全部")} / 生成：{h(rep["generated_utc"])}</p>'
+'<h2>统计概况</h2><pre>'+summary+'</pre>'
+'<h2>测量批次</h2><table>'+header+rows+'</table>'
+'<h2>RF 离群点</h2><pre>'+flags+'</pre>'
+'<h2>上传数据集（来源 imported）</h2><pre>'+imports+'</pre>'
+'<p>每条测量数据均带来源标记。统计离群点不等于攻击归因，且不代表仪器已校准。</p></body></html>')
