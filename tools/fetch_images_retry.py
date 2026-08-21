#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_images_retry.py — 补抓失败/损坏的设备图，支持多 slug 候选"""
import os
import re
import struct
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
IMG_RE = re.compile(r"https://i\d+\.appmifile\.com/[^\"'\s)]+\.(?:png|jpg|jpeg|webp)(?:\?[^\"'\s)]*)?")
BAD_MARKERS = ["maskable", "pwa", "favicon", "apple-touch"]

# code -> slug 候选列表（依次尝试）
RETRY = {
    "lchz.watch.m67":     ["xiaomi-smart-band-8-pro"],
    "mijia.watch.n62":    ["xiaomi-watch-s3"],
    "mijia.watch.n62lte": ["xiaomi-watch-s3-esim", "xiaomi-watch-s3"],
    "miwear.watch.p62":   ["xiaomi-watch-s5-46mm", "xiaomi-watch-s5", "xiaomi-watch-s5-esim"],
    "miwear.watch.p62lte":["xiaomi-watch-s5-esim", "xiaomi-watch-s5"],
    "lchz.watch.n65":     ["redmi-watch-4", "redmi-watch-4-active"],
    "miwear.watch.n69cn": ["redmi-band-3", "redmi-band-3-pro"],
    "mijia.watch.m69":    ["redmi-band-2", "redmi-band-2-pro"],
}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def size_of(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
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


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "assets", "devices")
    # 删除损坏文件 (<15KB)
    for f in os.listdir(out_dir):
        p = os.path.join(out_dir, f)
        if os.path.getsize(p) < 15000:
            os.remove(p)
            print(f"[del] 损坏文件 {f}")

    for code, slugs in RETRY.items():
        dst = os.path.join(out_dir, f"{code}.png")
        got = None
        for slug in slugs:
            try:
                page = fetch(f"https://www.mi.com/tw/product/{slug}/").decode("utf-8", errors="ignore")
                imgs = [i for i in IMG_RE.findall(page) if not any(m in i.lower() for m in BAD_MARKERS)]
                imgs = list(dict.fromkeys(imgs))
                for u in imgs[:15]:
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
            time.sleep(0.4)
        if got:
            with open(dst, "wb") as f:
                f.write(got[1])
            w, h = size_of(got[1])
            print(f"[✓] {code}: {w}x{h} {len(got[1])//1024}KB  {got[0][:80]}")
        else:
            print(f"[!] {code}: 所有 slug 均失败")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
