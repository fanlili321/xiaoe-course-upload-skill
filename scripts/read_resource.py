#!/usr/bin/env python3
"""tabbit-cli 结果太大时会返回 resourceId，用这个脚本分页取回完整结果。

用法: read_resource.py <task名> <resourceId> <输出文件>
"""
import json, os, subprocess, sys

task, rid, out = sys.argv[1:4]
cli = os.path.expanduser("~/.local/bin/tabbit-cli")
off, buf = 0, b""
while True:
    r = subprocess.run([cli, "resource", "--task", task, "--resource", rid, "--offset", str(off), "--max-bytes", "32768"], capture_output=True)
    j = json.loads(r.stdout)
    chunk = j.get("data") or j.get("content") or j.get("text")
    if chunk is None:
        sys.exit(f"读取失败: {str(j)[:300]}")
    buf += chunk.encode() if isinstance(chunk, str) else bytes(chunk)
    if j.get("eof") or j.get("nextOffset") is None:
        break
    off = j["nextOffset"]
open(out, "wb").write(buf)
print("saved", len(buf), "bytes →", out)
