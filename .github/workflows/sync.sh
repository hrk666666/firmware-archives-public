#!/usr/bin/env bash
# ============================================================
# 固件自动同步脚本
# 从上游 MiWearFirmwareArchives 同步所有 Releases（固件）到本仓库
# 幂等：已存在的 tag 跳过，新增的自动复制
# ============================================================
set -euo pipefail

UPSTREAM="${UPSTREAM:-AstralSightStudios/MiWearFirmwareArchives}"
REPO="${GITHUB_REPOSITORY:?}"
TOKEN="${GH_TOKEN:?}"
API="https://api.github.com"
UPLOADS="https://uploads.github.com"

echo "== 同步 $UPSTREAM → $REPO =="

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

# ---- 1. 获取上游全部 releases（翻页） ----
upstream_json="$tmpdir/upstream.json"
: > "$upstream_json"
page=1
while :; do
  body="$(curl -fsSL -H "Authorization: Bearer $TOKEN" "$API/repos/$UPSTREAM/releases?per_page=100&page=$page")"
  count="$(echo "$body" | jq 'length')"
  [ "$count" -eq 0 ] && break
  echo "$body" | jq -c '.[]' >> "$upstream_json"
  page=$((page + 1))
  [ "$count" -lt 100 ] && break
done
total="$(wc -l < "$upstream_json")"
echo "上游 releases 总数: $total"

# ---- 2. 本仓库已有 tags ----
existing_tags="$(curl -fsSL -H "Authorization: Bearer $TOKEN" "$API/repos/$REPO/releases?per_page=100" | jq -r '.[].tag_name' 2>/dev/null || true)"

# ---- 3. 逐条同步 ----
synced=0
skipped=0
while IFS= read -r rel; do
  tag="$(echo "$rel" | jq -r '.tag_name')"
  if echo "$existing_tags" | grep -qx "$tag"; then
    skipped=$((skipped + 1))
    continue
  fi
  echo "== 发现新 release: $tag"
  rel_name="$(echo "$rel" | jq -r '.name // ""')"
  rel_body="$(echo "$rel" | jq -r '.body // ""')"
  # 创建 release
  rel_id="$(curl -fsSL -X POST -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
    "$API/repos/$REPO/releases" \
    -d "$(jq -nc --arg t "$tag" --arg n "$rel_name" --arg b "$rel_body" '{tag_name:$t, name:$n, body:$b}')" | jq -r '.id')"
  echo "  release 已创建 (id=$rel_id)"
  # 下载并上传 assets
  while IFS= read -r asset; do
    aname="$(echo "$asset" | jq -r '.name')"
    asize="$(echo "$asset" | jq -r '.size')"
    echo "  下载: $aname ($asize bytes)"
    curl -fsSL -o "$tmpdir/$aname" "https://github.com/$UPSTREAM/releases/download/$tag/$aname"
    got="$(stat -c %s "$tmpdir/$aname")"
    if [ "$got" != "$asize" ]; then
      echo "  !! 大小不符 ($got != $asize)，跳过该 asset" >&2
      rm -f "$tmpdir/$aname"
      continue
    fi
    echo "  上传: $aname"
    curl -fsSL -X POST -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/octet-stream" \
      --data-binary "@$tmpdir/$aname" \
      "$UPLOADS/repos/$REPO/releases/$rel_id/assets?name=$aname" > /dev/null
    rm -f "$tmpdir/$aname"
  done < <(echo "$rel" | jq -c '.assets[]')
  synced=$((synced + 1))
done < "$upstream_json"

echo "== 完成: 新增 $synced / 已存在跳过 $skipped =="
