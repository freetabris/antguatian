# Codex 测试任务 brief（v2 视觉接入后回归）

> 写给一个 cold-start 的 AI agent（Codex）。你不需要读 git history，
> 这份 brief 自包含所有上下文。本次测试是**主站接入 A2 v2 视觉 + 修过 3 个 bug 之后**
> 的回归测试。

---

## 0. 跟上一轮的差异（重点）

上次你测过 v1 的简单表格版本，本次主站完全重做了视觉，并且修过 3 个 bug。
**重点关注**：

| 重做点 | 期望 |
|---|---|
| 主页视觉 | A2「24h 新闻台 + Bloomberg 终端」风：暖色 dark、警示橙红、LIVE 脉冲、滚动 ticker、editorial italic serif 装饰 |
| 列表 | 从 `<table>` 改成 `<article class="entry">` 卡片流 |
| 排名表达 | 删了「大背景数字 1/2/3/4」和「RANK · 01 小标签」(用户嫌歪 / 不符调子)，改用**左侧 3px 彩色条**：r1 红 / r2 橙 / r3 金 / 其它灰 |
| chip 筛选 | 性质从 select 换成 chip 单选切换，「全部 / 🚩 卷款跑路 / 🎭 假货 / ❌ 拒不发货 / 📦 货不对版」|
| ticker / 4 stat / footer | 从 `data.json` 动态注入数字 |
| evidence chips | 从 notes 字段抽取「闲鱼差评 ×N」「群证 ×N」自动显示 |
| 投稿成功后按钮 | 必须 re-enable（之前 bug，已修） |
| GitHub Issue labels | 投稿开的 issue 应该自动加 `pending-review` + `from-form` 两个 label（之前 PAT 权限问题，已改用 GitHub Action `auto-label.yml` 兜底） |

**视觉基线对照**：完整 v2 demo 在
`https://antguatian.pages.dev/demos/A2-v2-design-skill.html`（静态硬编码版）。
主站 `https://antguatian.pages.dev/` 应该跟它视觉**几乎一致**（差别：主站列表是
真实数据驱动 + 没有大背景数字、改用左侧色条；其它视觉元素一致）。

---

## 1. 项目快速回顾

- **是什么**：蚂蚁圈交易诈骗黑名单查询站（蚁圈瓜田 / Formica Watch）
- **线上**：https://antguatian.pages.dev
- **Repo**：https://github.com/freetabris/antguatian（公开）
- **本地代码**：`E:\cc\antguatian\`
- **架构**：纯静态 SPA（CF Pages）+ 一个 Pages Function `/api/submit` 调 GitHub Issues API
- **数据源**：`/data.json`（schema v2 扁平 records 数组，4 条种子）
- **审核流程**：投稿 → GitHub Issue（auto label）→ 站长手动跑 `tools/add-record.py` 改 `public/data.json` → push → CF Pages 自动部署

## 2. 数据 schema（v2）

```json
{
  "version": 2,
  "generated_at": "ISO8601 UTC",
  "records": [
    {
      "id": "...",                      // 主 ID 明文公示
      "platform": "wechat|xianyu|phone|qq|other",
      "alt_ids": ["..."],               // 同一卖家其它账号
      "nature": "...",                  // 自由文本
      "goods_type": "...",
      "ship_from": "...",
      "price_range": "...",
      "victim_count": 8,
      "notes": "...",                   // ≥20 字
      "added_at": "ISO8601 UTC"
    }
  ]
}
```

种子数据 4 条（按当前默认排序「受骗人数 ↓」）：

| rank | id | platform | nature | ship_from | victim |
|---|---|---|---|---|---|
| 1 | wxid_antscam_a88 | wechat | 卷款跑路 | 北京 | 8 |
| 2 | 13800138888 | phone | 假货 / 冒充 | 广东深圳 | 5 |
| 3 | x_dealer_023 | xianyu | 拒不发货 | 北京 | 2 |
| 4 | wxid_w_156 | wechat | 货不对版 | 云南昆明 | 1 |

## 3. `/api/submit` 验证规则（没变）

| 字段 | 必填 | 约束 |
|---|---|---|
| id | ✅ | 1-100 字 |
| platform | ✅ | wechat/xianyu/phone/qq/other |
| alt_ids | 否 | array，≤10 项，每项 1-100 字 |
| nature | ✅ | 1-50 字 |
| goods_type | 否 | ≤200 字 |
| ship_from | ✅ | 1-100 字 |
| price_range | 否 | ≤50 字 |
| victim_count | 否 | int 1-99999 |
| notes | ✅ | 20-5000 字 |
| contact | 否 | ≤200 字 |

错误返回 `{ok:false, error}` + HTTP 400 / 405 / 502 / 500。

---

## 4. 测试任务

按段做。没浏览器跑不动 B / C / G 段，做剩下的即可。

### A. Smoke test（必做，2 分钟）

| ID | 命令 | 期望 |
|---|---|---|
| A1 | `curl -sI https://antguatian.pages.dev/` | HTTP 200, html, CSP 头存在 |
| A2 | `curl -s .../data.json \| jq '.records \| length'` | 4 |
| A3 | `curl -sI .../disclaimer.html` | 200 |
| A4 | `curl -sI .../demos/A2-v2-design-skill.html` | 200（视觉基线还在）|
| A5 | `curl -sX GET .../api/submit` | 405 |

### B. 主页视觉（需要浏览器）

打开 https://antguatian.pages.dev，肉眼对照 demos/A2-v2-design-skill.html 做视觉对比。

| ID | 检查项 | 期望 |
|---|---|---|
| B1 | 顶部 sticky nav | 🍉 logo + 「蚁圈瓜田 / Formica Watch」 + 红色 LIVE 标签带脉冲红点 + 4 个导航链接 |
| B2 | LIVE 红点 | 持续 pulse 动画（不停顿） |
| B3 | ticker bar | 顶部橙色 ALERT 标签 + 横向滚动文字（含「北京发货 ×2」「最新档案 [id] · [YYYY-MM]」「在录 4 例 · 受害合计 16 人」等动态文本）|
| B4 | ticker hover 暂停 | 鼠标悬停 ticker 上时，文字停止滚动 |
| B5 | hero kicker | 橙色 italic serif 小标，结尾有横线装饰 |
| B6 | hero h1 | 大字「圈内卖家**避雷榜**」，「避雷榜」三字橙色 + 倾斜矩形边框 |
| B7 | stats strip | 4 列横条 hairline 分隔（**不是** 4 个独立 card），数字大字号、单位小灰字 |
| B8 | stat 数字 | records=4 / victims=16 / amount 非「—」(估算值) / beijing=2 |
| B9 | toolbar | 搜索框（带 🔍 ico 和 `/` kbd 标）、chip 性质过滤、发货地 select、排序 select |
| B10 | 性质 chip | 至少 5 个：「全部 04」「🚩 卷款跑路 01」「🎭 假货 / 冒充 01」「❌ 拒不发货 01」「📦 货不对版 01」，「全部」默认 active 橙底 |
| B11 | board entry | 4 条卡片，每条左侧 3px 彩色条（**注意验证 rank 颜色：r1 红 / r2 橙 / r3 金 / r4 灰**）|
| B12 | entry row1 | ID（mono 等宽字）+ 平台 tag + 性质 chip（带 emoji）|
| B13 | entry row2 | 发货地（北京带 📍 红字、其它带 · 灰前缀）+ 商品 + 价位（金色 mono）|
| B14 | evidence chips | 第 1 条 entry 应有「闲鱼差评 ×23」「群证 ×8」「关联号 ×2」「首曝 2026-02」 |
| B15 | 受骗右侧 | 大数字 + 「🔥」(victim≥5) + 价位重复 + 横向进度条 |
| B16 | 投稿区 hazard tape | 顶部 4px 高的黄黑 45° 斜条纹 |
| B17 | footer | 4 列（关于 / 数据 / 原则 / 联系）+ 底部 colophon 单行 last_update |

### C. 交互行为

| ID | 操作 | 期望 |
|---|---|---|
| C1 | 点 entry 任一行 | 该行下方展开 entry-detail（含关联 ID code 块 + notes-full 全文 + 录入时间）|
| C2 | 再点同一行 | 详情收起 |
| C3 | hover entry | 背景从 #14110d 变 #1d1813；左侧颜色条从 3px → 5px |
| C4 | 点性质 chip「🚩 卷款跑路」 | 仅显示 wxid_antscam_a88 一条；chip 变橙底 active 状态 |
| C5 | 再点同 chip | （应该不会取消选中，单选行为；点「全部」才回全） |
| C6 | 点「全部」 chip | 4 条全显示 |
| C7 | 搜索 `scammer` | 命中 wxid_antscam_a88（alt_ids 含 x_scammer_88）|
| C8 | 搜索 `北京` | 命中 2 条 |
| C9 | 发货地 select 选「北京」 | 仅显示 wxid_antscam_a88 / x_dealer_023 |
| C10 | 排序换「最近录入 ↓」 | 行顺序变化（按 added_at desc） |
| C11 | 投稿表单提交（满足约束，id 以 `codex_test_` 开头，notes 含 `[CODEX TEST]`，≥20 字） | 跳出「✓ 已提交 · issue #N」链接；按钮 re-enable 可再次提交 |
| C12 | 提交后**不刷新页面再提交一次** | 应能再次提交成功（**这是之前修过的 bug，必测**） |

### D. `/api/submit` API（必做）

跟上一轮一样，逐条 POST 测，所有测试 payload 的 `id` 必须以 `codex_test_` 开头、`notes` 第一行写 `[CODEX TEST]`（站长事后批量 close）。

| ID | payload | 期望 |
|---|---|---|
| D1 happy | 合法完整字段，UTF-8 中文 | 200 `{ok:true, issue_url, issue_number}` |
| D2 缺 id | | 400 |
| D3 platform 越界 (`weibo`) | | 400 |
| D4 notes 短（5 字） | | 400 「至少 20 字」|
| D5 notes 长（5001 字） | | 400 「最长 5000 字」|
| D6 alt_ids 11 个 | | 400 「最多 10 个」|
| D7 victim_count=0 | | 400 |
| D8 victim_count=1.5 | | 400 |
| D9 alt_ids 非数组 | | 400 |
| D10 非 JSON body | | 400 |
| D11 GET | | 405 |
| D12 UTF-8 中文 | nature/notes/ship_from 全中文 | 200 + issue body 中文正确 |

> **重要**：用 UTF-8 文件 + `curl --data-binary @file` 发请求，**不要** shell 单引号塞中文（Git Bash GBK 会乱码）。

### E. HTTP 头（必做）

`curl -sI .../` 检查响应头：

| ID | header | 期望 |
|---|---|---|
| E1 | X-Robots-Tag | 含 noindex |
| E2 | Referrer-Policy | no-referrer |
| E3 | X-Content-Type-Options | nosniff |
| E4 | X-Frame-Options | DENY |
| E5 | Content-Security-Policy | **必须含 `'unsafe-inline'` 在 style-src**（demos 用 inline style，主 CSP 已放宽）|
| E6 | Permissions-Policy | 含 interest-cohort=() |
| E7 | /data.json Cache-Control | max-age=300 |

### F. GitHub 集成（必做）

D 段每次成功 POST 都会创建一个 issue。等 **20-30 秒**让 Action 跑完，然后查：

| ID | 检查 | 期望 |
|---|---|---|
| F1 | issue 存在 | `gh issue view N --repo freetabris/antguatian` 不报错 |
| F2 | title | `[投稿] <id> (<nature>)` 格式 |
| F3 | labels | **必须含 `pending-review` + `from-form` 两个 label**（这是 auto-label.yml Action 加的，**之前 bug 已修**，必测）|
| F4 | body | 含主 ID / 平台 / 性质 / 商品 / 发货地 / 价位 / 受骗 / 备注 / 来源 |
| F5 | UTF-8 | 中文不乱码 |
| F6 | 末尾 | 含 `来源: 网页表单 (/api/submit)` |
| F7 | Action 运行 | `gh run list --repo freetabris/antguatian --workflow auto-label.yml --limit 5` 应能看到每条 issue 触发的一次 run，全部 success |

### G. 响应式（需要浏览器）

| ID | 视口 | 期望 |
|---|---|---|
| G1 | 1280px | 完整布局（stats 4 列 / entry 1+1 列） |
| G2 | 800px | stats 2x2 / entry 单列 / entry-victim 横排底部 |
| G3 | 480px | hero h1 缩小、ticker label 缩小、submit row 单列、brand .name-en 隐藏 |

### H. 不该出现的旧版痕迹（回归）

| ID | 检查 | 期望 |
|---|---|---|
| H1 | DevTools 查 DOM | **不应有** `<table>` `<tbody>` `<th>` `<td>` 元素（已改为 article entry） |
| H2 | 查 CSS | **不应有** `.row-main` `.row-detail` `.platform-tag` `.truncate` 旧 class 在 DOM 上使用 |
| H3 | 大背景排名数字 | **不应有** `.rank-bg` 元素或 128px / 96px / 80px 的大数字 1/2/3/4 浮在 entry 左侧 |
| H4 | 「RANK · 01」小标签 | **不应存在** |
| H5 | 旧路径 redirect | `/submission.html` `/appeal.html` `/pgp.html` 应 **301 redirect 到 `/disclaimer.html`**（内容已合并过去，保留外链友好性）。`curl -sI` 看 Location 头 |

---

## 5. 你**不要**做的事

- ❌ 不要 push、不要改 main 分支
- ❌ 不要修改 `public/data.json`
- ❌ 不要碰 `.github/`、`functions/`、`tools/`
- ❌ 不要 close 不是你开的 issue
- ❌ 不要打开 `pending-review` 标签下的非 `codex_test_*` issue
- ❌ 不要在测试投稿里写真人信息

允许：
- ✅ GET / curl 静态资源
- ✅ POST `/api/submit` 投合规测试稿（id `codex_test_*`，notes `[CODEX TEST]…` 开头）
- ✅ `gh issue view` / `gh run list` 任意只读 git 操作
- ✅ 读 repo 内任何文件

## 6. 输出格式

写到 `E:\cc\antguatian\TESTING_REPORT.md`（覆盖上次的）。结构：

```markdown
# 蚁圈瓜田 测试报告 v2

测试时间：YYYY-MM-DD HH:MM UTC
执行人：Codex
环境：https://antguatian.pages.dev
浏览器测试：是 / 否（说明）

## 总览
- 通过：X / 失败：Y / 跳过：Z

## A 段
- A1 ✅ ...
...

## B 段
- B1 ✅ / ❌（描述差异）
...

## H 段（旧版痕迹回归）
- H1 ✅ DOM 无 table 元素
...

## 发现的 Bug
1. **[P0/P1/P2/P3] 标题**
   - 重现：
   - 期望：
   - 实际：
   - 涉及文件 / 行：

## 跟 v1 测试报告的回归对比
[上次失败 / 未实现的项，本次是否已修]

## 备注
[任何观察、改进建议、设计上的疑虑]
```

提交方式：写入文件即可，**不要 push**。

## 7. 提示

- 中文 payload 用 UTF-8 文件 + `curl --data-binary @file`
- 测试期会开一批 `codex_test_*` issue，事后批量 close 命令：
  ```bash
  gh issue list --repo freetabris/antguatian --state open --search "codex_test" --json number --jq '.[].number' | xargs -I {} gh issue close {} --repo freetabris/antguatian --comment "regression test, closing"
  ```
- 视觉对比时，先开两个 tab 并排：主站 vs `demos/A2-v2-design-skill.html`
- 如果发现 LIVE 红点不脉冲、ticker 不滚动、左侧色条没有 r1 红 r2 橙等——记下来当 Bug
- 如果 F3 labels 又没附上（auto-label.yml Action 没跑或失败），先查 `gh run list` 看 Action 状态，再 `gh run view <id>` 看具体失败
- 如果你的 IP 被 CF 临时 429，sleep 30s 再重试
