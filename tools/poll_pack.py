#!/usr/bin/env python3
"""轮询 pack-zips Actions 运行状态直到完成。"""
import json, subprocess, sys, time, os

TOKEN = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_TOKEN", "")
RUN_ID = "32729486621"
BASE = "https://api.github.com/repos/hrk666666/firmware-archives-public"

def gh(path):
    r = subprocess.run(["curl", "-sS", "-H", f"Authorization: Bearer {TOKEN}",
                        "-H", "Accept: application/vnd.github+json", BASE + path],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}

deadline = time.time() + 12 * 60
while time.time() < deadline:
    run = gh(f"/actions/runs/{RUN_ID}")
    rel = gh("/releases/tags/firmware-zips-20260824")
    assets = rel.get("assets", [])
    status = run.get("status")
    concl = run.get("conclusion") or ""
    print(f"[{time.strftime('%H:%M:%S')}] run={status} {concl} zip={len(assets)}", flush=True)
    if status == "completed":
        print("DONE conclusion=" + concl, flush=True)
        sys.exit(0)
    time.sleep(20)
print("TIMEOUT", flush=True)
sys.exit(1)
