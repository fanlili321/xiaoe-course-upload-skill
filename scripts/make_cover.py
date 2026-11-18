#!/usr/bin/env python3
"""生成 750×422 的简洁课程封面（暖黄配色、思源黑体）。

用法: make_cover.py "<课程名>" "<副标题>" <输出.png>
需要 Pillow 和 ~/Library/Fonts/SourceHanSansCN-Heavy.otf / -Medium.otf（没有思源黑体时改用系统 PingFang）。
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

title, sub, out = sys.argv[1:4]
fd = os.path.expanduser("~/Library/Fonts/")
def font(name, size):
    for p in (fd + name, "/System/Library/Fonts/PingFang.ttc"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

W, H = 1500, 844
im = Image.new("RGB", (W, H), (255, 250, 240)); d = ImageDraw.Draw(im)
d.ellipse((-260, -300, 420, 330), fill=(250, 214, 150))
d.ellipse((1180, 560, 1760, 1140), fill=(253, 232, 196))
d.rounded_rectangle((110, 170, W - 110, H - 150), radius=36, outline=(245, 190, 40), width=6, fill=(255, 255, 255))
size = 150 if len(title) <= 6 else max(80, int(900 / len(title)))
B = font("SourceHanSansCN-Heavy.otf", size); M = font("SourceHanSansCN-Medium.otf", 52)
b = d.textbbox((0, 0), title, font=B); d.text(((W - b[2]) / 2, 250 + (150 - size) / 2), title, font=B, fill=(30, 30, 30))
b = d.textbbox((0, 0), sub, font=M); d.text(((W - b[2]) / 2, 470), sub, font=M, fill=(240, 120, 67))
im.resize((750, 422), Image.LANCZOS).save(out)
print("saved", out)
