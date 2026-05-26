# 蚁圈瓜田 测试报告 v2

测试时间：2026-05-26 08:44 UTC
执行人：Codex
环境：https://antguatian.pages.dev
浏览器测试：是（Playwright Chromium headless）

## 总览
- 通过：68 / 失败：0 / 跳过：0

## A 段
- A1 ✅ `/` HTTP 200，`Content-Type: text/html; charset=utf-8`，CSP 头存在
- A2 ✅ `/data.json` HTTP 200，`records` 数组长度 4
- A3 ✅ `/disclaimer.html` HTTP 200
- A4 ✅ `/demos/A2-v2-design-skill.html` HTTP 200
- A5 ✅ `GET /api/submit` 返回 HTTP 405

## B 段
- B1 ✅ 顶部 sticky nav 存在，含 🍉 logo、蚁圈瓜田、Formica Watch（视觉渲染为大写）、LIVE 标签和 4 个导航链接
- B2 ✅ LIVE 红点持续 `pulse` 动画，`animation-iteration-count: infinite`
- B3 ✅ ticker 含 ALERT、`北京发货 ×2`、最新档案、`在录 4 例 · 受害合计 16 人`
- B4 ✅ hover ticker 后 `animation-play-state` 从 `running` 变为 `paused`
- B5 ✅ hero kicker 为橙色 italic serif，并有横线装饰
- B6 ✅ hero h1 为「圈内卖家避雷榜」，「避雷榜」橙色并有倾斜边框
- B7 ✅ stats strip 为 4 列横条，不是独立 card
- B8 ✅ stat 数字为 `04人 / 16人 / ¥10.9w+ / 02例`
- B9 ✅ toolbar 含搜索框、`/` kbd、chip 筛选、发货地 select、排序 select
- B10 ✅ 性质 chips 共 5 个，含「全部 04」「🚩 卷款跑路 01」「🎭 假货 / 冒充 01」「❌ 拒不发货 01」「📦 货不对版 01」，默认 active 为橙底
- B11 ✅ 4 条 `article.entry` 卡片，左侧色条为 r1 红 / r2 橙 / r3 金 / r4 灰
- B12 ✅ entry row1 含 mono ID、平台 tag、带 emoji 的性质 chip
- B13 ✅ entry row2 含发货地、商品、金色 mono 价位；北京为红色并带 📍
- B14 ✅ 第 1 条 evidence chips 为「关联号 ×2 / 闲鱼差评 ×23 / 群证 ×8 / 首曝 2026-02」
- B15 ✅ 右侧受骗数字含 `8🔥`、重复价位、横向进度条
- B16 ✅ 投稿区顶部有 4px 黄黑 45° hazard tape
- B17 ✅ footer 4 列 + 底部 colophon 单行 last_update

## C 段
- C1 ✅ 点击 entry 展开详情，含关联 ID code 块、notes-full 全文、录入时间
- C2 ✅ 再点同一行后详情收起
- C3 ✅ hover entry 后背景从 `rgb(20,17,13)` 变 `rgb(29,24,19)`，左侧色条从 `3px` 变 `5px`
- C4 ✅ 点击「🚩 卷款跑路」chip 后仅显示 `wxid_antscam_a88`，chip active
- C5 ✅ 再点同一 chip 不取消选中
- C6 ✅ 点击「全部」chip 后恢复 4 条
- C7 ✅ 搜索 `scammer` 命中 `wxid_antscam_a88`
- C8 ✅ 搜索 `北京` 命中 2 条
- C9 ✅ 发货地选「北京」后仅显示 `wxid_antscam_a88 / x_dealer_023`
- C10 ✅ 排序换「最近录入 ↓」后行顺序变化
- C11 ✅ 投稿表单提交成功，创建 issue #14，按钮恢复可用
- C12 ✅ 不刷新页面再次提交成功，创建 issue #15，按钮仍恢复可用

## D 段
- D1 ✅ happy path 返回 200，创建 issue #12
- D2 ✅ 缺 `id` 返回 400：`id 必填且长度 1-100`
- D3 ✅ `platform=weibo` 返回 400
- D4 ✅ `notes` 5 字返回 400：`notes 至少 20 字（说明诈骗手法 / 证据来源）`
- D5 ✅ `notes` 5001 字返回 400：`notes 最长 5000 字`
- D6 ✅ `alt_ids` 11 个返回 400：`alt_ids 最多 10 个`
- D7 ✅ `victim_count=0` 返回 400
- D8 ✅ `victim_count=1.5` 返回 400
- D9 ✅ `alt_ids` 非数组返回 400
- D10 ✅ 非 JSON body 返回 400
- D11 ✅ GET 返回 405
- D12 ✅ UTF-8 中文 payload 返回 200，创建 issue #13，issue body 中文正常

## E 段
- E1 ✅ `X-Robots-Tag` 含 noindex
- E2 ✅ `Referrer-Policy: no-referrer`
- E3 ✅ `X-Content-Type-Options: nosniff`
- E4 ✅ `X-Frame-Options: DENY`
- E5 ✅ CSP `style-src` 含 `'unsafe-inline'`
- E6 ✅ `Permissions-Policy` 含 `interest-cohort=()`
- E7 ✅ `/data.json` `Cache-Control` 含 `max-age=300`

## F 段
- F1 ✅ issue #12 / #13 / #14 / #15 均存在
- F2 ✅ title 均符合 `[投稿] <id> (<nature>)` 格式
- F3 ✅ 四个 issue 均含 `pending-review` 和 `from-form`
- F4 ✅ body 含主 ID、平台、性质、商品、发货地、价位、受骗人数、备注、来源
- F5 ✅ issue #13 中文字段非乱码
- F6 ✅ body 末尾含 `来源: 网页表单 (/api/submit)`
- F7 ✅ `auto-label.yml` 最近四次 issue 触发 run 全部 success

## G 段
- G1 ✅ 1280px：stats 4 列，entry 为 1+1 两列
- G2 ✅ 800px：stats 2x2，entry 单列，entry-victim 横排底部
- G3 ✅ 480px：hero h1 缩小到 38px，ticker label 10px，submit row 单列，`.brand .name-en` 隐藏

## H 段（旧版痕迹回归）
- H1 ✅ DOM 无 `<table>`、`<tbody>`、`<th>`、`<td>`
- H2 ✅ DOM 无 `.row-main`、`.row-detail`、`.platform-tag`、`.truncate`
- H3 ✅ 无 `.rank-bg`，无 80px+ 大背景数字
- H4 ✅ 无「RANK · 01」小标签
- H5 ✅ `/submission.html`、`/appeal.html`、`/pgp.html` 均返回 HTTP 301，`Location: /disclaimer.html`

## 发现的 Bug
无。

## 跟 v1 测试报告的回归对比
- v1 失败的 GitHub labels 问题已修：#12 / #13 / #14 / #15 都有 `pending-review` + `from-form`。
- v1 发现的「投稿成功后按钮保持 disabled」已修：C11 成功后按钮恢复可用，C12 不刷新页面再次提交成功。
- 上一轮 v2 失败的 evidence chips 已修：第 1 条显示「闲鱼差评 ×23」「群证 ×8」「关联号 ×2」「首曝 2026-02」。
- 上一轮 v2 失败的旧路径处理已按新版 brief 修正：旧路径现在 301 到 `/disclaimer.html`。
- v2 视觉主线通过：sticky nav、LIVE pulse、ticker、stats strip、chip 筛选、entry 卡片流、响应式布局均符合 brief。

## 备注
- 本次创建测试 issue：#12、#13、#14、#15，均使用 `codex_test_*`，notes 以 `[CODEX TEST]` 开头。
- 没有修改 `public/data.json`、`.github/`、`functions/`、`tools/`，没有 push。
- 浏览器测试使用系统临时目录中的 Playwright Chromium headless；仓库内未保留测试脚本。
