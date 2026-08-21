#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_missing.py — 补全缺失设备图
策略：
  1. 同款变体（NFC/陶瓷/限定版等）直接复用标准版主图（复制 webp）
  2. 真正缺失的型号从 mi.com 台湾站抓取（保留原始格式）
  3. 抓不到的跳过（页面有占位符兜底）
用法: python3 fetch_missing.py
"""
import os
import re
import struct
import sys
import time
import urllib.request
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE_DIR, "..", "docs", "assets", "devices")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
IMG_RE = re.compile(r"https://i\d+\.appmifile\.com/[^\"'\s)]+\.(?:png|jpg|jpeg|webp)(?:\?[^\"'\s)]*)?")
BAD_MARKERS = ["maskable", "pwa", "favicon", "apple-touch"]

# 1) 变体复用映射: 变体code -> 标准版code（复用标准版图片）
VARIANTS = {
    "miwear.watch.o66nfc": "miwear.watch.o66cn",   # 手环10 NFC
    "miwear.watch.p67gln": "miwear.watch.p67cn",   # 手环10 Pro NFC
    "miwear.watch.p67tc":  "miwear.watch.p67cn",   # 手环10 Pro 陶瓷
    "miwear.watch.o66lj":  "miwear.watch.o66cn",   # 手环10 耀影金
    "miwear.watch.o66tc":  "miwear.watch.o66cn",   # 手环10 陶瓷
    "miwear.watch.m66nfc": "miwear.watch.m66",     # 手环8 NFC
    "lchz.watch.m67ys":    "lchz.watch.m67",       # 手环8 Pro 原神版
    "miwear.watch.n66nfc": "miwear.watch.n66cn",   # 手环9 NFC
    "miwear.watch.n66tc":  "miwear.watch.n66cn",   # 手环9 陶瓷
    "miwear.watch.n66gl":  "miwear.watch.n66cn",   # 手环9 海外版
    "miwear.watch.o65m":   "miwear.watch.o65",     # Watch 5 eSIM
    "mijia.watch.o62m":    "mijia.watch.o62",      # Watch S4 15周年
}

# 2) 需要真实抓取的: code -> slug 候选列表
FETCH = {
    "mijia.watch.n62":     ["xiaomi-watch-s3", "xiaomi-watch-s3-esim"],
    "mijia.watch.n62lte":  ["xiaomi-watch-s3-esim", "xiaomi-watch-s3"],
    "mijia.watch.n62cg":   ["xiaomi-watch-s3", "xiaomi-watch-s3-su7"],
    "mijia.watch.n62car":  ["xiaomi-watch-s3", "xiaomi-watch-s3-su7"],
    "mijia.watch.n62s":    ["xiaomi-watch-s4-sport"],
    "lchz.watch.n65":      ["redmi-watch-4", "redmi-watch-4-active"],
    "midr.watch.ds":       ["mi-watch-color", "xiaomi-watch-color"],
    "mijia.watch.band01":  ["redmi-band-1", "redmi-band"],
    "miwear.watch.n69cn":  ["redmi-band-3"],
    "mijia.watch.m69":     ["redmi-band-2"],
    "midr.watch.m62s":     ["xiaomi-watch-s2"],
    "midr.watch.m62a":     ["xiaomi-watch-s2"],
    "midr.watch.k65":      ["redmi-watch-3"],
    "midr.watch.k63":      ["redmi-watch-3", "redmi-watch-2"],
    "midr.watch.k62":      ["redmi-watch-2"],
    "lchz.watch.m65s":     ["redmi-watch-4-active", "redmi-watch-4"],
}


def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def size_of(data):
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


def main():
    os.makedirs(OUT, exist_ok=True)

    # ---- 1) 变体复制 ----
    copied = 0
    for var, base in VARIANTS.items():
        # 找标准版文件（任意扩展名）
        base_file = None
        for ext in ("webp", "png", "jpg"):
            p = os.path.join(OUT, f"{base}.{ext}")
            if os.path.exists(p):
                base_file = p
                break
        if not base_file:
            print(f"[skip] {var}: 标准版 {base} 无图")
            continue
        var_file = None
        for ext in ("webp", "png", "jpg"):
            p = os.path.join(OUT, f"{var}.{ext}")
            if os.path.exists(p):
                var_file = p
                break
        if var_file and os.path.getsize(var_file) > 15000:
            continue  # 已有图
        shutil.copy2(base_file, os.path.join(OUT, f"{var}{os.path.splitext(base_file)[1]}"))
        copied += 1
        print(f"[✓] {var} <- 复用 {os.path.basename(base_file)}")

    # ---- 2) 真实抓取 ----
    ok, fail = [], []
    for code, slugs in FETCH.items():
        # 已有图则跳过
        existing = [f for f in os.listdir(OUT) if f.startswith(code + ".")]
        if existing and any(os.path.getsize(os.path.join(OUT, f)) > 15000 for f in existing):
            print(f"[cached] {code}")
            continue
        got = None
        for slug in slugs:
            try:
                page = fetch(f"https://www.mi.com/tw/product/{slug}/").decode("utf-8", errors="ignore")
                imgs = [i for i in IMG_RE.findall(page) if not any(m in i.lower() for m in BAD_MARKERS)]
                imgs = list(dict.fromkeys(imgs))
                for u in imgs[:8]:
                    try:
                        data = fetch(u)
                        wh = size_of(data)
                        if not wh or len(data) < 15000:
                            continue
                        w, h = wh
                        if w < 300 or h < 300:
                            continue
                        if 0.55 <= w / h <= 1.8:
                            got = (u, data)
                            break
                    except Exception:
                        continue
                if got:
                    break
            except Exception as e:
                print(f"[x] {code} slug={slug}: {str(e)[:50]}")
            time.sleep(0.2)
        if got:
            u, data = got
            ext = ext_of(data) or "png"
            with open(os.path.join(OUT, f"{code}.{ext}"), "wb") as f:
                f.write(data)
            w, h = size_of(data)
            ok.append((code, f"{w}x{h} {ext} {len(data)//1024}KB"))
            print(f"[✓] {code}: {w}x{h} {ext} {u[:80]}")
        else:
            fail.append(code)
            print(f"[!] {code}: 所有 slug 均失败")
        time.sleep(0.3)

    print(f"\n===== 结果: 复用 {copied} / 抓取成功 {len(ok)} / 失败 {len(fail)} =====")
    for c, info in ok:
        print(f"  ✓ {c}: {info}")
    for c in fail:
        print(f"  x {c}")


if __name__ == "__main__":
    main()
