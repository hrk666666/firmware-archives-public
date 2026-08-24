#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_data.py — 从 GitHub Releases 生成固件选择器 data.json
数据源: hrk666666/firmware-archives-public (公开仓, 下载无需登录)
用法: python3 build_data.py [--repo hrk666666/firmware-archives-public] [--out docs/data.json]
"""
import json
import os
import re
import sys
import time
import urllib.request

# ---------- 设备映射（与 README 对照表一致，来自官方欢迎语交叉核对） ----------
# category: band=手环, watch=手表, other=其他/待确认
DEVICES = {
    # 手环
    "miwear.watch.m66":   ("小米手环 8", "band", True, ""),
    "miwear.watch.m66nfc":("小米手环 8 NFC", "band", True, ""),
    "miwear.watch.n66cn": ("小米手环 9", "band", True, ""),
    "miwear.watch.n66nfc":("小米手环 9 NFC", "band", True, ""),
    "miwear.watch.n66tc": ("小米手环 9 陶瓷特别版", "band", True, ""),
    "miwear.watch.n66gl": ("小米手环 9（海外版）", "band", True, ""),
    "miwear.watch.n67cn": ("小米手环 9 Pro", "band", True, ""),
    "miwear.watch.o66cn": ("小米手环 10", "band", True, ""),
    "miwear.watch.o66nfc":("小米手环 10 NFC", "band", True, ""),
    "miwear.watch.o66tc": ("小米手环 10 陶瓷版", "band", True, ""),
    "miwear.watch.o66lj": ("小米手环 10 耀影金特别版", "band", True, ""),
    "miwear.watch.p67cn": ("小米手环 10 Pro", "band", True, ""),
    "miwear.watch.p67tc": ("小米手环 10 Pro 陶瓷版", "band", True, "官方欢迎语：小米手环10 Pro 陶瓷版"),
    "miwear.watch.p67gln":("小米手环 10 Pro NFC 版", "band", True, "官方欢迎语：小米手环10 Pro NFC版"),
    "miwear.watch.n69cn": ("Redmi 手环 3", "band", True, ""),
    "mijia.watch.m69":    ("Redmi 手环 2", "band", True, ""),
    "mijia.watch.band01": ("Redmi 手环（初代）", "band", False, "待确认"),
    "lchz.watch.m67":     ("小米手环 8 Pro", "band", True, "官方欢迎语：小米手环 8 Pro"),
    "lchz.watch.m67ys":   ("小米手环 8 Pro 原神定制版", "band", True, "官方欢迎语：小米手环8 Pro 原神定制版"),
    "hqbd3.watch.l67":    ("小米手环 7 Pro", "band", True, "类手表形态，官方欢迎语确认"),
    # 手表
    "mijia.watch.n62":    ("小米手表 S3", "watch", True, ""),
    "mijia.watch.n62lte": ("小米手表 S3 eSIM 版", "watch", True, ""),
    "mijia.watch.n62car": ("小米手表 S3 SU7 限定版", "watch", True, "官方欢迎语：Xiaomi Watch S3 eSIM（硬件为 eSIM 版）"),
    "mijia.watch.n62cg":  ("小米手表 S3 SU7 限定版", "watch", True, "同 n62car，官方欢迎语同为 Xiaomi Watch S3 eSIM"),
    "mijia.watch.o62":    ("小米手表 S4", "watch", True, ""),
    "mijia.watch.o62lte": ("小米手表 S4 eSIM 版", "watch", True, ""),
    "mijia.watch.o62m":   ("小米手表 S4 15 周年版", "watch", True, "XRING INSIDE，官方欢迎语：Xiaomi Watch S4 eSIM"),
    "miwear.watch.o63":   ("小米手表 S4（41mm）", "watch", True, ""),
    "mijia.watch.n62s":   ("小米手表 S4 Sport", "watch", True, ""),
    "miwear.watch.p62":   ("小米手表 S5（46mm）", "watch", True, ""),
    "miwear.watch.p62lte":("小米手表 S5 eSIM（46mm）", "watch", True, ""),
    "lchz.watch.n65":     ("REDMI Watch 4", "watch", True, ""),
    "miwear.watch.o65":   ("REDMI Watch 5", "watch", True, ""),
    "miwear.watch.o65m":  ("REDMI Watch 5 eSIM", "watch", True, "XRING INSIDE"),
    "miwear.watch.p65":   ("REDMI Watch 6", "watch", True, ""),
    "midr.watch.ds":      ("小米手表 Color", "watch", True, "官方更新说明标题：小米手表Color"),
    "mijia.watch.l61":    ("小米手表 S1 Pro", "watch", True, "OronBox 设备目录确认：l61 = Xiaomi Watch S1 Pro"),
    # 其他 / 待确认
    "lchz.watch.m65s":    ("未知设备（推测 REDMI Watch 4 Active 一带）", "other", False, "lchz 系列"),
    "lchz.watch.m65ac":   ("未知设备（推测 REDMI Watch 4 Active 一带）", "other", False, "lchz 系列，与 m65s 同代（ac 疑为 Active）"),
    "midr.watch.k62":     ("未知设备（midr 系列）", "other", False, "暂未查到公开对照"),
    "midr.watch.k63":     ("未知设备（midr 系列）", "other", False, "暂未查到公开对照"),
    "midr.watch.k65":     ("未知设备（midr 系列）", "other", False, "暂未查到公开对照"),
    "midr.watch.m62a":    ("未知设备（midr 系列）", "other", False, "暂未查到公开对照"),
    "midr.watch.m62s":    ("未知设备（midr 系列）", "other", False, "暂未查到公开对照"),
    "midr.watch.sports":  ("未知设备（midr 系列）", "other", False, "暂未查到公开对照"),
    "mijia.watch.v1":     ("未知设备", "other", False, "暂未查到公开对照"),
    "mj1205.motion.ecg":  ("米家系心电/血压类设备（推测）", "other", False, "推测为米家系心电/血压类设备"),
}

# 文件名: {code}_{version}_full_{hash}.bin
# 或     {code}_{version}_from_{old}_incremental_{hash}.bin
FULL_RE = re.compile(r"^(.+?)_(v[0-9][^_]*)_full_([0-9a-f]+)\.bin$")
INC_RE = re.compile(r"^(.+?)_(v[0-9][^_]*)_from_(v[0-9][^_]*)_incremental_([0-9a-f]+)\.bin$")


def load_device_map(path="docs/devices-map.json"):
    """加载 OronBox 自动生成的设备映射（tools/fetch_devices_map.py 产物）"""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def api_get(url, token=None, retries=3):
    req = urllib.request.Request(url, headers={
        "User-Agent": "firmware-archives-builder",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    last_err = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # 网络抖动/断流时重试
            last_err = e
            time.sleep(2 * (i + 1))
    raise last_err


def fetch_all_releases(repo, token):
    releases = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}"
        batch = api_get(url, token)
        if not batch:
            break
        releases.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.3)
    return releases


def version_key(v):
    """v3.101.043 -> (3, 101, 43) 用于排序"""
    nums = re.findall(r"\d+", v)
    return tuple(int(n) for n in nums) if nums else (0,)


def build(repo="hrk666666/firmware-archives-public", out="docs/data.json"):
    token = None
    tok_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".github_token")
    if os.path.exists(tok_file):
        token = open(tok_file).read().strip()

    print(f"[*] 拉取 {repo} releases ...")
    releases = fetch_all_releases(repo, token)
    print(f"[*] 共 {len(releases)} 个 release")

    # code -> { version -> {full: [], inc: []} }
    agg = {}
    asset_count = 0
    for r in releases:
        tag = r.get("tag_name", "")
        # tag 形如 firmware-{code}-{version}-{hash}，但以资产文件名为准
        for a in r.get("assets", []):
            name = a.get("name", "")
            size = a.get("size", 0)
            url = a.get("browser_download_url", "")
            m = FULL_RE.match(name)
            if m:
                code, ver, hsh = m.group(1), m.group(2), m.group(3)
                d = agg.setdefault(code, {})
                rel = d.setdefault(ver, {"full": [], "incrementals": []})
                rel["full"].append({"file": name, "size": size, "hash": hsh, "url": url})
                asset_count += 1
                continue
            m = INC_RE.match(name)
            if m:
                code, ver, old, hsh = m.group(1), m.group(2), m.group(3), m.group(4)
                d = agg.setdefault(code, {})
                rel = d.setdefault(ver, {"full": [], "incrementals": []})
                rel["incrementals"].append({"from": old, "file": name, "size": size, "hash": hsh, "url": url})
                asset_count += 1
                continue
            print(f"[!] 未识别资产: {name}")

    # 加载 OronBox 自动映射（三级优先：人工 DEVICES > OronBox 映射 > 未知）
    device_map = load_device_map(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "devices-map.json")
    )
    fam_cat = (device_map or {}).get("family_category", {})

    def resolve_device(code):
        if code in DEVICES:
            return DEVICES[code]
        if device_map and code in device_map.get("alias_index", {}):
            cn = device_map["alias_index"][code]
            info = device_map["xiaomi"][cn]
            return (
                info.get("displayName", code),
                fam_cat.get(info.get("family", "unknown"), "other"),
                False,
                f"来源：OronBox 设备目录（codename {cn}）",
            )
        return (code, "other", False, "未知设备（未在对照表）")

    devices = []
    for code, versions in agg.items():
        name, category, confirmed, note = resolve_device(code)
        rel_list = []
        for ver in sorted(versions.keys(), key=version_key, reverse=True):
            v = versions[ver]
            rel_list.append({
                "version": ver,
                "full": sorted(v["full"], key=lambda x: x["size"]),
                "incrementals": sorted(v["incrementals"], key=lambda x: version_key(x["from"]), reverse=True),
            })
        devices.append({
            "code": code,
            "name": name,
            "category": category,
            "confirmed": confirmed,
            "note": note,
            "releases": rel_list,
        })

    # 排序：已确认优先，然后手环/手表/其他，最后按名称
    cat_order = {"band": 0, "watch": 1, "other": 2}
    devices.sort(key=lambda d: (not d["confirmed"], cat_order.get(d["category"], 9), d["name"]))

    data = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_repo": repo,
        "device_count": len(devices),
        "release_count": len(releases),
        "asset_count": asset_count,
        "devices": devices,
    }

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"[✓] 写入 {out}: {len(devices)} 设备 / {len(releases)} release / {asset_count} 资产")
    return data


if __name__ == "__main__":
    repo = "hrk666666/firmware-archives-public"
    out = "docs/data.json"
    if "--repo" in sys.argv:
        repo = sys.argv[sys.argv.index("--repo") + 1]
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    build(repo, out)
