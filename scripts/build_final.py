#!/usr/bin/env python3
"""把 sections.json 里的 {{IMG:n}} 换成小鹅通素材库地址。

用法: build_final.py <sections.json> <urls.json> <final.json> [--strip-lesson-no]
  urls.json: {"<课程名>_01.png": "https://...", ...}（文件名里的两位序号 = n）
  --strip-lesson-no: 去掉标题开头的"第 X 课 / 第X章"
"""
import json, re, sys

sec_p, url_p, out_p = sys.argv[1:4]
strip = "--strip-lesson-no" in sys.argv
secs = json.load(open(sec_p)); urls = json.load(open(url_p))
byn = {}
for k, v in urls.items():
    m = re.search(r"_(\d{2})(?:\.\w+)$", k)
    if m and int(m.group(1)) > 0:
        byn[int(m.group(1))] = v.split("?")[0]

missing = set()
def img(m):
    n = int(m.group(1))
    if n not in byn:
        missing.add(n); return m.group(0)
    return f'<img src="{byn[n]}" width="100%" height="auto"/>'

out = []
for s in secs:
    t = re.sub(r"^第 ?(\d+) ?课 ", r"第\1课 ", s["title"])
    if strip:
        t = re.sub(r"^第 ?\d+ ?[课章节][：:\s]*", "", t)
    h = re.sub(r"\{\{IMG:(\d+)\}\}", img, s["html"])
    out.append({"title": t, "html": h})
    print(f"{t} | 图 {h.count('<img')} | 表 {h.count('<table')}")
if missing:
    sys.exit(f"缺少这些图片的地址: {sorted(missing)}")
json.dump(out, open(out_p, "w"), ensure_ascii=False)
