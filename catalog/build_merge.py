#!/usr/bin/env python3
# Merge Elaf (print-catalog) products with Queen (Excel) products into one catalog dataset.
import json, os, re, unicodedata, openpyxl
from xml.etree import ElementTree as ET
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
QXLSX = os.path.join(PROJ, "منتجات شركه قوين 2026-2027.xlsx")
QEXT = "/tmp/elaf_extract/queen"
QMEDIA = os.path.join(QEXT, "xl/media")
QOUT = os.path.join(ROOT, "assets/queen"); os.makedirs(QOUT, exist_ok=True)
NS={'xdr':'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing','a':'http://schemas.openxmlformats.org/drawingml/2006/main','rel':'http://schemas.openxmlformats.org/package/2006/relationships'}

def nname(s):
    s=unicodedata.normalize('NFKC',s or ''); s=re.sub(r'[ًٌٍَُِّْٰ]','',s)
    s=s.replace('إ','ا').replace('أ','ا').replace('آ','ا').replace('ى','ي').replace('ة','ه')
    return re.sub(r'\s+',' ',s).strip()
def nsku(s): return re.sub(r'[^A-Z0-9]','',(s or '').upper())

# ---- category rules (shared) ----
RULES=[
 ("swim","مستلزمات السباحة","Swimming",["سباحه","سباح","عوامه","طوق"]),
 ("toys","الألعاب","Toys",["لعبه","العاب","لعبة","مسدس","دباب","عروسه","بازل","مكعبات"]),
 ("shoes","الأحذية","Footwear",["احذية","حذاء","شبشب","نعال"]),
 ("sports","الرياضة والكرات","Sports & Balls",["كرة","كره"]),
 ("paper","الورقيات والمناديل","Paper & Tissues",["ورق","مناديل","منديل","رول","ورقي","ورقيه","ورقية","شييت","سحبة","قلاية هوائية","حفاض"]),
 ("clean","أدوات التنظيف","Cleaning Tools",["مكنسة","شطاف","شطافة","جاروف","مساحة","ممسحة","عربة","مناشف","فرشاة","اسفنج","ليفة","دلو","سطل","نظاف"]),
 ("vase","الفازات والديكور","Vases & Decor",["فاز","مزهري","تحفة","تحف","ثقالات","ثقاله","شمعة","شمعدان","اطار","برواز"]),
 ("store","الحفظ والتخزين","Storage & Organizers",["برطم","حافظ","منظم","علبة هداياء","علبة هدايا","سكرية","حفظ","علب حفظ","صندوق","سله","سلة","رف","دولاب"]),
 ("bottle","القوارير والمطارات والزيوت","Bottles, Flasks & Oil",["قارورة","قاروره","قله","قلة","قلل","مطارة","مطاره","مطارات","مزيت","مزايت","مزبتة","مزيته","بهارات","ترمس","زجاجة ماء","كوب ماء"]),
 ("cook","الطهي وأدوات المطبخ","Cookware & Utensils",["قدور","قدر","حلة","قلاية","عصارة","خباط","هراسة","قطاعة","ملاعق","ملعقة","مشخال","صواني","صينية","سكاكين","سكين","شوي","عيدان","مقلاة","غلاية","شوكة","سكين","مبشرة","لوح تقطيع","فتاحة","كبه"]),
 ("pet","مستلزمات الحيوانات","Pet Supplies",["قطط","قطه","كلاب","كلب","حيوان","طيور","عصافير"]),
 ("cup","الأكواب والكاسات","Cups & Mugs",["اكواب","كاسات","كاسا","كوب","بيالات","مج","فناجين","فنجان","استكان"]),
 ("table","أدوات المائدة والتقديم","Tableware & Serving",["صحن","صحون","زبدي","زبيدة","طفرية","سيراميك","سيرميك","سراميك","طقم","اطقم","اباريق","ابريق","ابريق","حوض","مزهر","تقديم","سفرة","طبق","صحفة"]),
]
MISC=("misc","منتجات متنوعة","Miscellaneous")
catmeta={k:(a,e) for k,a,e,_ in RULES}; catmeta["misc"]=(MISC[1],MISC[2])
CATORDER=[k for k,_,_,_ in RULES]+["misc"]
def categorize(name):
    for k,a,e,kws in RULES:
        for kw in kws:
            if kw in name: return k
    return "misc"

# ---- load existing Elaf (print) products ----
cur=json.load(open(os.path.join(ROOT,"data/products.json"),encoding="utf-8"))
elaf=[]
for p in cur["products"]:
    p=dict(p); p["company"]="elaf"; elaf.append(p)

# ---- print maps for Queen photo matching ----
pp=json.load(open("/tmp/print_products.json"))
def fmtprice(v):
    try: v=float(v)
    except: return ""
    return str(int(v)) if v==int(v) else f"{v:.2f}".rstrip('0').rstrip('.')
psku={nsku(p['sku']):p for p in pp if p['sku']}
pname={}
for p in pp: pname.setdefault(nname(p['name']),p)
# map a print product to its already-saved img path (assets/print/pIDX.jpg)
def print_img(pp_item): return pp_item.get("img","")

# ---- queen image anchors ----
rels={}
for rel in ET.parse(os.path.join(QEXT,'xl/drawings/_rels/drawing1.xml.rels')).getroot().findall('rel:Relationship',NS):
    rels[rel.get('Id')]=rel.get('Target').split('/')[-1]
dx=ET.parse(os.path.join(QEXT,'xl/drawings/drawing1.xml')).getroot()
imgmap={}
for a in dx.findall('xdr:oneCellAnchor',NS)+dx.findall('xdr:twoCellAnchor',NS):
    row0=int(a.find('xdr:from/xdr:row',NS).text)
    blip=a.find('.//a:blip',NS)
    if blip is None: continue
    rid=blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
    if rels.get(rid): imgmap[row0+1]=rels[rid]

def save_thumb(srcmedia, dst):
    try:
        img=Image.open(os.path.join(QMEDIA,srcmedia)).convert("RGB")
        w,h=img.size
        if max(w,h)<240:
            s=520/max(w,h); img=img.resize((round(w*s),round(h*s)),Image.LANCZOS)
            img=img.filter(ImageFilter.UnsharpMask(radius=1.4,percent=110,threshold=2))
        elif max(w,h)>1000:
            s=1000/max(w,h); img=img.resize((round(w*s),round(h*s)),Image.LANCZOS)
        img.save(dst,"JPEG",quality=86); return True
    except Exception: return False

wb=openpyxl.load_workbook(QXLSX,data_only=True); ws=wb.active
queen=[]; n_sku=n_name=n_thumb=n_no=0
for r in range(2,ws.max_row+1):
    sku=ws.cell(r,2).value; name=ws.cell(r,5).value; unit=ws.cell(r,6).value
    if not sku and not name: continue
    sku=str(sku).strip() if sku else ""; name=str(name).strip() if name else ""
    unit=str(unit).strip() if unit else ""
    img=""; price=""
    m=psku.get(nsku(sku)) or pname.get(nname(name))
    if m:
        img=print_img(m); price=fmtprice(m.get("price"))
        if nsku(sku) in psku: n_sku+=1
        else: n_name+=1
    elif r in imgmap:
        fn=f"q{r}.jpg"
        if save_thumb(imgmap[r], os.path.join(QOUT,fn)): img=f"assets/queen/{fn}"; n_thumb+=1
        else: n_no+=1
    else:
        n_no+=1
    idx=len(queen)+1
    queen.append({"idx":idx,"company":"queen","sku":sku,"name":unicodedata.normalize('NFKC',name),
                  "price":price,"qty":"","unit":unit,"img":img,"cat":categorize(nname(name))})

print(f"Queen: {len(queen)}  print-SKU photo={n_sku}  print-name photo={n_name}  thumbnail={n_thumb}  no-photo={n_no}")

# ---- merge + categories metadata ----
allp=elaf+queen
# ensure every elaf product has company + ensure cat keys exist
cats=[{"key":k,"ar":catmeta[k][0],"en":catmeta[k][1]} for k in CATORDER]
companies=[{"key":"elaf","ar":"شركة ايلاف الشرقية التجارية","en":"ELAF AL SHARQIAH"},
           {"key":"queen","ar":"شركة قوين","en":"QUEEN"}]
from collections import Counter
data={"companies":companies,"categories":cats,
      "count":len(allp),
      "counts":{"elaf":len(elaf),"queen":len(queen)},
      "products":allp}
json.dump(data,open(os.path.join(ROOT,"data/products.json"),"w"),ensure_ascii=False,indent=1)
with open(os.path.join(ROOT,"data/products.js"),"w") as f:
    f.write("window.CATALOG=");json.dump(data,f,ensure_ascii=False);f.write(";")
print(f"TOTAL products: {len(allp)} (elaf {len(elaf)} + queen {len(queen)})")
print("queen with image:",sum(1 for q in queen if q['img']),"  queen with price:",sum(1 for q in queen if q['price']))
