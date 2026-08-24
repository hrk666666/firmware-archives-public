#!/bin/bash
# pack_zips.sh - 下载全部固件，按系列分组打包成 10 个 zip，上传到分发 release
# 要点：
#   - zip 文件名为 ASCII（GitHub 资产名不支持中文，会损坏成乱码）
#   - zip 内部目录为中文分级目录：系列/设备/版本/全量包或增量包
#   - 每组源数据 <2GB（GitHub 单资产上限 2GB），流式处理：组内 下载→打包→上传→删除
# 在 GitHub Actions runner 上运行（磁盘 14GB）
set -euo pipefail

REPO_SRC="${REPO_SRC:-hrk666666/firmware-archives-public}"
REPO_DST="${REPO_DST:-hrk666666/firmware-archives-public}"
DATE=$(date +%Y%m%d)
TAG="firmware-zips-$DATE"
NOTES="按系列分组的固件打包（共 10 个 zip，zip 内为中文分级目录：系列/设备/版本/全量包或增量包）。创建时间: $(date '+%F %T UTC')"

# 分组：key(ASCII 文件名) -> 中文目录名
declare -A PACK_LABELS=(
  ["01_band7_8"]="01_小米手环7与8系列"
  ["02_band9"]="02_小米手环9系列"
  ["03_band10"]="03_小米手环10系列"
  ["04_band10pro"]="04_小米手环10Pro系列"
  ["05_watch_s1s3color"]="05_小米手表S1_S3_Color系列"
  ["06_watch_s4"]="06_小米手表S4系列"
  ["07_watch_s5"]="07_小米手表S5系列"
  ["08_redmi_watch"]="08_Redmi手表系列"
  ["09_midr_misc"]="09_待确认设备_midr系列"
  ["10_other"]="10_待确认设备_其他"
)

# 分组：key -> 设备代号列表（每组合计源大小 <2GB）
declare -A PACK_GROUPS=(
  ["01_band7_8"]="hqbd3.watch.l67 miwear.watch.m66 miwear.watch.m66nfc lchz.watch.m67 lchz.watch.m67ys"
  ["02_band9"]="miwear.watch.n66cn miwear.watch.n66nfc miwear.watch.n66tc miwear.watch.n66gl miwear.watch.n67cn"
  ["03_band10"]="miwear.watch.o66cn miwear.watch.o66nfc miwear.watch.o66tc miwear.watch.o66lj"
  ["04_band10pro"]="miwear.watch.p67cn miwear.watch.p67gln miwear.watch.p67tc"
  ["05_watch_s1s3color"]="mijia.watch.l61 mijia.watch.n62 mijia.watch.n62cg mijia.watch.n62car mijia.watch.n62lte mijia.watch.n62s midr.watch.ds"
  ["06_watch_s4"]="mijia.watch.o62 mijia.watch.o62m mijia.watch.o62lte miwear.watch.o63"
  ["07_watch_s5"]="miwear.watch.p62 miwear.watch.p62lte"
  ["08_redmi_watch"]="lchz.watch.n65 miwear.watch.o65 miwear.watch.o65m miwear.watch.p65"
  ["09_midr_misc"]="midr.watch.sports midr.watch.m62s midr.watch.m62a midr.watch.k62 midr.watch.k63 midr.watch.k65"
  ["10_other"]="mijia.watch.v1 lchz.watch.m65ac lchz.watch.m65s mj1205.motion.ecg"
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
total=${#PACK_GROUPS[@]}
i=0
for key in "${!PACK_GROUPS[@]}"; do
  i=$((i+1))
  group="${PACK_LABELS[$key]}"
  echo "==> [$i/$total] 打包 $group (zip: $key.zip)"
  mkdir -p "tmp/$group"
  for code in ${PACK_GROUPS[$key]}; do
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
  (cd tmp && zip -qr "../$key.zip" "$group")
  echo "    -> $key.zip ($(du -h "$key.zip" | cut -f1))"
  gh release upload "$TAG" -R "$REPO_DST" "$key.zip" --clobber
  rm -rf "tmp/$group" "$key.zip"
done
echo "==> 全部完成: $total 个 zip 已上传到 $TAG"
