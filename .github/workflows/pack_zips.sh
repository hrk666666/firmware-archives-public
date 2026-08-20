#!/bin/bash
# pack_zips.sh - 从公开镜像仓库下载全部固件，按设备打包 zip，上传到临时分发 release
# 在 GitHub Actions runner 上运行（磁盘 14GB，流式处理：每设备 下载→打包→上传→删除）
set -euo pipefail

REPO_SRC="${REPO_SRC:-hrk666666/firmware-archives-public}"   # 下载源
REPO_DST="${REPO_DST:-hrk666666/firmware-archives-public}"   # 上传目标（临时分发）
DATE=$(date +%Y%m%d)
TAG="firmware-zips-$DATE"
NOTES="临时打包分发（按设备分组 zip，共 46 个）。下载完成后请删除本 Release。创建时间: $(date '+%F %T UTC')"

echo "==> 确保分发 release 存在: $TAG"
if ! gh release view "$TAG" -R "$REPO_DST" >/dev/null 2>&1; then
  gh release create "$TAG" -R "$REPO_DST" --title "固件 ZIP 打包包 ($DATE)" --notes "$NOTES"
fi

echo "==> 枚举上游 release tags"
gh release list -R "$REPO_SRC" --limit 200 --json tagName -q '.[].tagName' > /tmp/tags.txt
echo "    tags: $(wc -l < /tmp/tags.txt)"

# 按设备分组（tag 格式: firmware-设备代号-版本-hash，设备代号内无 '-'）
# 跳过分发用的 firmware-zips-* release，避免把 zip 也当固件源
if [[ -n "${FILTER_TAGS:-}" ]]; then
  echo "    tag 过滤: $FILTER_TAGS"
fi
declare -A groups
while read -r tag; do
  [[ "$tag" == firmware-zips-* ]] && continue
  dev=$(echo "$tag" | sed -E 's/^firmware-([^-]+)-.*/\1/')
  groups["$dev"]="${groups[$dev]:-} $tag"
done < /tmp/tags.txt
echo "    设备数: ${#groups[@]}"

mkdir -p tmp
total=${#groups[@]}
i=0
for dev in "${!groups[@]}"; do
  i=$((i+1))
  echo "==> [$i/$total] 打包 $dev"
  mkdir -p "tmp/$dev"
  for tag in ${groups[$dev]}; do
    ver=$(echo "$tag" | sed -E 's/^firmware-[^-]+-//')
    mkdir -p "tmp/$dev/$ver"
    gh release download "$tag" -R "$REPO_SRC" --dir "tmp/$dev/$ver" --clobber
  done
  # zip 保留 设备/版本/文件 目录层次
  (cd tmp && zip -qr "../$dev.zip" "$dev")
  echo "    -> $dev.zip ($(du -h "$dev.zip" | cut -f1))"
  gh release upload "$TAG" -R "$REPO_DST" "$dev.zip" --clobber
  rm -rf "tmp/$dev" "$dev.zip"
  echo "    -> 已上传并清理"
done

echo "==> 完成。所有 zip 已上传到: https://github.com/$REPO_DST/releases/tag/$TAG"
