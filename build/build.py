#!/usr/bin/env python3
"""
build.py — data/items/*.json کو پڑھ کر data/index.json دوبارہ بناتا ہے۔

استعمال:  python3 build/build.py
جب بھی نیا متن data/items/ میں ڈالیں، یہ ایک بار چلا دیں۔
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = os.path.join(ROOT, "data", "items")
INDEX = os.path.join(ROOT, "data", "index.json")

# categories کی فہرست یہاں ایک ہی جگہ رکھی جاتی ہے
# اعمال کے مہینے — قمری ترتیب میں
HIJRI_MONTHS = [
    ("muharram","محرم"),("safar","صفر"),("rabi1","ربیع الاول"),("rabi2","ربیع الثانی"),
    ("jumada1","جمادی الاولیٰ"),("jumada2","جمادی الثانیہ"),("rajab","رجب"),
    ("shaban","شعبان"),("ramadan","رمضان"),("shawwal","شوال"),
    ("dhulqada","ذی القعدہ"),("dhulhijja","ذی الحجہ"),
]

CATEGORIES = [
    {"id": "adiya",  "ur": "ادعیہ",  "en": "Duas",    "note": "روزانہ اور مشہور دعائیں"},
    {"id": "ziarat", "ur": "زیارات", "en": "Ziyarat", "note": "معصومینؑ کی زیارتیں"},
    {"id": "amaal",  "ur": "اعمال",  "en": "Amaal",   "note": "دنوں اور مہینوں کے اعمال"},
    {"id": "namaz",  "ur": "نماز",   "en": "Namaz",   "note": "نمازیں اور تعقیبات"},
]

REQUIRED = ("id", "cat", "ur", "lines")

def main():
    valid_cats = {c["id"] for c in CATEGORIES}
    items, errors = [], []

    for fn in sorted(os.listdir(ITEMS)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(ITEMS, fn)
        try:
            it = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            errors.append(f"{fn}: JSON خراب ہے — {e}")
            continue

        for k in REQUIRED:
            if not it.get(k):
                errors.append(f"{fn}: '{k}' موجود نہیں")
        if it.get("id") and it["id"] != fn[:-5]:
            errors.append(f"{fn}: id ({it['id']}) فائل کے نام سے مختلف ہے")
        if it.get("cat") and it["cat"] not in valid_cats:
            errors.append(f"{fn}: cat '{it['cat']}' معلوم نہیں")
        if it.get("audio") is not None and not isinstance(it["audio"], list):
            errors.append(f"{fn}: 'audio' اب array ہونا چاہیے — [{{reciter, file}}]")
        for a in (it.get("audio") or []):
            if not isinstance(a, dict) or not a.get("file"):
                errors.append(f"{fn}: audio میں 'file' نہیں")
        for n, l in enumerate(it.get("lines", []), 1):
            if not l.get("ar"):
                errors.append(f"{fn}: سطر {n} میں عربی متن نہیں")

        items.append({
            "id": it.get("id", fn[:-5]),
            "cat": it.get("cat", ""),
            "group": it.get("group", ""),
            "hijri": it.get("hijri", []),
            "ur":  it.get("ur", ""),
            "en":  it.get("en", ""),
            "when": it.get("when", ""),
            "audio_count": len(it.get("audio") or []),
        })

    if errors:
        print("⚠ مسائل:")
        for e in errors:
            print("  -", e)

    # ہر مہینے میں کتنے اعمال ہیں
    groups = []
    for gid, gur in HIJRI_MONTHS:
        n = sum(1 for i in items if i["group"] == gid)
        groups.append({"id": gid, "ur": gur, "count": n})

    json.dump({"categories": CATEGORIES, "groups": groups, "items": items},
              open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✓ index.json بن گیا — {len(items)} متون")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
