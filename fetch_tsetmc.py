#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""دارندگان صندوق‌های سرمایه‌گذاری درآمد ثابت را از API رسمی tsetmc می‌گیرد
و data.json + holders.csv می‌سازد.

اجرا:
    python fetch_tsetmc.py            # همه ۷۳ صندوق
    python fetch_tsetmc.py --limit 3  # فقط برای تست
"""
import argparse
import csv
import json
import sys
import time
from urllib.parse import quote

import requests

API = "https://cdn.tsetmc.com/api"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json",
    "Referer": "https://cdn.tsetmc.com/",
}

# «هامز» در tsetmc «هام‌رز» است.
FUND_NAMES = [
    "آتیه ملت", "آکورد", "آسا", "دامون", "فردا", "پاداش", "فیروزا", "اعتماد", "آلا",
    "داریک", "هام‌رز", "افران", "امین یکم", "اوصتا", "بمان", "پارند", "پایا", "تداوم",
    "رابین", "آوند", "مانی", "ثبات", "فاخر", "خاتم", "دارا", "آرامش", "یارا", "ارکیده",
    "ثابت اکسیژن",
    "پاسارگاد", "تصمیم", "توسکا", "ثمر", "نخل", "پایش", "سام", "شمیم", "آسال", "کارآمد",
    "کمند", "کیان", "اونیکس", "کارما", "آسان", "ماهور", "نشان", "کارین", "درین", "دوام",
    "رشد", "زمرد کوروش", "ساحل", "سپر",
    "سپیدما", "ستاره", "خورشید", "طلوع", "کامیاب", "صایند", "گنجینه", "گنجین", "لبخند",
    "دیبا", "خزانه ملت", "اصیل", "اعتبار", "آفاق", "کاج", "کارا", "صنهال", "نیلی",
    "همای", "یاقوت",
]

EXCLUDED = {
    "شخص حقيقي",
    "ETFكدرزروصندوقهاي سرمايه گذاري قابل معامله",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def get(path, tries=4):
    url = f"{API}/{path}"
    for i in range(tries):
        try:
            r = SESSION.get(url, timeout=25)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def search(name):
    data = get("Instrument/GetInstrumentSearch/" + quote(name))
    rows = (data or {}).get("instrumentSearch") or []
    if not rows:
        return None
    for row in rows:
        if row.get("lVal30") == name:
            return row["insCode"], row["lVal30"]
    return rows[0]["insCode"], rows[0].get("lVal30", name)


def holders(ins):
    data = get(f"Shareholder/GetInstrumentShareHolderLast/{ins}")
    out = []
    for h in (data or {}).get("shareHolder") or []:
        out.append({
            "n": (h.get("shareHolderName") or "").strip(),
            "u": h.get("numberOfShares") or 0,
            "p": float(h.get("perOfShares") or 0),
            "c": h.get("changeAmount") or 0,
        })
    return out


def info(ins):
    i = (get(f"Instrument/GetInstrumentInfo/{ins}") or {}).get("instrumentInfo", {})
    return {
        "full": i.get("faraDesc") or i.get("lVal18AFC") or "",
        "units": i.get("zTitad") or 0,
        "sector": (i.get("sector") or {}).get("lSecVal", ""),
    }


def price(ins):
    c = (get(f"ClosingPrice/GetClosingPriceInfo/{ins}") or {}).get("closingPriceInfo", {})
    return c.get("pClosing") or c.get("pDrCotVal") or 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="data.json")
    args = ap.parse_args()

    names = FUND_NAMES[:args.limit] if args.limit else FUND_NAMES
    funds, missing, removed = [], [], 0

    for name in names:
        hit = search(name)
        if not hit:
            missing.append(name)
            print(f"[!] پیدا نشد: {name}", file=sys.stderr)
            continue
        ins, ticker = hit
        keep = []
        for h in holders(ins):
            if h["n"] in EXCLUDED:
                removed += 1
                continue
            keep.append(h)
        funds.append({"name": ticker or name, "short": name, "ins": ins, **info(ins),
                      "price": price(ins), "holders": keep})
        print(f"[ok] {ticker}: {len(keep)} دارنده، قیمت {funds[-1]['price']}")

    total = sum(f["units"] * f["price"] for f in funds)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"source": "tsetmc.com",
                   "stamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "funds": funds, "removed": removed, "missing": missing},
                  fh, ensure_ascii=False, indent=1)

    with open("holders.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["صندوق", "کد نماد", "قیمت پایانی (ریال)", "نام دارنده",
                    "درصد از کل واحدها", "ارزش (میلیارد تومان)", "تغییر واحد"])
        for f in funds:
            for h in f["holders"]:
                w.writerow([f["name"], f["ins"], f["price"], h["n"], h["p"],
                            round(h["u"] * f["price"] / 1e10, 1), h["c"]])

    print(f"\n{len(funds)} صندوق، {sum(len(f['holders']) for f in funds)} ردیف، "
          f"حذف‌شده {removed}، ارزش کل {total/1e10:,.1f} میلیارد تومان")
    if missing:
        print("پیدا نشد:", "، ".join(missing))


if __name__ == "__main__":
    main()
