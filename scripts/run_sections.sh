#!/bin/bash
# 按顺序新建全部小节；任何一节失败立即停止。已存在的同名小节自动跳过。
# 用法: run_sections.sh <js目录(含 run_0.js...)> "<Tabbit 任务名>"
set -uo pipefail
JS="$1"; TASK="$2"
CLI="$HOME/.local/bin/tabbit-cli"
n=$(ls "$JS"/run_*.js 2>/dev/null | wc -l | tr -d ' ')
[ "$n" -gt 0 ] || { echo "没有找到 run_*.js" >&2; exit 1; }
stamp=$(date +%s)
for ((i=0; i<n; i++)); do
  res=$("$CLI" nodejs --task "$TASK" --request-id "sec-$i-$stamp" --timeout-ms 120000 < "$JS/run_$i.js" 2>/dev/null)
  line=$(printf '%s' "$res" | python3 -c '
import json,sys
j=json.load(sys.stdin); r=j.get("result",{}); v=r.get("value") or {}
if j.get("status")!="succeeded": print("FAIL", (r.get("error") or "")[:300]); sys.exit()
if v.get("err"): print("FAIL", json.dumps(v,ensure_ascii=False)[:300]); sys.exit()
if v.get("skipped"): print("SKIP", v.get("title")); sys.exit()
f=v.get("filled",{})
print(("OK  " if v.get("saved") else "FAIL"), f.get("title"), "| 字", f.get("textLen"), "| 图", f.get("imgs"), "| 表", f.get("tables"), "| 小节数", v.get("sectionsBefore"), "→", v.get("sectionsAfter"))
' 2>&1)
  echo "[$i] $line"
  case "$line" in FAIL*|Traceback*|"") echo "第 $i 节出错，已停止。请检查后再继续（重跑时已建好的小节会自动跳过）。" >&2; exit 1;; esac
done
echo "全部 $n 个小节处理完成"
