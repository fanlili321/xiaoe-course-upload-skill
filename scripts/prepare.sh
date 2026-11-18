#!/bin/bash
# 一键准备：读飞书文档 → 拆小节 → 下载图片。只读飞书，不改任何东西。
# 用法: prepare.sh "<飞书文档链接>" <工作目录(新目录)>
# 输出: <工作目录>/build/sections.json、images.tsv，<工作目录>/images/NN_xxx.*
set -euo pipefail
URL="$1"; W="$2"
S="$(cd "$(dirname "$0")" && pwd)"
if [ -e "$W" ] && [ -n "$(ls -A "$W" 2>/dev/null)" ]; then
  echo "工作目录 $W 已存在且不为空，请换一个新目录" >&2; exit 1
fi
mkdir -p "$W/build" "$W/images"
lark-cli docs +fetch --as user --doc "$URL" --doc-format markdown > "$W/doc.json"
lark-cli docs +fetch --as user --doc "$URL" --detail with-ids > "$W/ids.json"
python3 "$S/feishu_to_sections.py" "$W/doc.json" "$W/ids.json" "$W/build"
fail=0
while IFS=$'\t' read -r n tok name; do
  [ -z "$tok" ] && continue
  out="$W/images/$(printf %02d "$n")_${name%.*}"
  if ! lark-cli docs +media-download --as user --token "$tok" --output "$out" >/dev/null 2>&1; then
    echo "!! 第 $n 张图片下载失败: $name" >&2; fail=1
  fi
done < "$W/build/images.tsv"
echo "== 已下载图片 =="; ls "$W/images"
[ "$fail" = 0 ] || { echo "有图片下载失败，请检查后再继续" >&2; exit 1; }
