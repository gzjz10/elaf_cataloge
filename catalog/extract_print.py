#!/usr/bin/env python3
# Extract name + SKU + price + photo per product from the designed print catalog PDF.
import fitz, re, os, io, json
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(os.path.dirname(ROOT), "كتالوج إيلاف طباعة 2026-1.pdf")
OUT_IMG = os.path.join(ROOT, "assets/print"); os.makedirs(OUT_IMG, exist_ok=True)

doc = fitz.open(PDF)
ARRX = re.compile(r'[؀-ۿ]')
def is_code(t): return bool(re.fullmatch(r'[A-Za-z]{1,6}-?\d{2,}[A-Za-z0-9\-]*', t) or re.fullmatch(r'\d{4,}', t) or re.fullmatch(r'\d+[Xx]\d+([Xx]\d+)?', t))
def is_qp(t): return bool(re.fullmatch(r'\d{1,3}(\.\d{1,2})?', t))

def extract_photo(xref, dst):
    try:
        info = doc.extract_image(xref)
        img = Image.open(io.BytesIO(info["image"]))
        if img.mode in ("CMYK","P","RGBA","LA"): img = img.convert("RGB")
        elif img.mode != "RGB": img = img.convert("RGB")
        w,h = img.size
        if max(w,h) > 1000:
            s = 1000/max(w,h); img = img.resize((round(w*s),round(h*s)), Image.LANCZOS)
        img.save(dst, "JPEG", quality=88)
        return True
    except Exception as e:
        return False

products = []
pno_seen = 0
for pi in range(len(doc)):
    pg = doc[pi]; W,H = pg.rect.width, pg.rect.height
    # candidate product images: reasonable size, top within page, not full-width background
    imgs = []
    for im in pg.get_image_info(xrefs=True):
        b = im['bbox']; w=b[2]-b[0]; h=b[3]-b[1]
        if im['xref']<=0: continue
        if w<90 or h<55: continue
        if w>W*0.8: continue            # skip background/banner spanning images
        if b[1]<-30 or b[3]>H+30: continue  # skip bleed/duplicates way off page
        imgs.append((im['xref'], b, w*h))
    # quadrant assign, keep largest area per quadrant
    quads = {}
    for xref,b,area in imgs:
        cx=(b[0]+b[2])/2; cy=(b[1]+b[3])/2
        q=(0 if cx<W/2 else 1, 0 if cy<H/2 else 1)
        if q not in quads or area>quads[q][2]:
            quads[q]=(xref,b,area)
    if not quads: continue
    # text spans
    spans=[]
    for blk in pg.get_text("dict")["blocks"]:
        for ln in blk.get("lines",[]):
            for sp in ln["spans"]:
                t=sp["text"].strip()
                if not t: continue
                cx=(sp["bbox"][0]+sp["bbox"][2])/2; cy=(sp["bbox"][1]+sp["bbox"][3])/2
                # exclude centered page number at bottom
                if is_qp(t) and W*0.42<cx<W*0.58 and cy>H*0.86 and sp['size']>=11: continue
                spans.append((cx,cy,sp["bbox"][0],t,sp['size']))
    for q,(xref,b,area) in quads.items():
        bx0,by0,bx1,by1=b
        band=[s for s in spans if (bx0-28)<=s[0]<=(bx1+55) and by0<=s[1]<=(by1+56)]
        names=sorted([(y,-x0,t) for (cx,y,x0,t,sz) in band if ARRX.search(t)])
        name=" ".join(t for _,_,t in names).strip()
        codes=[(cx,t) for (cx,cy,x0,t,sz) in band if not ARRX.search(t) and is_code(t)]
        nums=sorted([(cx,t) for (cx,cy,x0,t,sz) in band if not ARRX.search(t) and is_qp(t) and not is_code(t)])
        qty = nums[0][1] if len(nums)>=2 else None
        price = nums[-1][1] if nums else None
        if not name or price is None:   # skip non-product cells (covers, dividers)
            continue
        idx=len(products)+1
        fn=f"p{idx}.jpg"
        ok=extract_photo(xref, os.path.join(OUT_IMG, fn))
        products.append({"idx":idx,"page":pi+1,"name":name,"sku":(codes[0][1] if codes else ""),
                         "qty":qty,"price":price,"img":(f"assets/print/{fn}" if ok else "")})

json.dump(products, open("/tmp/print_products.json","w"), ensure_ascii=False, indent=1)
print(f"pages={len(doc)}  products extracted={len(products)}  with photo={sum(1 for p in products if p['img'])}")
# price sanity
pr=[float(p['price']) for p in products if p['price']]
print(f"price range: {min(pr)} .. {max(pr)}  (median ~{sorted(pr)[len(pr)//2]})")
print("with sku:", sum(1 for p in products if p['sku']))
