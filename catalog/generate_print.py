#!/usr/bin/env python3
# Premium A4 RTL Arabic catalog — TWO companies (إيلاف + قوين), deterministic pagination.
import json, os, html

ROOT = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(ROOT, "data/products.json"), encoding="utf-8"))
companies = d["companies"]
catmeta = {c["key"]: c for c in d["categories"]}
catorder = [c["key"] for c in d["categories"]]
prods = d["products"]

AR = "٠١٢٣٤٥٦٧٨٩"
def ar(n): return str(n).translate(str.maketrans("0123456789", AR))
def esc(s): return html.escape(s or "")
def img_src(p):
    rel = p.get("img") or ""
    return rel if rel and os.path.exists(os.path.join(ROOT, rel)) else None

FIRST_PER_PAGE = 6
CONT_PER_PAGE  = 9
SAR = '<svg class="sar" viewBox="0 0 1124.14 1256.39"><path d="M699.62,1113.02h0c-20.06,44.48-33.32,92.75-38.4,143.37l424.51-90.24c20.06-44.47,33.31-92.75,38.4-143.37l-424.51,90.24Z"/><path d="M1085.73,895.8c20.06-44.47,33.32-92.75,38.4-143.37l-330.68,70.33v-135.2l292.27-62.11c20.06-44.47,33.32-92.75,38.4-143.37l-330.68,70.27V66.13c-50.67,28.45-95.67,66.32-132.25,110.99v403.35l-132.25,28.11V0c-50.67,28.44-95.67,66.32-132.25,110.99v525.69l-295.91,62.88c-20.06,44.47-33.33,92.75-38.42,143.37l334.33-71.05v170.26l-358.3,76.14c-20.06,44.47-33.32,92.75-38.4,143.37l375.04-79.7c30.53-6.35,56.77-24.4,73.83-49.24l68.78-101.97v-.02c7.14-10.55,11.3-23.27,11.3-36.97v-149.98l132.25-28.11v270.4l424.53-90.28Z"/></svg>'

def card(p):
    src = img_src(p)
    media = f'<img src="{src}" alt="{esc(p["name"])}"/>' if src else '<div class="noimg">بدون صورة</div>'
    sku = f'<span class="sku">{esc(p["sku"])}</span>' if p.get("sku") else "<span></span>"
    pr = esc(str(p.get("price") or "")).translate(str.maketrans("0123456789", AR))
    price = f'<span class="price"><b>{pr}</b>{SAR}</span>' if pr else f'<span class="price">{SAR}<span class="pdash">____</span></span>'
    return (f'<article class="card"><div class="media"><span class="idx">{ar(p["idx"])}</span>{media}</div>'
            f'<div class="info"><h3 class="name">{esc(p["name"])}</h3>'
            f'<div class="foot">{sku}{price}</div></div></article>')

def banner(co_key, cat_key, count):
    c = catmeta[cat_key]
    return (f'<div class="sec-banner {co_key}"><div class="sec-titles"><h2 class="sec-ar">{esc(c["ar"])}</h2>'
            f'<div class="sec-en">{esc(c["en"])}</div></div>'
            f'<div class="sec-count">{ar(count)}<span>صنف</span></div></div>')

# group products: company -> category -> [products]
grp = {co["key"]: {k: [] for k in catorder} for co in companies}
for p in prods:
    grp.setdefault(p["company"], {k: [] for k in catorder})[p.get("cat","misc")].append(p)

# ---- pass 1: build page list (records anchors) ----
PAGE_OFFSET = 2  # cover + toc
content = []     # {kind:'company'|'cards', ...}
anchors = {}     # ('co',key) or ('sec',co,key) -> content index
for co in companies:
    co_items = [k for k in catorder if grp[co["key"]][k]]
    if not co_items: continue
    anchors[("co", co["key"])] = len(content)
    content.append({"kind":"company","co":co})
    for k in co_items:
        items = grp[co["key"]][k]
        anchors[("sec", co["key"], k)] = len(content)
        content.append({"kind":"cards","co":co["key"],"cat":k,"banner":(k,len(items)),"cards":items[:FIRST_PER_PAGE]})
        rest = items[FIRST_PER_PAGE:]
        for i in range(0,len(rest),CONT_PER_PAGE):
            content.append({"kind":"cards","co":co["key"],"cat":k,"banner":None,"cards":rest[i:i+CONT_PER_PAGE]})

TOTAL = PAGE_OFFSET + len(content)
def pageno(anchor): return PAGE_OFFSET + anchors[anchor] + 1

co_ar = {c["key"]: c["ar"] for c in companies}

def header(co_key, sec_ar=""):
    coname = co_ar.get(co_key,"")
    return (f'<div class="phead"><div class="ph-brand"><img src="assets/brand/logo-trans.png"/>'
            f'<span>{esc(coname)}</span></div><div class="ph-sec">{esc(sec_ar)}</div></div>')
def footer(n):
    return f'<div class="pfoot"><span>كتالوج المنتجات ٢٠٢٦ / ٢٠٢٧</span><span class="pn">{ar(n)} / {ar(TOTAL)}</span></div>'

out=[]
# cover
out.append(f'''<section class="page cover">
  <div class="cover-inner"><img class="logo" src="assets/brand/logo-white.png"/>
    <div class="kicker">دليل المنتجات الرسمي</div><h1>كتالوج المنتجات</h1><div class="rule"></div>
    <div class="sub">شركة ايلاف الشرقية التجارية &amp; شركة قوين<br/>أدوات منزلية ومستلزمات متنوعة بجودة عالية</div>
    <div class="season">موسم ٢٠٢٦ / ٢٠٢٧</div></div>
  <div class="cover-foot">ELAF AL SHARQIAH TRADING COMPANY · QUEEN</div></section>''')

# toc grouped by company
toc=""
for co in companies:
    if ("co",co["key"]) not in anchors: continue
    toc+=f'<div class="toc-co"><span class="toc-co-ar">{esc(co["ar"])}</span><span class="toc-co-pg">{ar(pageno(("co",co["key"])))}</span></div>'
    for k in catorder:
        if ("sec",co["key"],k) in anchors:
            cnt=len(grp[co["key"]][k])
            toc+=(f'<a class="toc-row" href="#sec-{co["key"]}-{k}"><span class="toc-name">{esc(catmeta[k]["ar"])}</span>'
                  f'<span class="toc-en">{esc(catmeta[k]["en"])}</span><span class="toc-dots"></span>'
                  f'<span class="toc-count">{ar(cnt)}</span><span class="toc-pg">{ar(pageno(("sec",co["key"],k)))}</span></a>')
out.append(f'''<section class="page"><div class="phead"></div>
  <div class="pbody toc"><h2 class="toc-title">المحتويات</h2>
  <div class="toc-sub">{ar(d["counts"]["elaf"])} صنف ايلاف · {ar(d["counts"]["queen"])} صنف قوين</div>{toc}</div>{footer(2)}</section>''')

# content pages
for i,pg in enumerate(content):
    n=PAGE_OFFSET+i+1
    if pg["kind"]=="company":
        co=pg["co"]
        out.append(f'''<section class="page co-divider {co["key"]}" id="co-{co["key"]}">
          <div class="cd-inner"><div class="cd-kicker">القسم</div>
          <h2 class="cd-ar">{esc(co["ar"])}</h2><div class="cd-en">{esc(co["en"])}</div>
          <div class="cd-rule"></div><div class="cd-count">{ar(d["counts"][co["key"]])} صنف</div></div></section>''')
    else:
        anchor=f' id="sec-{pg["co"]}-{pg["cat"]}"' if pg["banner"] else ""
        sec_ar=catmeta[pg["cat"]]["ar"]
        bn = banner(pg["co"],pg["cat"],pg["banner"][1]) if pg["banner"] else ""
        body = bn + '<div class="grid">'+"".join(card(p) for p in pg["cards"])+'</div>'
        out.append(f'<section class="page"{anchor}>{header(pg["co"],sec_ar)}<div class="pbody">{body}</div>{footer(n)}</section>')

CSS='''
:root{--brand:#14605f;--brand2:#1d8480;--dark:#0c3e3d;--ink:#23262b;--muted:#6b7280;--line:#e2e6e5;--soft:#e9f2f1;
 --queen:#7a3e8f;--queen2:#9d5cb0;--queen-dark:#4d245c;}
*{box-sizing:border-box}
@page{size:A4;margin:0}
html{font-family:'Tajawal',sans-serif;color:var(--ink)}
body{margin:0;background:#d9dcdb;-webkit-print-color-adjust:exact;print-color-adjust:exact}
h1,h2,h3{font-family:'Cairo';margin:0;line-height:1.2}
img{display:block}
.sar{width:.82em;height:.82em;fill:currentColor;display:inline-block;vertical-align:-.06em}
.page{position:relative;width:210mm;height:297mm;background:#fff;overflow:hidden;margin:0 auto;page-break-after:always;break-after:page;display:flex;flex-direction:column;padding:10mm 11mm 8mm}
.page:last-child{break-after:auto}
@media screen{.page{margin:8mm auto;box-shadow:0 6px 30px rgba(0,0,0,.18)}}
.phead{display:flex;align-items:center;justify-content:space-between;height:9mm;border-bottom:1px solid var(--line);padding-bottom:2mm;margin-bottom:4mm;flex:0 0 auto}
.ph-brand{display:flex;align-items:center;gap:6px;font-family:'Cairo';font-weight:800;font-size:9.5pt;color:var(--brand)}
.ph-brand img{height:6mm}
.ph-sec{font-family:'Tajawal';font-weight:500;font-size:9pt;color:#9aa1a8}
.pfoot{display:flex;align-items:center;justify-content:space-between;height:6mm;border-top:1px solid var(--line);padding-top:2mm;margin-top:3mm;font-family:'Tajawal';font-size:8.5pt;color:#9aa1a8;flex:0 0 auto}
.pfoot .pn{font-family:'Cairo';font-weight:700;color:var(--brand)}
.pbody{flex:1 1 auto;min-height:0;display:flex;flex-direction:column}
/* cover */
.cover{padding:0;color:#fff;justify-content:center;align-items:center;text-align:center;background:radial-gradient(700px 430px at 80% 6%,rgba(29,132,128,.6),transparent 60%),linear-gradient(150deg,#0c3e3d,#14605f 55%,#0f514f)}
.cover-inner{display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1}
.cover .logo{width:120mm;margin-bottom:16mm}
.cover .kicker{font-family:'Tajawal';font-weight:500;letter-spacing:.45em;font-size:11pt;color:#bfe7e3;margin-bottom:6mm;padding-inline-start:.45em}
.cover h1{font-size:44pt;font-weight:900}
.cover .rule{width:58mm;height:2px;background:linear-gradient(90deg,transparent,#9fe0db,transparent);margin:7mm 0}
.cover .sub{font-family:'Tajawal';font-weight:300;font-size:13pt;color:#d6ece9;line-height:1.8}
.cover .season{margin-top:13mm;border:1px solid rgba(255,255,255,.32);border-radius:999px;padding:7px 28px;font-family:'Cairo';font-weight:700;font-size:13pt}
.cover-foot{padding-bottom:16mm;font-family:'Tajawal';font-size:9pt;letter-spacing:.2em;color:#9fe0db}
/* company divider */
.co-divider{padding:0;color:#fff;justify-content:center;align-items:center;text-align:center;background:linear-gradient(150deg,#0c3e3d,#14605f 60%,#0f514f)}
.co-divider.queen{background:linear-gradient(150deg,var(--queen-dark),var(--queen) 60%,#5e2e6e)}
.cd-inner{display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1}
.cd-kicker{font-family:'Tajawal';letter-spacing:.4em;font-size:11pt;color:rgba(255,255,255,.7);margin-bottom:5mm}
.cd-ar{font-size:38pt;font-weight:900}
.cd-en{font-family:'Tajawal';letter-spacing:.2em;font-size:11pt;color:rgba(255,255,255,.8);margin-top:3mm}
.cd-rule{width:50mm;height:2px;background:rgba(255,255,255,.5);margin:8mm 0}
.cd-count{font-family:'Cairo';font-weight:700;font-size:15pt;border:1px solid rgba(255,255,255,.35);border-radius:999px;padding:6px 24px}
/* toc */
.toc{padding-top:3mm}
.toc-title{font-size:26pt;color:var(--brand);margin-bottom:1mm}
.toc-sub{font-family:'Tajawal';color:var(--muted);font-size:10.5pt;margin-bottom:6mm}
.toc-co{display:flex;justify-content:space-between;align-items:center;margin:5mm 0 2mm;padding-bottom:1.5mm;border-bottom:2px solid var(--brand)}
.toc-co-ar{font-family:'Cairo';font-weight:800;font-size:14pt;color:var(--brand)}
.toc-co-pg{font-family:'Cairo';font-weight:800;color:var(--brand);font-size:12pt}
.toc-row{display:flex;align-items:center;gap:9px;padding:2.4mm 2mm;border-bottom:1px dotted #d3d9d7;text-decoration:none;color:var(--ink)}
.toc-name{font-family:'Cairo';font-weight:700;font-size:12pt;white-space:nowrap}
.toc-en{font-family:'Tajawal';font-size:7.5pt;color:#aab0b0;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}
.toc-dots{flex:1;border-bottom:1px dotted #c4cccb;margin:0 4px;transform:translateY(-3px)}
.toc-count{font-family:'Tajawal';font-size:9pt;color:var(--muted);white-space:nowrap}
.toc-pg{font-family:'Cairo';font-weight:800;color:var(--brand);font-size:12pt;min-width:8mm;text-align:center}
/* section banner */
.sec-banner{display:flex;align-items:center;justify-content:space-between;gap:12px;flex:0 0 auto;background:linear-gradient(120deg,var(--brand),var(--brand2));color:#fff;border-radius:9px;padding:5mm 7mm;margin-bottom:5mm}
.sec-banner.queen{background:linear-gradient(120deg,var(--queen),var(--queen2))}
.sec-ar{font-size:19pt;font-weight:800}
.sec-en{font-family:'Tajawal';font-size:8.5pt;letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.85);margin-top:2px}
.sec-count{font-family:'Cairo';font-weight:900;font-size:23pt;line-height:1;text-align:center}
.sec-count span{display:block;font-family:'Tajawal';font-weight:400;font-size:8pt;letter-spacing:.08em;color:rgba(255,255,255,.85)}
/* grid + cards */
.grid{display:grid;grid-template-columns:repeat(3,1fr);grid-auto-rows:76mm;gap:5mm;flex:0 0 auto;align-content:start}
.card{border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#fff;display:flex;flex-direction:column}
.media{position:relative;flex:1 1 auto;min-height:0;background:#fbfbfb;display:flex;align-items:center;justify-content:center;padding:3mm;border-bottom:1px solid #eef1f0}
.media img{max-width:100%;max-height:100%;object-fit:contain}
.idx{position:absolute;top:2mm;inset-inline-start:2mm;background:var(--brand);color:#fff;font-family:'Cairo';font-weight:700;font-size:7.5pt;padding:1px 6px;border-radius:5px}
.noimg{color:#bcc3c3;font-family:'Tajawal';font-size:9pt}
.info{padding:2.6mm 3mm 3mm;display:flex;flex-direction:column;gap:2.2mm;flex:0 0 auto}
.name{font-family:'Tajawal';font-weight:700;font-size:9pt;line-height:1.4;color:#23262b;height:2.8em;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.foot{display:flex;align-items:center;justify-content:space-between;gap:5px;padding-top:2.2mm;border-top:1px dashed var(--line)}
.sku{font-family:'Tajawal';font-weight:600;font-size:7.5pt;color:var(--brand);background:var(--soft);padding:2px 6px;border-radius:5px;direction:ltr}
.price{display:inline-flex;align-items:center;gap:3px;color:var(--brand);font-size:9pt;white-space:nowrap}
.price b{font-family:'Cairo';font-weight:800;font-size:11.5pt;line-height:1}
.pdash{color:#cbd2d1;letter-spacing:.5px;font-size:8pt}
'''
doc=f'''<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"/>
<title>كتالوج المنتجات | ايلاف الشرقية وقوين</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&family=Tajawal:wght@300;400;500;700&display=swap" rel="stylesheet"/>
<style>{CSS}</style></head><body>{''.join(out)}</body></html>'''
open(os.path.join(ROOT,"print.html"),"w",encoding="utf-8").write(doc)
print(f"wrote print.html  pages={TOTAL}  products={len(prods)} (elaf {d['counts']['elaf']} + queen {d['counts']['queen']})")
