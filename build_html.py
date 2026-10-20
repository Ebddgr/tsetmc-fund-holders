#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data.json + template.html -> گزارش HTML تک‌فایلی.

    python fetch_tsetmc.py     # data.json
    python build_html.py       # tsetmc-fund-holders.html
"""
import base64
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GROUPS = [(0, 29, "۱"), (29, 53, "۲"), (53, 73, "۳")]


def b64(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def group_of(i):
    for a, b, g in GROUPS:
        if a <= i < b:
            return g
    return ""


def main():
    data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
    funds, agg = [], {}
    for i, f in enumerate(data["funds"]):
        row = {"name": f.get("short") or f["name"],
               "full": f.get("full", ""), "ins": f["ins"], "units": f.get("units", 0),
               "price": f["price"], "g": group_of(i), "holders": []}
        for h in f["holders"]:
            row["holders"].append({"n": h["n"], "u": h["u"], "p": h["p"], "c": h.get("c", 0)})
            a = agg.setdefault(h["n"], {"funds": 0, "value": 0.0})
            a["funds"] += 1
            a["value"] += h["u"] * f["price"]
        funds.append(row)

    payload = {
        "date": data.get("stamp", "")[:10],
        "stamp": data.get("stamp", ""),
        "removed": data.get("removed", 0),
        "funds": funds,
        "agg": sorted(([k, v["funds"], v["value"]] for k, v in agg.items()),
                      key=lambda r: -r[2]),
    }

    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    html = (tpl.replace("__FONT_REG__", b64(os.path.join(HERE, "assets", "iransans.woff2")))
               .replace("__FONT_BOLD__", b64(os.path.join(HERE, "assets", "iransans-bold.woff2")))
               .replace("__DATA__", json.dumps(payload, ensure_ascii=False), 1))
    out = os.path.join(HERE, "tsetmc-fund-holders.html")
    open(out, "w", encoding="utf-8").write(html)
    print("نوشته شد:", out, os.path.getsize(out), "بایت")


if __name__ == "__main__":
    main()
