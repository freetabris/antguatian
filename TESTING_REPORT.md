# 蚁圈瓜田 测试报告

测试时间：2026-05-26 03:16 UTC
执行人：Codex
环境：https://antguatian.pages.dev
浏览器测试：是（Playwright Chromium headless）

## 总览
- 通过：45
- 失败：2
- 跳过：0

## A 段（Smoke test）
- A1 ✅ `/` HTTP 200，`Content-Type: text/html; charset=utf-8`，响应头含 `content-security-policy`
- A2 ✅ `/data.json` HTTP 200，`records` 数组长度 4
- A3 ✅ `/disclaimer.html` HTTP 200
- A4 ✅ `/robots.txt` HTTP 200，body 含 `Disallow: /`
- A5 ✅ `GET /api/submit` 返回 HTTP 405，body 为 `{ok:false, error:"Method Not Allowed (use POST)"}`

## B 段（前端交互）
- B1 ✅ 表格渲染 4 行，列顺序为：主 ID / 性质 / 发货地 / 商品类型 / 价位 / 受骗人数
- B2 ✅ 排序切换到「最近录入 ↓」后，行顺序从 `wxid_antscam_a88, 13800138888, x_dealer_023, wxid_w_156` 变为 `wxid_antscam_a88, x_dealer_023, wxid_w_156, 13800138888`
- B3 ✅ 性质筛选「卷款跑路」后只剩 `wxid_antscam_a88`
- B4 ✅ 发货地筛选「北京」后剩 2 行：`wxid_antscam_a88, x_dealer_023`
- B5 ✅ 搜索 `scammer` 命中 `wxid_antscam_a88`
- B6 ✅ 搜索 `北京` 命中 2 行：`wxid_antscam_a88, x_dealer_023`
- B7 ✅ 点击表格行展开详情，详情含关联 ID、备注、录入时间
- B8 ✅ 再点同一行后详情收起
- B9 ✅ 浏览器表单提交成功，创建 issue #5：https://github.com/freetabris/antguatian/issues/5
- B10 ✅ notes 留空时被浏览器 HTML5 必填校验拦下，没有发请求
- B11 ❌ 期望后端 400 并在前端显示「notes 至少 20 字...」，实际被浏览器 `minlength=20` 校验拦下，请求未发出，`#sf-msg` 无错误文案

## C 段（`/api/submit` API）
- C1 ✅ happy path 返回 200，创建 issue #3：https://github.com/freetabris/antguatian/issues/3
- C2 ✅ 缺 `id` 返回 400：`id 必填且长度 1-100`
- C3 ✅ 缺 `platform` 返回 400：`platform 必须是 wechat / xianyu / phone / qq / other`
- C4 ✅ `platform=weibo` 返回 400，同上
- C5 ✅ 缺 `nature` 返回 400：`nature 必填且长度 1-50`
- C6 ✅ 缺 `ship_from` 返回 400：`ship_from 必填且长度 1-100`
- C7 ✅ `notes` 过短返回 400：`notes 至少 20 字（说明诈骗手法 / 证据来源）`
- C8 ✅ `notes` 长度 5001 返回 400：`notes 最长 5000 字`
- C9 ✅ `alt_ids` 11 个返回 400：`alt_ids 最多 10 个`
- C10 ✅ `victim_count=0` 返回 400：`victim_count 必须是 1-99999 的整数`
- C11 ✅ `victim_count=1.5` 返回 400，同上
- C12 ✅ `alt_ids` 非数组返回 400：`alt_ids 必须是数组`
- C13 ✅ 非 JSON body 返回 400：`请求体不是合法 JSON`
- C14 ✅ GET 方法返回 405
- C15 ✅ OPTIONS 返回 405（brief 允许 405 或 200，仅观察）
- C16 ✅ 中文字段返回 200，创建 issue #4：https://github.com/freetabris/antguatian/issues/4，issue body 中文显示正常

## D 段（静态资源 / HTTP 头）
- D1 ✅ `/` 的 `X-Robots-Tag` 含 `noindex, nofollow, noarchive, nosnippet`
- D2 ✅ `/` 的 `Referrer-Policy` 为 `no-referrer`
- D3 ✅ `/` 的 `X-Content-Type-Options` 为 `nosniff`
- D4 ✅ `/` 的 `X-Frame-Options` 为 `DENY`
- D5 ✅ `/` 的 `Content-Security-Policy` 含 `default-src 'self'` 和 `frame-ancestors 'none'`
- D6 ✅ `/` 的 `Permissions-Policy` 含 `interest-cohort=()`
- D7 ✅ `/data.json` 的 `Cache-Control` 含 `max-age=300`，`X-Robots-Tag` 含 noindex
- D8 ✅ `/styles.css` 的 `Content-Type` 为 `text/css; charset=utf-8`
- D9 ✅ `/app.js` 的 `Content-Type` 为 `application/javascript`

## E 段（GitHub 集成）
- E1 ✅ issue #3 / #4 / #5 均真实存在，`gh issue view` 不报错
- E2 ✅ title 符合 `[投稿] <id> (<nature>)` 格式
- E3 ❌ labels 为空；期望含 `pending-review` 和 `from-form`
- E4 ✅ body 含主 ID、平台、性质、商品类型、发货地、价位、受骗人数、备注、来源
- E5 ✅ issue #4 中文字段非乱码
- E6 ✅ body 末尾含 `来源: 网页表单 (/api/submit)`

## 发现的 Bug
1. **[严重度 P2] 表单创建的 GitHub issue 没有打上 labels**
   - 重现：POST `/api/submit` 创建测试投稿，或用首页表单提交测试投稿。
   - 期望：issue labels 含 `pending-review` 和 `from-form`。
   - 实际：issue #3 / #4 / #5 的 `labels` 均为 `[]`。
   - 涉及文件 / 行：`functions/api/submit.ts:191-194`

2. **[严重度 P3] notes 过短的前端行为与 brief 不一致**
   - 重现：首页投稿表单中填写必填项，`notes` 填 `短` 后提交。
   - 期望：请求发到后端，后端返回 400，前端显示「notes 至少 20 字...」。
   - 实际：`public/index.html` 的 `minlength=20` 触发浏览器原生校验，请求未发出，`#sf-msg` 没有错误文案。
   - 涉及文件 / 行：`public/index.html:109`，`public/app.js:203-216`

3. **[严重度 P3] 投稿成功后按钮保持 disabled，用户不能在同一页面继续提交**
   - 重现：首页表单成功提交一次后，不刷新页面，尝试再次提交。
   - 期望：成功提示出现后，按钮恢复可用，或页面明确提示无需重复提交。
   - 实际：`#sf-btn` 保持 disabled；后续同页无法再次提交。
   - 涉及文件 / 行：`public/app.js:186`，`public/app.js:218`

## 备注
- 本次创建的测试 issue：#3、#4、#5，均使用 `codex_test_*` ID，notes 含 `[CODEX TEST]`。
- 没有修改 `public/data.json`、`.github/`、`functions/`、`tools/`，没有 push。
- Playwright 依赖和 Chromium 下载在系统临时目录 / Playwright 缓存中完成，仓库内未保留测试脚本。
