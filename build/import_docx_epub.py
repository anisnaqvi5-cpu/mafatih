#!/usr/bin/env python3
"""
import_docx_epub.py — .docx یا .epub سے متن نکال کر data/items/*.json بناتا ہے۔
کسی اضافی library کی ضرورت نہیں — صرف Python 3۔

استعمال:
    python3 build/import_docx_epub.py mafatih.docx --cat adiya
    python3 build/import_docx_epub.py mafatih.epub --cat ziarat --dry

اختیارات:
    --cat   category id (adiya / ziarat / amaal / namaz)   [لازم]
    --dry   کچھ save نہ کرو، صرف دکھاؤ کہ کیا بنے گا      [تجویز کردہ پہلا قدم]
    --out   کہاں save ہو (default: data/items)

کام کرنے کا طریقہ:
  • bold یا بڑے heading والی سطر  → نئی دعا کا عنوان
  • عربی سطر (اردو کے مخصوص حروف ٹ ڈ ڑ ے ں گ چ پ نہیں)  → "ar"
  • اُس کے فوراً بعد آنے والی اردو سطر                    → اُسی لائن کا "ur"
"""
import argparse, json, os, re, sys, unicodedata, zipfile
from html.parser import HTMLParser

# ── اردو کے وہ حروف جو عربی میں نہیں ہوتے ──────────────────
URDU_ONLY = set("ٹڈڑںھےگچپژۓہ")
ARABIC_RANGE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF]')

def is_arabic_line(t):
    """اگر سطر میں اردو کے مخصوص حروف نہ ہوں تو اسے عربی مانا جائے"""
    if not ARABIC_RANGE.search(t):
        return False
    return not (URDU_ONLY & set(t))

def clean(t):
    t = unicodedata.normalize("NFC", t)
    t = t.replace("\u200c", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()

def slug(t, n):
    s = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return s or f"item-{n}"

# ── DOCX ───────────────────────────────────────────────────
def read_docx(path):
    """(text, is_heading) کی فہرست واپس کرتا ہے"""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        text = clean("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)))
        if not text:
            continue
        heading = bool(re.search(r'w:pStyle w:val="(Heading|Title|عنوان)', p)) \
                  or "<w:b/>" in p or '<w:b ' in p
        out.append((text, heading))
    return out

# ── EPUB ───────────────────────────────────────────────────
class _H(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows = []; self.buf = []; self.head = False; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.skip += 1
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "li", "br"): self._flush()
        if tag in ("h1", "h2", "h3", "h4", "b", "strong"): self.head = True
    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip: self.skip -= 1
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "li"): self._flush()
    def handle_data(self, d):
        if not self.skip: self.buf.append(d)
    def _flush(self):
        t = clean("".join(self.buf)); self.buf = []
        if t: self.rows.append((t, self.head))
        self.head = False

def read_epub(path):
    rows = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith((".xhtml", ".html", ".htm"))]
        # spine کی ترتیب استعمال کرو، ورنہ نام کے حساب سے
        try:
            opf = next(n for n in z.namelist() if n.endswith(".opf"))
            data = z.read(opf).decode("utf-8", "ignore")
            base = os.path.dirname(opf)
            hrefs = dict(re.findall(r'id="([^"]+)"[^>]*href="([^"]+)"', data))
            order = [os.path.join(base, hrefs[i]).replace("\\", "/")
                     for i in re.findall(r'<itemref[^>]*idref="([^"]+)"', data) if i in hrefs]
            names = [n for n in order if n in z.namelist()] or sorted(names)
        except Exception:
            names = sorted(names)
        for n in names:
            p = _H(); p.feed(z.read(n).decode("utf-8", "ignore")); p._flush()
            rows += p.rows
    return rows

# ── متن کو items میں بدلنا ─────────────────────────────────
def to_items(rows, cat):
    items, cur = [], None
    for text, heading in rows:
        if heading and len(text) < 90:
            cur = {"id": "", "cat": cat, "ur": text, "en": "", "when": "",
                   "audio": [], "lines": []}
            items.append(cur)
            continue
        if cur is None:
            cur = {"id": "", "cat": cat, "ur": "بلا عنوان", "en": "", "when": "",
                   "audio": [], "lines": []}
            items.append(cur)
        if is_arabic_line(text):
            cur["lines"].append({"ar": text, "ur": ""})
        elif cur["lines"] and not cur["lines"][-1]["ur"]:
            cur["lines"][-1]["ur"] = text          # پچھلی عربی سطر کا ترجمہ
        else:
            cur["lines"].append({"ar": "", "ur": text})
    for n, it in enumerate(items, 1):
        it["id"] = slug(it["en"] or it["ur"], n) if re.search(r"[a-z]", it["en"] or "") \
                   else f"{cat}-{n:03d}"
        it["lines"] = [l for l in it["lines"] if l["ar"] or l["ur"]]
    return [i for i in items if i["lines"]]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--cat", required=True)
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "items"))
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    ext = a.file.lower().rsplit(".", 1)[-1]
    if ext == "docx":  rows = read_docx(a.file)
    elif ext == "epub": rows = read_epub(a.file)
    else:
        sys.exit("صرف .docx یا .epub قبول ہے")

    items = to_items(rows, a.cat)
    print(f"{len(rows)} پیراگراف → {len(items)} متون\n")
    for it in items:
        miss = sum(1 for l in it["lines"] if not l["ur"])
        flag = f"  ⚠ {miss} سطروں کا ترجمہ نہیں" if miss else ""
        print(f"  {it['id']:<14} {it['ur'][:34]:<36} {len(it['lines'])} سطریں{flag}")

    if a.dry:
        if items:
            print("\nنمونہ:\n" + json.dumps(items[0], ensure_ascii=False, indent=1)[:700])
        print("\n(--dry تھا، کچھ save نہیں ہوا)")
        return

    os.makedirs(a.out, exist_ok=True)
    for it in items:
        json.dump(it, open(os.path.join(a.out, it["id"] + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"\n✓ {len(items)} فائلیں {a.out} میں بن گئیں۔ اب چلائیں: python3 build/build.py")

if __name__ == "__main__":
    main()
