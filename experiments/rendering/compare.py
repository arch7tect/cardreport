from pathlib import Path
import io, json, hashlib, time, argparse
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
from weasyprint import HTML
from pypdf import PdfReader
from playwright.sync_api import sync_playwright
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=ROOT/"local/rendering-comparison/p0")
OUT=parser.parse_args().output
OUT.mkdir(parents=True, exist_ok=False)
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "DejaVu Sans"
fig, ax = plt.subplots(figsize=(5, 2.5))
ax.barh(["Attempted", "Answered", "Обещания"], [21, 5, 2], color="#20a6c4")
fig.tight_layout()
s = io.StringIO(); fig.savefig(s, format="svg"); plt.close(fig)
svg=s.getvalue();svg=svg[svg.index("<svg"):]
style = """@page {size:A4 landscape;margin:10mm} body{font:12px sans-serif}
.row{display:flex;gap:4mm}.card{border:1px solid #ddd;padding:4mm;width:80mm;height:70mm}
.probe{width:25mm;height:10mm;border:1px solid red} table{width:100%;border-collapse:collapse}
th,td{padding:3mm;border-bottom:1px solid #ddd} tr{break-inside:avoid} thead{display:table-header-group}"""
normal = f"<div class=row><div class=card>Clients: 21<br>Answered: 5<br>Promises: 2</div><div class=card>{svg}</div></div>"
overflow = "<div id=overflow class=probe>" + "Long wrapped label Пример "*30 + "</div>"
flow = "<table><thead><tr><th>Identity</th><th>Value</th></tr></thead><tbody>"+"".join(f"<tr><td>ROW-{i:03d}</td><td>Example row</td></tr>" for i in range(120))+"</tbody></table>"
results={}
for name,body in [("normal",normal),("overflow",overflow),("flow",flow)]:
    html=f"<!doctype html><html><head><meta charset=utf-8><style>{style}</style></head><body>{body}</body></html>"
    (OUT/f"b-{name}.html").write_text(html)
    t=time.monotonic(); doc=HTML(string=html).render(); doc.write_pdf(OUT/f"b-{name}.pdf")
    reader=PdfReader(OUT/f"b-{name}.pdf")
    results[f"b-{name}"]={"pages":len(reader.pages),"seconds":round(time.monotonic()-t,3),"anchors":[p.anchors for p in doc.pages],"text":''.join(p.extract_text() for p in reader.pages)}
with sync_playwright() as pw:
    browser=pw.chromium.launch()
    for name in ["normal","overflow","flow"]:
        page=browser.new_page(viewport={"width":1047,"height":718})
        html=(OUT/f"b-{name}.html").read_text()
        if name=="normal":
            chart=go.Figure(go.Bar(x=[21,5,2],y=["Attempted","Answered","Обещания"],orientation="h"))
            chart.update_layout(width=300,height=240,font={"family":"DejaVu Sans"},margin={"l":85,"r":20,"t":20,"b":30})
            html=html.replace(svg,chart.to_html(full_html=False,include_plotlyjs=True,config={"staticPlot":True}))
        page.emulate_media(media="print");page.set_content(html)
        if name=="normal":page.wait_for_function("document.querySelector('.main-svg') !== null")
        page.evaluate("document.fonts.ready")
        over=page.locator(".probe").evaluate_all("els=>els.map(e=>({height:e.clientHeight,contentHeight:e.scrollHeight,width:e.clientWidth,contentWidth:e.scrollWidth}))")
        page.pdf(path=str(OUT/f"a-{name}.pdf"),format="A4",landscape=True,print_background=True)
        reader=PdfReader(OUT/f"a-{name}.pdf")
        results[f"a-{name}"]={"pages":len(reader.pages),"overflow":over,"text":''.join(p.extract_text() for p in reader.pages)}
        page.close()
    browser.close()
(OUT/"results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
(OUT/"manifest.json").write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in OUT.iterdir() if f.name!="manifest.json"},indent=2))
for k,v in results.items():print(k,{a:b for a,b in v.items() if a!="text"})
