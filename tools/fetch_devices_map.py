#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_devices_map.py — 从 OronBox 官方源码自动提取设备代号映射，生成 docs/devices-map.json

数据源: https://github.com/zxor-org/OronBox (AGPL-3.0)
  - lib/src/device/core/xiaomi_wearable_catalog.dart  (小米/红米系 VelaOS)

生成的 devices-map.json 供 build_data.py 使用：
  - 固件文件名中的设备代号（如 miwear.watch.p68cn）→ 自动匹配到设备名
  - OronBox 上游新增设备时，本脚本重新拉取即可自动同步到固件选择器页面

用法: python3 tools/fetch_devices_map.py [--out docs/devices-map.json]
"""
import json
import os
import re
import sys
import time
import urllib.request

ORONBOX_RAW = (
    "https://raw.githubusercontent.com/zxor-org/OronBox/main/"
    "lib/src/device/core/xiaomi_wearable_catalog.dart"
)

# OronBox family -> 本站 category
FAMILY_CAT = {
    "band": "band",
    "bandPro": "band",
    "redmiWatch": "watch",
    "xiaomiWatch": "watch",
    "unknown": "other",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "firmware-archives-device-map"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_xiaomi_catalog(src):
    """解析 xiaomi_wearable_catalog.dart 中的 XiaomiWearableIdentity 条目"""
    entries = {}
    for m in re.finditer(r"'([a-z0-9]+)': XiaomiWearableIdentity\((.*?)\n  \),", src, re.S):
        codename, body = m.group(1), m.group(2)

        def grab(pat):
            x = re.search(pat, body)
            return x.group(1) if x else None

        aliases = []
        if "aliases:" in body:
            aliases = re.findall(r"'([^']+)'", body.split("aliases:", 1)[1])

        entries[codename] = {
            "codename": codename,
            "displayName": grab(r"displayName: '([^']+)'") or codename,
            "abV2Id": grab(r"abV2Id: '([^']+)'") or codename,
            "family": grab(r"family: XiaomiWearableFamily\.(\w+)") or "unknown",
            "chip": grab(r"chip: XiaomiWearableChip\.(\w+)") or "unknown",
            "protocol": grab(r"protocol: XiaomiWearableProtocol\.(\w+)") or "unsupported",
            "aliases": aliases,
        }
    return entries


def main():
    out = "docs/devices-map.json"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]

    print("[*] 抓取 OronBox xiaomi_wearable_catalog.dart ...")
    src = fetch(ORONBOX_RAW)
    xiaomi = parse_xiaomi_catalog(src)
    print(f"[*] 解析到 {len(xiaomi)} 个小米系设备条目")

    # alias 索引：alias（含 codename 自身）-> codename
    alias_index = {}
    for cn, info in xiaomi.items():
        alias_index[cn] = cn
        for a in info["aliases"]:
            alias_index.setdefault(a, cn)

    data = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "zxor-org/OronBox (AGPL-3.0) xiaomi_wearable_catalog.dart",
        "source_url": ORONBOX_RAW,
        "xiaomi_count": len(xiaomi),
        "alias_count": len(alias_index),
        "family_category": FAMILY_CAT,
        "xiaomi": xiaomi,
        "alias_index": alias_index,
    }

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"[✓] 写入 {out}: {len(xiaomi)} codename / {len(alias_index)} alias")
    return data


if __name__ == "__main__":
    main()
