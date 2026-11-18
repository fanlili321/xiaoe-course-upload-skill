#!/usr/bin/env python3
"""回读核对：比较 final.json（应写入的内容）和 verify.js 的结果。

用法: compare.py <final.json> <verify.json>
  verify.json 可以是 tabbit-cli 的完整输出（含 result.value），也可以是 read_resource.py 取回的结果。
"""
import html, json, re, sys

exp = json.load(open(sys.argv[1]))
v = json.load(open(sys.argv[2]))
if isinstance(v, dict) and "result" in v:
    v = v["result"].get("value", v["result"])
if isinstance(v, dict) and "value" in v and "sections" not in v:
    v = v["value"]
print(v.get("header", ""), "| 小节数", v.get("n"))
norm = lambda s: re.sub(r"\s", "", s)
ok_all = len(exp) == len(v["sections"])
if not ok_all:
    print(f"!! 小节数不一致：应为 {len(exp)}，后台为 {len(v['sections'])}")
for e, g in zip(exp, v["sections"]):
    text = html.unescape(re.sub(r"<[^>]+>", "", e["html"]))
    ei = re.findall(r'<img src="([^"]+)"', e["html"])
    ok_t, ok_x, ok_i = e["title"] == g["title"], norm(text) == norm(g["text"]), ei == g["imgs"]
    ok = ok_t and ok_x and ok_i
    ok_all &= ok
    print(("OK  " if ok else "DIFF"), g["title"], f"| 字 {len(norm(g['text']))} | 图 {len(g['imgs'])} | 表 {g['tables']}",
          "" if ok else f"| 标题{ok_t} 正文{ok_x} 图片{ok_i}")
    if not ok_x:
        a, b = norm(text), norm(g["text"])
        k = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
        print("   首个差异:", a[max(0, k - 20):k + 30], "||", b[max(0, k - 20):k + 30])
print("全部一致" if ok_all else "存在差异，请检查")
sys.exit(0 if ok_all else 1)
