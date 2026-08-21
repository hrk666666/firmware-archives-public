#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_images.py v2 — 从 mi.com 官方 CDN 抓取设备产品渲染图
改进：按宽高比筛选（产品图接近方形/竖图，排除横幅条），下载后验证 PNG 尺寸
用法: python3 fetch_images.py
输出: docs/assets/devices/{code}.png
"""
import os
import re
import struct
import sys
import time
import urllib.request

BASE = "https://www.mi.com/tw/product/{slug}/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}

# code -> mi.com 台湾站 slug
SLUGS = {
    "miwear.watch.p67cn":  "xiaomi-smart-band-10-pro",
    "miwear.watch.o66cn":  "xiaomi-smart-band-10",
    "miwear.watch.n67cn":  "xiaomi-smart-band-9-pro",
    "miwear.watch.n66cn":  "xiaomi-smart-band-9",
    "lchz.watch.m67":      "xiaomi-smart-band-8-pro",
    "miwear.watch.m66":    "xiaomi-smart-band-8",
    "hqbd3.watch.l67":     "xiaomi-smart-band-7-pro",
    "miwear.watch.p62":    "xiaomi-watch-s5",
    "mijia.watch.o62":     "xiaomi-watch-s4",
    "mijia.watch.n62":     "xiaomi-watch-s3",
    "miwear.watch.p65":    "redmi-watch-6",
    "miwear.watch.o65":    "redmi-watch-5",
    "lchz.watch.n65":      "redmi-watch-4",
    "miwear.watch.o63":    "xiaomi-watch-s4-41mm",
    "miwear.watch.p62lte": "xiaomi-watch-s5",
    "mijia.watch.o62lte":  "xiaomi-watch-s4",
    "mijia.watch.n62lte":  "xiaomi-watch-s3",
    "miwear.watch.n69cn":  "redmi-band-3",
    "mijia.watch.m69":     "redmi-band-2",
}

IMG_RE = re.compile(r"https://i\d+\.appmifile\.com/[^\"'\s)]+\.(?:png|jpg|jpeg|webp)(?:\?[^\"'\s)]*)?")

# 坏文件特征（PWA 默认图标等）
BAD_MARKERS = ["maskable", "pwa", "favicon", "apple-touch"]


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def png_size(data):
    """从 PNG 头解析宽高, 非 PNG 返回 None"""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return w, h


def jpg_size(data):
    """JPEG 尺寸 (简版)"""
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def size_of(data):
    return png_size(data) or jpg_size(data)


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "assets", "devices")
    os.makedirs(out_dir, exist_ok=True)
    ok, fail = [], []
    for code, slug in SLUGS.items():
        dst = os.path.join(out_dir, f"{code}.png")
        if os.path.exists(dst) and os.path.getsize(dst) > 20000:
            ok.append((code, "cached"))
            continue
        try:
            page = fetch(BASE.format(slug=slug)).decode("utf-8", errors="ignore")
            imgs = IMG_RE.findall(page)
            imgs = [i for i in imgs if not any(m in i.lower() for m in BAD_MARKERS)]
            imgs = list(dict.fromkeys(imgs))  # 去重保序
            if not imgs:
                fail.append((code, "no image"))
                print(f"[!] {code}: 页面无可用图片")
                continue

            # 依次下载候选，选第一张宽高比合理的
            picked = None
            for u in imgs[:12]:
                try:
                    data = fetch(u)
                    wh = size_of(data)
                    if not wh:
                        continue
                    w, h = wh
                    if w < 300 or h < 300:
                        continue
                    ratio = w / h
                    if 0.55 <= ratio <= 1.8:  # 产品图接近方形/略宽
                        picked = (u, data)
                        break
                except Exception:
                    continue
            if not picked:
                fail.append((code, "no square image"))
                print(f"[!] {code}: 未找到方形产品图 ({slug})")
                continue
            u, data = picked
            with open(dst, "wb") as f:
                f.write(data)
            w, h = size_of(data)
            ok.append((code, f"{w}x{h} {len(data)//1024}KB"))
            print(f"[✓] {code}: {w}x{h} {u[:80]}")
        except Exception as e:
            fail.append((code, str(e)[:60]))
            print(f"[x] {code}: {e}")
        time.sleep(0.4)

    print("\n===== 结果 =====")
    print(f"成功 {len(ok)}")
    for c, info in ok:
        print(f"  ✓ {c}: {info}")
    print(f"失败 {len(fail)}")
    for c, why in fail:
        print(f"  x {c}: {why}")


if __name__ == "__main__":
    main()
