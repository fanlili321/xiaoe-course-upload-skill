#!/usr/bin/env python3
"""为每个小节生成 Tabbit 程序：在指定课程下新建图文小节、填标题和正文、保存。

用法: make_tabbit_js.py <final.json> <course_id> <out_dir>
输出: out_dir/run_<i>.js（i 从 0 开始，按小节顺序逐个运行）和 out_dir/verify.js（回读全部小节）
运行: ~/.local/bin/tabbit-cli nodejs --task "小鹅通上传" --request-id run-<i> --timeout-ms 120000 < run_<i>.js
"""
import json, os, sys

final_p, course_id, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
secs = json.load(open(final_p))
DETAIL = f"https://admin.xiaoe-tech.com/t/course/camp_pro/detail/{course_id}"

RUN = r"""
const S = __SECTION__;
const DETAIL = __DETAIL__;
if (!page.url().startsWith(DETAIL)) await page.goto(DETAIL, {waitUntil: "domcontentloaded"});
await page.locator('button:visible', {hasText: "添加小节"}).first().waitFor({timeout: 20000});
await page.waitForTimeout(1500);
// 0) 防重复：目录里已有同名小节就跳过（中途失败后重跑也不会建出重复小节）
const exists = await page.evaluate((t) => [...document.querySelectorAll('*')].some(e => e.childElementCount === 0 && e.offsetParent && e.textContent.trim() === t), S.title);
if (exists) return {skipped: true, reason: "已有同名小节，未重复创建", title: S.title};
const before = await page.locator('span:text-is("编辑"):visible').count();
// 1) 添加小节 → 单个添加 → 悬停「图文」→ 新建（菜单是悬停出现的，必须在同一个程序里连续操作）
await page.locator('button:visible', {hasText: "添加小节"}).first().click();
const item = page.locator('li.ss-dropdown-item:visible', {hasText: "单个添加"}).first();
await item.waitFor({timeout: 5000}); await item.click();
const dr = page.locator('.ss-drawer:visible', {hasText: "添加小节"}).first();
await dr.waitFor({timeout: 8000});
await dr.getByText("图文", {exact: true}).first().hover();
const nb = dr.locator('.action__btn__entity__text:visible', {hasText: /^新建$/}).first();
await nb.waitFor({timeout: 5000}); await nb.click();
// 2) 等编辑器 iframe 和 UEditor 就绪
let f = null;
for (let t = 0; t < 40 && !f; t++) { f = page.frames().find(fr => fr.url().includes('/text/edit/new')); if (!f) await page.waitForTimeout(500); }
if (!f) return {err: '没有出现图文编辑器'};
await f.waitForFunction(() => { try { return !!window.UE.instants['ueditorInstant0'].body; } catch (e) { return false; } }, null, {timeout: 30000});
// 3) 填标题和正文
await f.locator('input[placeholder="建议14字内"]').first().fill(S.title);
await f.evaluate(h => { const e = window.UE.instants['ueditorInstant0']; e.setContent(h); e.fireEvent('contentchange'); }, S.html);
await page.waitForTimeout(1000);
const filled = await f.evaluate(() => { const e = window.UE.instants['ueditorInstant0']; const d = document.createElement('div'); d.innerHTML = e.getContent(); return {title: document.querySelector('input[placeholder="建议14字内"]').value, textLen: d.innerText.length, imgs: d.querySelectorAll('img').length, tables: d.querySelectorAll('table').length}; });
const expImgs = (S.html.match(/<img /g) || []).length;
if (filled.title !== S.title || filled.imgs !== expImgs) return {err: '填写结果与预期不符，未保存', filled, expImgs};
// 4) 保存并等抽屉关闭
await f.locator('button:visible', {hasText: /^\s*保存\s*$/}).last().click();
let saved = false;
for (let t = 0; t < 30; t++) { await page.waitForTimeout(1000); if (!page.frames().some(fr => fr.url().includes('/text/edit/new'))) { saved = true; break; } }
await page.waitForTimeout(1500);
const after = await page.locator('span:text-is("编辑"):visible').count();
return {filled, saved, sectionsBefore: before, sectionsAfter: after};
"""

VERIFY = r"""
const DETAIL = __DETAIL__;
await page.goto(DETAIL, {waitUntil: "domcontentloaded"});
const out = {sections: []};
await page.locator('span:text-is("编辑"):visible').first().waitFor({timeout: 20000});
await page.waitForTimeout(1500);
const t = await page.locator('body').innerText();
out.header = (t.match(/小节数:[\s\S]{0,60}(免费|付费|加密)/) || [''])[0].replace(/\s+/g, ' ');
const n = await page.locator('span:text-is("编辑"):visible').count();
out.n = n;
for (let i = 0; i < n; i++) {
  if (i > 0) { await page.reload({waitUntil: "domcontentloaded"}); await page.locator('span:text-is("编辑"):visible').first().waitFor({timeout: 20000}); await page.waitForTimeout(1200); }
  await page.locator('span:text-is("编辑"):visible').nth(i).click();
  let f = null;
  for (let k = 0; k < 40 && !f; k++) { await page.waitForTimeout(500); f = page.frames().find(fr => fr.url().includes('/text/edit/')); }
  await f.waitForFunction(() => { try { return window.UE.instants['ueditorInstant0'].getContent().length > 0; } catch (e) { return false; } }, null, {timeout: 25000});
  await page.waitForTimeout(800);
  out.sections.push(await f.evaluate(() => { const e = window.UE.instants['ueditorInstant0']; const d = document.createElement('div'); d.innerHTML = e.getContent(); return {title: document.querySelector('input[placeholder="建议14字内"]').value, text: d.innerText, imgs: [...d.querySelectorAll('img')].map(i => i.src.split('?')[0]), tables: d.querySelectorAll('table').length}; }));
}
// 只读：刷新页面丢弃打开的编辑抽屉，不保存
await page.reload({waitUntil: "domcontentloaded"});
return out;
"""

for i, s in enumerate(secs):
    js = RUN.replace("__SECTION__", json.dumps(s, ensure_ascii=False)).replace("__DETAIL__", json.dumps(DETAIL))
    open(os.path.join(out, f"run_{i}.js"), "w").write(js)
open(os.path.join(out, "verify.js"), "w").write(VERIFY.replace("__DETAIL__", json.dumps(DETAIL)))
print(f"生成 {len(secs)} 个 run_<i>.js 和 verify.js 到 {out}")
