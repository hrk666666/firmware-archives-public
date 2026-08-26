#!/usr/bin/env python3
"""只推送指定文件到公开仓库 main 分支（git Tree API）。
用法: python3 push_selected.py <rel_path> [<rel_path> ...]
"""
import json, os, subprocess, sys, urllib.request, time

REPO = "hrk666666/firmware-archives-public"
BRANCH = "main"
WORKSPACE = "/home/node/.openclaw/workspace-agent-670442f3/github-sync"
SCRIPT_PATH = "/app/skills/github-skill"
TOKEN_FILE = "/home/node/.openclaw/workspace-agent-670442f3/.github_token"

def token():
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

def api(method, url, payload=None, retries=4):
    for attempt in range(retries):
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
            with urllib.request.urlopen(req, data=data, timeout=60) as resp:
                body = resp.read().decode()
                return resp.status, json.loads(body) if body else {}
        except Exception as e:
            print(f"  retry {attempt+1}/{retries} {method} {url.split('/')[-1]}: {e}")
            time.sleep(3 * (attempt + 1))
    return 0, {"message": "max retries"}

selected = sys.argv[1:]
msg = "update: push selected files"
if selected and selected[0] == "--msg":
    msg = selected[1]
    selected = selected[2:]
if not selected:
    print("usage: push_selected.py [--msg <commit message>] <rel_path> [...]")
    sys.exit(1)

status, head = api("GET", f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}")
if status != 200:
    print(f"FAIL get head: {status} {head.get('message')}")
    sys.exit(1)
head_sha = head["object"]["sha"]
print(f"head: {head_sha[:10]}")

blob_sha = {}
for rel in selected:
    p = os.path.join(WORKSPACE, rel)
    if not os.path.exists(p):
        print(f"SKIP missing {rel}")
        continue
    with open(p, "rb") as f:
        content = f.read()
    if rel.endswith((".webp", ".png", ".jpg", ".zip")):
        import base64
        payload = {"content": base64.b64encode(content).decode(), "encoding": "base64"}
    else:
        payload = {"content": content.decode("utf-8"), "encoding": "utf-8"}
    status, r = api("POST", f"https://api.github.com/repos/{REPO}/git/blobs", payload)
    if status != 201:
        print(f"FAIL blob {rel}: {status} {r.get('message')}")
        sys.exit(1)
    blob_sha[rel] = r["sha"]
    print(f"blob ok: {rel} ({len(content)}B)")

tree = [{"path": rel, "mode": "100644", "type": "blob", "sha": blob_sha[rel]} for rel in selected if rel in blob_sha]
status, r = api("POST", f"https://api.github.com/repos/{REPO}/git/trees", {"base_tree": head_sha, "tree": tree})
if status != 201:
    print(f"FAIL tree: {status} {r.get('message')}")
    sys.exit(1)
tree_sha = r["sha"]
print(f"tree: {tree_sha[:10]}")

msg = msg
status, r = api("POST", f"https://api.github.com/repos/{REPO}/git/commits",
                {"message": msg, "tree": tree_sha, "parents": [head_sha]})
if status != 201:
    print(f"FAIL commit: {status} {r.get('message')}")
    sys.exit(1)
commit_sha = r["sha"]
print(f"commit: {commit_sha[:10]}")

status, r = api("PATCH", f"https://api.github.com/repos/{REPO}/git/refs/heads/{BRANCH}",
                {"sha": commit_sha, "force": False})
if status != 200:
    print(f"FAIL ref: {status} {r.get('message')}")
    sys.exit(1)
print(f"OK 推送成功 {REPO}@{BRANCH} -> {commit_sha}")
