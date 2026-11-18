# 小鹅通后台页面操作手册（Tabbit / Playwright）

以下代码都通过 `~/.local/bin/tabbit-cli nodejs --task "<任务名>" --request-id <新ID> < 文件.js` 运行，`page` 是当前标签页。
每个新程序都用新的 request-id。

## 目录
1. 页面地址
2. 通用坑
3. 新建课程表单
4. 上传图片并取回地址
5. 选封面
6. 备份小节原文（更新旧课前必做）
7. 批量改小节标题 / 正文替换
8. 核对其他课程没被动

## 1. 页面地址

| 页面 | 地址 |
|---|---|
| 课程列表 | `https://admin.xiaoe-tech.com/t/course/camp_pro/list#/list` |
| 课程详情（目录） | `https://admin.xiaoe-tech.com/t/course/camp_pro/detail/<course_id>` |
| 新建课程 | 列表页点「新建」→ `.../camp_pro/edit/new` |
| 学员端预览 | 课程分享短链会跳到 `*.h5.xet.pomoho.com/p/course/ecourse/preview/<course_id>` |

## 2. 通用坑

- **固定列表格**：列表页每行的「管理」有隐藏副本，用 `span:text-is("管理"):visible`。
- **悬停菜单**：「添加小节」下拉、小节类型里的「新建/已有」都是悬停才出现，必须在**同一个程序**里连续 hover/click，跨程序会收起。
- **小节编辑器在抽屉里的 iframe**：`page.frames().find(f => f.url().includes('/text/edit/'))`，新建为 `/text/edit/new`，已有为 `/text/edit/i_xxx`。
- **UEditor**：`window.UE.instants['ueditorInstant0']`，`getContent()` 读、`setContent(html)` 写，写完 `fireEvent('contentchange')`。刚打开时 `getContent()` 可能抛错，用 try 包起来等。
- **放弃编辑**：直接 `page.reload()`，抽屉里未保存的内容会丢掉，不会存草稿。
- **弹窗**：「暂未开启联系商家入口」等警告会挡住点击，点它的 `.ss-message-close`（×）关闭，不要点「去开启」。
- 点图片缩略图会打开大图预览，按 Escape 关闭；选图要点行首的 `label.ss-radio`。
- **封面的「添加图片」是悬停遮罩按钮**（`.ss-material-selection .ss-mask-btn`），不悬停时不可见：先 `hover()` 封面框，再 `click({force: true})`。
- **新建课程页刚打开时会重置名称输入框**：名称放到最后填，填完用 `inputValue()` 读回核对；没填上就用 `pressSequentially` 逐字输入。
- `locator.evaluate(fn, arg)` 的 `fn` 第一个参数是元素本身，传入的参数在第二个：`(root, arg) => ...`。
- 页面控制台的 SyntaxError/TypeError 警告是站点自身的，可忽略。

## 3. 新建课程表单

```js
await page.goto("https://admin.xiaoe-tech.com/t/course/camp_pro/list#/list", {waitUntil: "domcontentloaded"});
await page.locator('button:visible', {hasText: /^新建$/}).first().click();
await page.waitForTimeout(4000);
// 关掉可能出现的警告
const warn = page.locator('.ss-message-box-wrapper__warning');
if (await warn.isVisible().catch(() => false)) await warn.locator('.ss-message-close').click();
await page.getByPlaceholder("建议14字内").first().fill("<课程名>");
await page.locator('label', {hasText: /^\s*暂不上架\s*$/}).first().click();   // 默认是「立即上架」！
// 封面见第 5 节；保存前读一遍状态给自己核对：
return await page.evaluate(() => { const r = {}; document.querySelectorAll('input[type=radio],input[type=checkbox]').forEach(i => { const t = (i.closest('label')?.innerText || '').trim(); if (['免费','付费','立即上架','暂不上架','显示','隐藏','长期有效'].includes(t)) r[t] = i.checked; }); return {name: document.querySelector('input[placeholder="建议14字内"]').value, r}; });
```

核对无误后保存：`await page.locator('button:visible', {hasText: /^\s*保存\s*$/}).last().click();`，跳转后的 URL 里就是课程 ID。

## 4. 上传图片并取回地址

在新建课程页点封面区的「添加图片」打开素材库「选择图片」弹窗：

```js
await page.getByText("添加图片", {exact: true}).first().click();
await page.waitForTimeout(2500);
const lib = page.locator('.ss-dialog:visible', {hasText: "选择图片"}).first();
await lib.getByText("上传图片", {exact: true}).first().click();
await page.waitForTimeout(1500);
const up = page.locator('.ss-dialog:visible', {hasText: "确认上传"}).last();
const fcP = page.waitForEvent('filechooser', {timeout: 8000});
await up.getByText("点击选择图片", {exact: false}).first().click();
(await fcP).setFiles(<list.json 里的绝对路径数组>);
await page.waitForTimeout(3000);
await up.getByText(/确认上传/).last().click();
```

等它显示「共 N 个 上传成功 N」后点上传窗的 ×（`[class*=close]`）。然后在「选择图片」弹窗里把每页改成 30 条，按文件名抓地址：

```js
const lib = page.locator('.ss-dialog:visible', {hasText: "选择图片"}).first();
await lib.locator('.ss-pagination-options-size .ss-select').click();
await page.waitForTimeout(800);
await page.locator('.ss-select-dropdown:visible li', {hasText: "30 条"}).first().click();
await page.waitForTimeout(3000);
return await lib.evaluate((prefix) => Object.fromEntries([...document.querySelectorAll('img')].map(i => [ (i.closest('tr')?.innerText || '').match(new RegExp(prefix + '_\\S+'))?.[0], i.src.split('?')[0] ]).filter(([k]) => k)), "<课程名>");
```

把返回值存成 `build/urls.json`，数量应等于上传数。超过 30 张时再翻页（分页器 `ul.ss-pagination`）。

## 5. 选封面

```js
const lib = page.locator('.ss-dialog:visible', {hasText: "选择图片"}).first();
const row = lib.locator('tr').filter({hasText: "<课程名>_00封面"}).first();
await row.locator('label.ss-radio').click();
await lib.locator('button', {hasText: /^\s*确认\s*$/}).last().click();
await page.waitForTimeout(2000);
return await page.evaluate(() => [...document.querySelectorAll('.ss-material-selection img')].filter(i => i.offsetParent).map(i => i.src));
```

## 6. 备份小节原文（更新旧课前必做）

在课程详情页运行，结果大时用 `scripts/read_resource.py` 取回，再把每节 `html` 存成文件：

```js
const out = [];
const n = await page.locator('span:text-is("编辑"):visible').count();
for (let i = 0; i < n; i++) {
  await page.reload({waitUntil: "domcontentloaded"});
  await page.locator('span:text-is("编辑"):visible').first().waitFor();
  await page.waitForTimeout(1500);
  await page.locator('span:text-is("编辑"):visible').nth(i).click();
  let f = null;
  for (let t = 0; t < 40 && !f; t++) { await page.waitForTimeout(500); f = page.frames().find(fr => fr.url().includes('/text/edit/')); }
  await f.waitForFunction(() => { try { return window.UE.instants['ueditorInstant0'].getContent().length > 0; } catch (e) { return false; } }, null, {timeout: 25000});
  out.push(await f.evaluate(() => ({id: location.pathname.split('/').pop(), title: document.querySelector('input[placeholder="建议14字内"]').value, html: window.UE.instants['ueditorInstant0'].getContent()})));
}
await page.reload({waitUntil: "domcontentloaded"});   // 不保存
return out;
```

## 7. 批量改小节标题 / 正文替换

先确认用户要的新标题和每处正文改法。下面的例子会去掉标题开头的「第X课 」，并替换正文里的课次引用。`REPL` 和要处理的小节下标按实际情况改：

```js
const REPL = [
  [/第 ?\d ?课会(详细展开|专门拆解|详细讲|细讲|专门讲)/g, "在后面会详细展开"],
  [/第 ?1 ?课讲过/g, "前面讲过"],
];
const out = [];
const n = await page.locator('span:text-is("编辑"):visible').count();
for (let i = 0; i < n; i++) {
  await page.reload({waitUntil: "domcontentloaded"});
  await page.locator('span:text-is("编辑"):visible').first().waitFor();
  await page.waitForTimeout(1200);
  await page.locator('span:text-is("编辑"):visible').nth(i).click();
  let f = null;
  for (let k = 0; k < 40 && !f; k++) { await page.waitForTimeout(500); f = page.frames().find(fr => fr.url().includes('/text/edit/')); }
  await f.waitForFunction(() => { try { return window.UE.instants['ueditorInstant0'].getContent().length > 0; } catch (e) { return false; } }, null, {timeout: 25000});
  const title = f.locator('input[placeholder="建议14字内"]').first();
  const old = await title.inputValue();
  if (!/^第\d+课 /.test(old)) { out.push({i, skip: old}); continue; }
  await title.fill(old.replace(/^第\d+课 /, ""));
  const r = await f.evaluate((reps) => { const e = window.UE.instants['ueditorInstant0']; let h = e.getContent(), c = 0; for (const [s, fl, to] of reps) h = h.replace(new RegExp(s, fl), () => { c++; return to; }); if (c) { e.setContent(h); e.fireEvent('contentchange'); } return c; }, REPL.map(([re, to]) => [re.source, re.flags, to]));
  await f.locator('button:visible', {hasText: /^\s*保存\s*$/}).last().click();
  let gone = false;
  for (let k = 0; k < 30; k++) { await page.waitForTimeout(1000); if (!page.frames().some(fr => fr.url().includes('/text/edit/'))) { gone = true; break; } }
  out.push({i, old, replaced: r, saved: gone});
  if (!gone) break;
}
return out;
```

改完用 `verify.js` + `compare.py` 回读（标题有变化时先用同样规则更新 final.json，或直接人工看回读结果）。

## 8. 核对其他课程没被动

```js
await page.goto("https://admin.xiaoe-tech.com/t/course/camp_pro/list#/list", {waitUntil: "domcontentloaded"});
await page.waitForTimeout(3000);
const input = page.getByPlaceholder(/搜索|名称|课程/).first();
await input.fill("<关键词>"); await input.press("Enter");
await page.waitForTimeout(3500);
return (await page.locator('body').innerText()).replace(/\s+/g, ' ').match(/内容数[\s\S]{0,600}/)?.[0];
```

看各课程的「上架状态」和「最新修改时间」，和动手前对比。
