#!/usr/bin/env python3
"""把要上传的图片复制成统一命名，便于在小鹅通素材库里定位。

用法: prepare_upload.py <images_dir> <upload_dir> <课程名> [--cover 封面.png] [--replace N=路径 ...]
  images_dir 里的文件以两位序号开头（01_xxx.png），与 sections.json 的 {{IMG:n}} 对应。
  --replace 10=fixed/10.png 用改好的图替换第 10 张。
输出: upload_dir/<课程名>_00封面.png、<课程名>_01.png ...，以及 upload_dir/list.json（绝对路径列表，供 Tabbit setFiles 使用）。
"""
import json, os, shutil, sys

args = sys.argv[1:]
src_dir, dst_dir, name = args[:3]
cover, repl = None, {}
i = 3
while i < len(args):
    if args[i] == "--cover":
        cover = args[i + 1]; i += 2
    elif args[i] == "--replace":
        n, p = args[i + 1].split("=", 1); repl[int(n)] = p; i += 2
    else:
        sys.exit(f"未知参数: {args[i]}")

os.makedirs(dst_dir, exist_ok=True)
if os.listdir(dst_dir):
    sys.exit(f"{dst_dir} 不是空目录，请换一个新目录")
out = []
if cover:
    d = os.path.join(dst_dir, f"{name}_00封面{os.path.splitext(cover)[1]}")
    shutil.copy(cover, d); out.append(os.path.abspath(d))
files = sorted(f for f in os.listdir(src_dir) if f[:2].isdigit())
for f in files:
    n = int(f[:2]); src = repl.get(n, os.path.join(src_dir, f))
    d = os.path.join(dst_dir, f"{name}_{n:02d}{os.path.splitext(src)[1]}")
    shutil.copy(src, d); out.append(os.path.abspath(d))
json.dump(out, open(os.path.join(dst_dir, "list.json"), "w"), ensure_ascii=False)
for p in out:
    print(os.path.basename(p), os.path.getsize(p))
print(f"共 {len(out)} 个文件（素材库一次最多 100 个）")
