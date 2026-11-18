#!/usr/bin/env python3
"""飞书文档 → 小鹅通小节 HTML。

用法: feishu_to_sections.py <doc.json(markdown)> <ids.json(with-ids)> <out_dir>
  doc.json : lark-cli docs +fetch --doc-format markdown 的输出
  ids.json : lark-cli docs +fetch --detail with-ids 的输出（用来取图片 token 和评论）
输出:
  out_dir/sections.json  [{title, html}]，图片为 {{IMG:n}} 占位（n 从 1 开始，按全文顺序）
  out_dir/images.tsv     n \t token \t 文件名
并打印每节统计、文档评论、草稿标记，供人工确认。
"""
import html, json, os, re, sys

doc_json, ids_json, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
md = json.load(open(doc_json))["data"]["document"]["content"]
ids = json.load(open(ids_json))["data"]["document"]
xml = ids["content"]

# ---- 草稿标记 & 评论（只报告，不自动处理）----
DRAFT = r"发布前|待改|待修改|仅供示意|TODO|待定|待补|待核对|上线前"
print("== 草稿标记 ==")
for i, line in enumerate(md.split("\n"), 1):
    if re.search(DRAFT, line):
        print(f"  L{i}: {line[:120]}")
comments = (ids.get("reference_map") or {}).get("comments") or {}
print(f"== 文档评论 {len(comments)} 条 ==")
for k, v in comments.items():
    quote = re.search(r"<quote>(.*?)</quote>", v["data"], re.S)
    msgs = re.findall(r"<msg[^>]*>(.*?)</msg>", v["data"], re.S)
    print(f"  {k} | 引用: {(quote.group(1) if quote else '')[:40]} | {' || '.join(msgs)[:160]}")

# ---- 图片 token（按出现顺序）----
imgs = []
for m in re.finditer(r"<img [^>]*>", xml):
    s = m.group(0)
    tok = re.search(r'src="([^"]*)"', s)
    name = re.search(r'name="([^"]*)"', s)
    imgs.append((tok.group(1) if tok else "", name.group(1) if name else "image.png"))
with open(os.path.join(out, "images.tsv"), "w") as f:
    for n, (tok, name) in enumerate(imgs, 1):
        f.write(f"{n}\t{tok}\t{name}\n")

# ---- markdown → html ----
md = re.sub(r"<title>.*?</title>", "", md, flags=re.S)
# 带"发布前删除"的 callout 不搬；其余 callout 保留为普通段落
md = re.sub(r"<callout[^>]*>(.*?)</callout>",
            lambda m: "" if re.search(r"发布前", m.group(1)) else m.group(1), md, flags=re.S)

P = '<p><span style="color: rgb(0, 0, 0); font-size: 16px;">{}</span></p>'
BLANK = "<p><br/></p>"
img_n = [0]

def inline(t):
    t = html.escape(t, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)

def convert(block):
    out, lines, i = [], block.split("\n"), 0
    while i < len(lines):
        l = lines[i]
        if not l.strip():
            i += 1; continue
        if re.match(r"^#{2,6} ", l):
            out.append(f"<h3><strong>{inline(l.split(' ', 1)[1].strip())}</strong></h3>"); i += 1; continue
        if l.startswith("!["):
            img_n[0] += 1
            out.append(f'<p style="text-align:center;">{{{{IMG:{img_n[0]}}}}}</p>'); i += 1; continue
        if l.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[-:| ]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            t = '<table width="100%" border="1" style="border-collapse:collapse;">'
            for r, row in enumerate(rows):
                tag = "th" if r == 0 else "td"
                t += "<tr>" + "".join(f'<{tag} style="border:1px solid #ccc;padding:6px;font-size:14px;">{inline(c)}</{tag}>' for c in row) + "</tr>"
            out.append(t + "</table>"); continue
        if re.match(r"^(- |\d+\. )", l):
            ordered = bool(re.match(r"^\d+\. ", l)); items = []
            while i < len(lines) and re.match(r"^(- |\d+\. )", lines[i]):
                items.append(re.sub(r"^(- |\d+\. )", "", lines[i]).rstrip()); i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f'<li><span style="color: rgb(0, 0, 0); font-size: 16px;">{inline(x)}</span></li>' for x in items) + f"</{tag}>"); continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{2,6} |!\[|\||- |\d+\. )", lines[i]):
            para.append(inline(lines[i].rstrip())); i += 1
        out.append(P.format("<br/>".join(para)))
    return BLANK.join(out)

secs = []
for s in re.split(r"\n(?=# )", md.strip()):
    if not s.startswith("# "):
        if s.strip():
            print("!! 一级标题之前还有内容（未放入任何小节）:", s.strip()[:80])
        continue
    title, body = (s.split("\n", 1) + [""])[:2]
    secs.append({"title": title[2:].strip(), "html": convert(body)})

json.dump(secs, open(os.path.join(out, "sections.json"), "w"), ensure_ascii=False, indent=1)
print("== 小节 ==")
for s in secs:
    text = re.sub(r"<[^>]+>|\{\{IMG:\d+\}\}|\s", "", s["html"])
    print(f"  {s['title']} | 字数≈{len(text)} | 图 {s['html'].count('{{IMG')} | 表 {s['html'].count('<table')}")
if img_n[0] != len(imgs):
    print(f"!! 正文图片数 {img_n[0]} 与文档图片 token 数 {len(imgs)} 不一致，请检查")
