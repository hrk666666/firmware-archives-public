#!/usr/bin/env python3
"""批量推送 github-sync 工作区全部文件到公开仓库 main 分支（git Tree API）。
用法: python3 push_tree.py
"""
import json, os, subprocess, sys, urllib.request

REPO = "hrk666666/firmware-archives-public"
BRANCH = "main"
WORKSPACE = "/home/node/.openclaw/workspace-agent-670442f3/github-sync"
SCRIPT_PATH = "/app/skills/github-skill"

TOKEN_FILE = "/home/node/.openclaw/workspace-agent-670442f3/.github_token"


def token():
    # 优先读缓存 token 文件，失败再走凭证托管
    try:
        with open(TOKEN_FILE) as f:
            t = f.read().strip()
        if t:
            return t
    except Exception:
        pass
    out = subprocess.run(
        ["bash", f"{SCRIPT_PATH}/get-token.sh"],
        capture_output=True, text=True, check=True,
        env={**os.environ, "BUILD_ENV": "prod"},
    ).stdout.strip()
    return out

TOK = token()

def api(method, url, payload=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {TOK}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "qclaw-sync")
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return e.code, json.loads(body) if body else {}

# 1. 获取当前 head
status, head = api("GET", f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}")
if status != 200:
    print(f"FAIL get head: {status} {head.get('message')}")
    sys.exit(1)
head_sha = head["object"]["sha"]
print(f"head: {head_sha[:10]}")

# 2. 收集文件
files = []
for root, dirs, names in os.walk(WORKSPACE):
    dirs[:] = [d for d in dirs if d != ".git"]
    for n in sorted(names):
        p = os.path.join(root, n)
        rel = os.path.relpath(p, WORKSPACE)
        files.append((rel, p))
files.sort()
print(f"待推送文件: {len(files)}")

# 3. 创建 blobs
blob_sha = {}
for rel, p in files:
    with open(p, "rb") as f:
        content = f.read()
    is_text = not rel.endswith((".webp", ".png", ".jpg", ".zip"))
    if is_text:
        payload = {"content": content.decode("utf-8"), "encoding": "utf-8"}
    else:
        import base64
        payload = {"content": base64.b64encode(content).decode(), "encoding": "base64"}
    status, r = api("POST", f"https://api.github.com/repos/{REPO}/git/blobs", payload)
    if status != 201:
        print(f"FAIL blob {rel}: {status} {r.get('message')}")
        sys.exit(1)
    blob_sha[rel] = r["sha"]
print(f"blobs: {len(blob_sha)} ok")

# 4. 创建 tree
tree = []
for rel in files:
    rel_path, _ = rel
    tree.append({"path": rel_path, "mode": "100644", "type": "blob", "sha": blob_sha[rel_path]})
status, r = api("POST", f"https://api.github.com/repos/{REPO}/git/trees", {"base_tree": head_sha, "tree": tree})
if status != 201:
    print(f"FAIL tree: {status} {r.get('message')}")
    sys.exit(1)
tree_sha = r["sha"]
print(f"tree: {tree_sha[:10]}")

# 5. 创建 commit
msg = "feat: 固件选择器图形化页面（46 设备/83 release/208 资产）+ 每日数据更新工作流"
status, r = api("POST", f"https://api.github.com/repos/{REPO}/git/commits",
                {"message": msg, "tree": tree_sha, "parents": [head_sha]})
if status != 201:
    print(f"FAIL commit: {status} {r.get('message')}")
    sys.exit(1)
commit_sha = r["sha"]
print(f"commit: {commit_sha[:10]}")

# 6. 更新 ref
status, r = api("PATCH", f"https://api.github.com/repos/{REPO}/git/refs/heads/{BRANCH}",
                {"sha": commit_sha, "force": False})
if status != 200:
    print(f"FAIL ref: {status} {r.get('message')}")
    sys.exit(1)
print(f"✅ 推送成功 {REPO}@{BRANCH} -> {commit_sha}")
