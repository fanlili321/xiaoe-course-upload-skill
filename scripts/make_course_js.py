#!/usr/bin/env python3
"""生成"新建课程"用的两个 Tabbit 程序（只新建，不碰已有课程）。

用法: make_course_js.py <课程名> <upload/list.json> <out_dir>
输出:
  out_dir/create_course.js  检查同名课程 → 新建 → 填名称 → 暂不上架 → 上传全部图片 → 取回地址 → 选封面。不保存。
                            返回 {urls, cover, form}，把 urls 存成 build/urls.json。
  out_dir/save_course.js    再核对一次表单（名称/免费/暂不上架/封面）→ 保存 → 返回 courseId。
两个程序必须在同一个 Tabbit 任务、同一个标签页里先后运行。
"""
import json, os, sys

name, list_p, out = sys.argv[1:4]
files = json.load(open(list_p))
if not files or len(files) > 100:
    sys.exit("图片数量必须在 1~100 之间")
cover = next((os.path.basename(f) for f in files if "_00封面" in os.path.basename(f)), None)
os.makedirs(out, exist_ok=True)

CREATE = r"""
const NAME = __NAME__;
const FILES = __FILES__;
const COVER = __COVER__;
const PREFIX = NAME + "_";
const LIST = "https://admin.xiaoe-tech.com/t/course/camp_pro/list#/list";
// 0) 同名课程检查：已存在就停下，绝不覆盖
await page.goto(LIST, {waitUntil: "domcontentloaded"});
await page.waitForTimeout(3000);
const search = page.getByPlaceholder(/搜索|名称|课程/).first();
await search.fill(NAME); await search.press("Enter");
await page.waitForTimeout(3500);
const same = await page.evaluate((n) => [...document.querySelectorAll('tr')].some(r => r.innerText.split(/\s+/).includes(n)), NAME);
if (same) return {err: "已存在同名课程「" + NAME + "」，已停止。请换课程名，或让用户决定。"};
// 1) 新建
await page.locator('button:visible', {hasText: /^新建$/}).first().click();
await page.getByPlaceholder("建议14字内").first().waitFor({timeout: 20000});
await page.waitForTimeout(2500);
const closeWarn = async () => {   // 只关提示（点 ×），不点「去开启」
  const warn = page.locator('.ss-message-box-wrapper__warning');
  if (await warn.isVisible().catch(() => false)) { await warn.locator('.ss-message-close').click(); await page.waitForTimeout(800); }
};
await closeWarn();
await page.locator('label', {hasText: /^\s*暂不上架\s*$/}).first().click();
await page.locator('label', {hasText: /^\s*免费\s*$/}).first().click();
// 2) 打开素材库并上传（「添加图片」是封面上的悬停遮罩按钮，要先悬停）
await page.evaluate(() => window.scrollTo(0, 0));
await closeWarn();
const sel = page.locator('.ss-material-selection:visible').first();
await sel.hover();
await page.waitForTimeout(500);
await sel.locator('.ss-mask-btn').first().click({force: true});
const lib = page.locator('.ss-dialog:visible', {hasText: "选择图片"}).first();
await lib.waitFor({timeout: 10000});
await page.waitForTimeout(1500);
// 每页 50 条（最新在前），按文件名前缀找图
await lib.locator('.ss-pagination-options-size .ss-select').click();
await page.waitForTimeout(800);
await page.locator('.ss-select-dropdown:visible li', {hasText: "50 条"}).first().click();
await page.waitForTimeout(3000);
const want = new Set(FILES.map(f => f.split('/').pop()));
const collect = async () => {
  const urls = {};
  for (let p = 0; p < 3 && Object.keys(urls).length < want.size; p++) {
    const got = await lib.evaluate((root, prefix) => [...root.querySelectorAll('tr')].map(r => { const t = r.innerText; const k = t.indexOf(prefix); const i = r.querySelector('img'); if (k < 0 || !i) return null; return [t.slice(k).split(/\s/)[0], i.src.split('?')[0]]; }).filter(Boolean), PREFIX);
    for (const [k, v] of got) if (want.has(k) && !urls[k]) urls[k] = v;
    if (Object.keys(urls).length >= want.size) break;
    const next = lib.locator('.ss-pagination li[class*=next], .ss-pagination button[class*=next]').first();
    if (!(await next.count())) break;
    await next.click(); await page.waitForTimeout(2500);
  }
  return urls;
};
// 防重复上传：同名图片都已在素材库（例如上次跑到一半）就直接用
let urls = await collect();
const uploaded = Object.keys(urls).length < want.size;
if (uploaded) {
await lib.getByText("上传图片", {exact: true}).first().click();
const up = page.locator('.ss-dialog:visible', {hasText: "确认上传"}).last();
await up.waitFor({timeout: 10000});
const fcP = page.waitForEvent('filechooser', {timeout: 8000});
await up.getByText("点击选择图片", {exact: false}).first().click();
await (await fcP).setFiles(FILES);
await page.waitForTimeout(2000);
await up.getByText(/确认上传/).last().click();
const upDone = page.locator('.ss-dialog:visible', {hasText: "上传成功"}).last();
let ok = false, txt = "";
for (let t = 0; t < 90; t++) {
  await page.waitForTimeout(2000);
  txt = (await upDone.innerText().catch(() => "")).replace(/\s+/g, " ");
  const m = txt.match(/共\s*(\d+)\s*个\s*上传成功\s*(\d+)/);
  if (m && +m[1] === FILES.length && +m[2] === FILES.length) { ok = true; break; }
  if (/失败/.test(txt) && !/上传失败或缓慢/.test(txt)) break;
}
if (!ok) return {err: "图片没有全部上传成功", detail: txt.slice(0, 300)};
await upDone.locator('[class*=close]').first().click();
await page.waitForTimeout(3000);
// 3) 取回地址
urls = await collect();
}
const missing = [...want].filter(k => !urls[k]);
if (missing.length) return {err: "素材库里没找到这些图的地址", missing, urls};
// 4) 选封面
if (COVER) {
  await lib.locator('.ss-pagination li', {hasText: /^1$/}).first().click().catch(() => {});
  await page.waitForTimeout(1500);
  const row = lib.locator('tr').filter({hasText: COVER}).first();
  await row.locator('label.ss-radio').click();
  await lib.locator('button', {hasText: /^\s*确认\s*$/}).last().click();
  await page.waitForTimeout(2000);
} else {
  await lib.locator('button', {hasText: /^\s*取消\s*$/}).last().click().catch(() => {});
}
// 5) 名称放在最后填（页面初始化时会重置输入框），填完读回核对
const nameInput = page.getByPlaceholder("建议14字内").first();
await nameInput.fill(NAME);
await page.waitForTimeout(500);
if ((await nameInput.inputValue()) !== NAME) { await nameInput.click(); await nameInput.fill(""); await nameInput.pressSequentially(NAME, {delay: 30}); await page.waitForTimeout(500); }
const form = await page.evaluate(() => { const r = {}; document.querySelectorAll('input[type=radio]').forEach(i => { const t = (i.closest('label')?.innerText || '').trim(); if (['免费','立即上架','暂不上架'].includes(t)) r[t] = i.checked; }); return {name: document.querySelector('input[placeholder="建议14字内"]').value, radios: r, cover: [...document.querySelectorAll('.ss-material-selection img')].filter(i => i.offsetParent).map(i => i.src.split('?')[0])}; });
return {urls, cover: COVER ? urls[COVER] : null, form, uploadedThisRun: uploaded, note: "尚未保存。核对后运行 save_course.js"};
"""

SAVE = r"""
const NAME = __NAME__;
const NEED_COVER = __NEED_COVER__;
if (!page.url().includes('/camp_pro/edit/new')) return {err: "当前不在新建课程页面，已停止"};
const st = await page.evaluate(() => { const r = {}; document.querySelectorAll('input[type=radio]').forEach(i => { const t = (i.closest('label')?.innerText || '').trim(); if (['免费','立即上架','暂不上架'].includes(t)) r[t] = i.checked; }); return {name: document.querySelector('input[placeholder="建议14字内"]').value, radios: r, cover: [...document.querySelectorAll('.ss-material-selection img')].filter(i => i.offsetParent).map(i => i.src.split('?')[0])}; });
const problems = [];
if (st.name !== NAME) problems.push("名称不对: " + st.name);
if (!st.radios['暂不上架']) problems.push("上架设置不是「暂不上架」");
if (!st.radios['免费']) problems.push("售卖方式不是「免费」");
// 封面：上传的图在店铺自己的素材域名下（wechatapppro / xiaoeknow），系统默认图在 commonresource 下
if (NEED_COVER && !st.cover.some(u => /wechatapppro/.test(u) && !/commonresource/.test(u))) problems.push("封面还是系统默认图，没有换成上传的封面");
if (problems.length) return {err: "表单核对未通过，未保存", problems, st};
await page.locator('button:visible', {hasText: /^\s*保存\s*$/}).last().click();
for (let t = 0; t < 20 && !page.url().includes('/camp_pro/detail/'); t++) await page.waitForTimeout(1000);
const m = page.url().match(/course_[A-Za-z0-9]+/);
if (!m) return {err: "保存后没有跳到课程详情页，请人工查看", url: page.url()};
const head = (await page.locator('body').innerText()).match(/小节数:[\s\S]{0,60}(免费|付费)/)?.[0]?.replace(/\s+/g, ' ');
return {courseId: m[0], head};
"""

def lit(x):
    return json.dumps(x, ensure_ascii=False)

open(os.path.join(out, "create_course.js"), "w").write(
    CREATE.replace("__NAME__", lit(name)).replace("__FILES__", lit(files)).replace("__COVER__", lit(cover)))
open(os.path.join(out, "save_course.js"), "w").write(
    SAVE.replace("__NAME__", lit(name)).replace("__NEED_COVER__", lit(bool(cover))))
print(f"生成 create_course.js 和 save_course.js（{len(files)} 张图，封面: {cover or '无，需人工在后台选封面'}）")
