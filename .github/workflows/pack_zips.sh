#!/bin/bash
# pack_zips.sh - 下载全部固件，按系列分组打包成 ≤10 个 zip（中文分级目录），上传到分发 release
# 在 GitHub Actions runner 上运行（磁盘 14GB，流式处理：组内 下载→打包→上传→删除）
set -euo pipefail

REPO_SRC="${REPO_SRC:-hrk666666/firmware-archives-public}"
REPO_DST="${REPO_DST:-hrk666666/firmware-archives-public}"
DATE=$(date +%Y%m%d)
TAG="firmware-zips-$DATE"
NOTES="按系列分组的固件打包（共 10 个 zip，zip 内为中文分级目录：系列/设备/版本/全量包或增量包）。创建时间: $(date '+%F %T UTC')"

# 系列分组：组名(中文) -> 设备代号列表
declare -A GROUPS=(
  ["01_小米手环7与8系列"]="hqbd3.watch.l67 miwear.watch.m66 miwear.watch.m66nfc lchz.watch.m67 lchz.watch.m67ys"
  ["02_小米手环9系列"]="miwear.watch.n66cn miwear.watch.n66nfc miwear.watch.n66tc miwear.watch.n66gl miwear.watch.n67cn"
  ["03_小米手环10系列"]="miwear.watch.o66cn miwear.watch.o66nfc miwear.watch.o66tc miwear.watch.o66lj miwear.watch.p67cn miwear.watch.p67gln miwear.watch.p67tc"
  ["04_红米手环系列"]="mijia.watch.m69 miwear.watch.n69cn mijia.watch.band01"
  ["05_小米手表S1与S3系列"]="mijia.watch.l61 mijia.watch.n62 mijia.watch.n62cg mijia.watch.n62car mijia.watch.n62lte mijia.watch.n62s"
  ["06_小米手表S4与S5系列"]="mijia.watch.o62 mijia.watch.o62m mijia.watch.o62lte miwear.watch.o63 miwear.watch.p62 miwear.watch.p62lte"
  ["07_小米手表Color系列"]="midr.watch.ds"
  ["08_Redmi手表系列"]="lchz.watch.n65 miwear.watch.o65 miwear.watch.o65m miwear.watch.p65"
  ["09_待确认设备_midr系列"]="midr.watch.sports midr.watch.m62s midr.watch.m62a midr.watch.k62 midr.watch.k63 midr.watch.k65"
  ["10_待确认设备_其他"]="mijia.watch.v1 lchz.watch.m65ac lchz.watch.m65s mj1205.motion.ecg"
)

echo "==> 确保分发 release 存在: $TAG"
if ! gh release view "$TAG" -R "$REPO_DST" >/dev/null 2>&1; then
  gh release create "$TAG" -R "$REPO_DST" --title "固件 ZIP 打包 ($DATE)" --notes "$NOTES"
fi

# 代号 -> 中文名 映射（来自 docs/data.json）
python3 - <<'EOF'
import json
d = json.load(open('docs/data.json'))
m = {dev['code']: dev['name'] for dev in d['devices']}
json.dump(m, open('/tmp/devnames.json', 'w'), ensure_ascii=False)
EOF

# 文件名中文化：全量包 / 增量包(含起点版本)
rename_file() {
  local f="$1" code="$2" out
  out=$(python3 - "$f" "$code" <<'EOF'
import re, sys
f, code = sys.argv[1], sys.argv[2]
base = f.split('/')[-1]
m = re.match(r'^.*_v([^_]+)_full_([0-9a-f]+)\.bin$', base)
if m:
    print(f"全量包_v{m.group(1)}_{m.group(2)}.bin"); sys.exit(0)
m = re.match(r'^.*_v([^_]+)_from_v([^_]+)_incremental_([0-9a-f]+)\.bin$', base)
if m:
    print(f"增量包_v{m.group(1)}_从v{m.group(2)}_{m.group(3)}.bin"); sys.exit(0)
print(base)
EOF
)
  echo "$out"
}

mkdir -p tmp
total=${#GROUPS[@]}
i=0
for group in "${!GROUPS[@]}"; do
  i=$((i+1))
  echo "==> [$i/$total] 打包 $group"
  mkdir -p "tmp/$group"
  for code in ${GROUPS[$group]}; do
    devname=$(python3 -c "import json; print(json.load(open('/tmp/devnames.json')).get('$code', '$code'))")
    devdir="tmp/$group/${devname}_${code}"
    mkdir -p "$devdir"
    # 该设备的所有固件 tag
    tags=$(gh release list -R "$REPO_SRC" --limit 300 --json tagName -q '.[].tagName' | grep "^firmware-$code-" || true)
    for tag in $tags; do
      ver=$(echo "$tag" | sed -E "s/^firmware-$code-//")
      mkdir -p "$devdir/$ver"
      gh release download "$tag" -R "$REPO_SRC" --dir "$devdir/$ver" --clobber
      # 文件名中文化
      for f in "$devdir/$ver"/*.bin; do
        [ -e "$f" ] || continue
        newname=$(rename_file "$f" "$code")
        [ "$newname" != "$(basename "$f")" ] && mv "$f" "$(dirname "$f")/$newname"
      done
    done
  done
  # zip 保留 系列/设备/版本/文件 中文目录层次
  (cd tmp && zip -qr "../$group.zip" "$group")
  echo "    -> $group.zip ($(du -h "$group.zip" | cut -f1))"
  gh release upload "$TAG" -R "$REPO_DST" "$group.zip" --clobber
  rm -rf "tmp/$group" "$group.zip"
done
echo "==> 全部完成: $total 个 zip 已上传到 $TAG"
