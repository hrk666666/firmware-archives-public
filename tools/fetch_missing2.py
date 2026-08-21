#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_missing2.py — 补抓缺失设备图（并发版）
台湾站 404 的型号尝试中国大陆站 mi.com。
"""
import os
import re
import struct
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE_DIR, "..", "docs", "assets", "devices")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
      "Referer": "https://www.mi.com/"}
IMG_RE = re.compile(r"https://i\d+\.appmifile\.com/[^\"'\s)]+\.(?:png|jpg|jpeg|webp)(?:\?[^\"'\s)]*)?")
BAD_MARKERS = ["maskable", "pwa", "favicon", "apple-touch", "icon", "logo"]

# code -> [(站点, slug), ...]
FETCH = {
    "mijia.watch.n62":    [("tw", "xiaomi-watch-s3"), ("cn", "xiaomi-watch-s3")],
    "mijia.watch.n62lte": [("tw", "xiaomi-watch-s3"), ("cn", "xiaomi-watch-s3")],
    "mijia.watch.n62cg":  [("tw", "xiaomi-watch-s3"), ("cn", "xiaomi-watch-s3")],
    "mijia.watch.n62car": [("tw", "xiaomi-watch-s3"), ("cn", "xiaomi-watch-s3")],
    "mijia.watch.n62s":   [("cn", "xiaomi-watch-s4-sport"), ("tw", "xiaomi-watch-s4-sport")],
    "lchz.watch.n65":     [("tw", "redmi-watch-4"), ("cn", "redmi-watch-4")],
    "midr.watch.ds":      [("cn", "xiaomi-watch-color"), ("cn", "mi-watch-color")],
    "mijia.watch.band01": [("cn", "redmi-band"), ("cn", "redmi-band-1")],
    "miwear.watch.n69cn": [("cn", "redmi-band-3"), ("cn", "redmi-band3")],
    "mijia.watch.m69":    [("cn", "redmi-band-2"), ("cn", "redmi-band2")],
    "midr.watch.m62s":    [("cn", "xiaomi-watch-s2"), ("tw", "xiaomi-watch-s2")],
    "midr.watch.m62a":    [("cn", "xiaomi-watch-s2"), ("tw", "xiaomi-watch-s2")],
    "midr.watch.k65":     [("cn", "redmi-watch-3"), ("cn", "redmi-watch3")],
    "midr.watch.k63":     [("cn", "redmi-watch-3"), ("cn", "redmi-watch-2")],
    "midr.watch.k62":     [("cn", "redmi-watch-2"), ("cn", "redmi-watch2")],
    "lchz.watch.m65s":    [("tw", "redmi-watch-4"), ("cn", "redmi-watch-4")],
}


def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def img_size(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            m = data[i + 1]
            if m in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def ext_of(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:2] == b"\xff\xd8":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def try_slug(code, site, slug):
    base = "https://www.mi.com/tw/product/" if site == "tw" else "https://www.mi.com/product/"
    page = fetch(base + slug + "/").decode("utf-8", errors="ignore")
    imgs = list(dict.fromkeys(i for i in IMG_RE.findall(page)
                              if not any(m in i.lower() for m in BAD_MARKERS)))
    for u in imgs[:12]:
        try:
            data = fetch(u)
            wh = img_size(data)
            if not wh or len(data) < 15000:
                continue
            w, h = wh
            if w < 300 or h < 300:
                continue
            if 0.55 <= w / h <= 1.8:
                return u, data
        except Exception:
            continue
    return None


def grab_one(code, sites):
    for site, slug in sites:
        try:
            r = try_slug(code, site, slug)
            if r:
                return r
        except Exception as e:
            print(f"  [{code}] {site}/{slug}: {str(e)[:60]}")
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    todo = []
    for code, sites in FETCH.items():
        existing = [f for f in os.listdir(OUT) if f.startswith(code + ".")]
        if existing and any(os.path.getsize(os.path.join(OUT, f)) > 15000 for f in existing):
            print(f"[cached] {code}")
            continue
        todo.append((code, sites))

    print(f"待抓: {len(todo)} 台")
    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(grab_one, c, s): c for c, s in todo}
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                r = fut.result()
                results[code] = r
            except Exception as e:
                results[code] = None
                print(f"  [x] {code}: {str(e)[:80]}")

    ok, fail = [], []
    for code, r in results.items():
        if r:
            u, data = r
            ext = ext_of(data) or "png"
            with open(os.path.join(OUT, f"{code}.{ext}"), "wb") as f:
                f.write(data)
            w, h = img_size(data)
            ok.append((code, f"{w}x{h} {ext} {len(data)//1024}KB"))
            print(f"[✓] {code}: {w}x{h} {ext} {len(data)//1024}KB")
        else:
            fail.append(code)
            print(f"[!] {code}: 全部失败")

    print(f"\n===== 结果: 成功 {len(ok)} / 失败 {len(fail)} =====")
    for c, info in ok:
        print(f"  ✓ {c}: {info}")
    for c in fail:
        print(f"  x {c}")


if __name__ == "__main__":
    main()
