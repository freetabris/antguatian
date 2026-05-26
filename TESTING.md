# Codex 测试任务 brief

> 写给一个 cold-start 的 AI agent（Codex）。你不需要读这个 repo 的对话历史，
> 这份 brief 包含所有上下文 + 测试任务 + 输出格式约定。

---

## 1. 项目是什么

**蚁圈瓜田**（`antguatian`）—— 蚂蚁爱好者圈子里的交易诈骗黑名单查询站。
访客输入卖家 ID（微信 / 闲鱼 / 手机号 / QQ），查圈内是否有该商家的诈骗记录。

- **线上**：https://antguatian.pages.dev
- **Repo**：https://github.com/freetabris/antguatian
- **本地代码**：`E:\cc\antguatian\`（你也可以远程操作，本地不是必须）

## 2. 架构（一分钟看懂）

```
浏览器
  ├─ GET  /, /data.json, /disclaimer.html, /styles.css, /app.js
  │     ↓
  │   Cloudflare Pages 静态文件（public/ 目录直发）
  │
  └─ POST /api/submit   { id, platform, nature, ... }
         ↓
       Cloudflare Pages Function（functions/api/submit.ts）
         ↓ 用 GITHUB_TOKEN（CF Pages Secret）调
       GitHub Issues API: POST /repos/freetabris/antguatian/issues
         ↓
       新 issue 自动开出来，labels: [pending-review, from-form]
         ↓
       返回 { ok: true, issue_url, issue_number } 给前端
```

录入流程（你**不要触发**）：站长在 GitHub 看到 issue → 审核 → 本地跑 `tools/add-record.py` → 改 `public/data.json` → push → CF Pages auto-deploy。

## 3. 数据 schema（v2 扁平）

`public/data.json`：

```json
{
  "version": 2,
  "generated_at": "ISO8601 UTC",
  "records": [
    {
      "id": "wxid_xxx",              // 主 ID（明文公示）
      "platform": "wechat",          // wechat | xianyu | phone | qq | other
      "alt_ids": ["x_alt_1"],        // 同一卖家其它账号
      "nature": "卷款跑路",            // 自由文本，常见值见 ISSUE_TEMPLATE
      "goods_type": "活体",            // 自由文本
      "ship_from": "北京",             // 城市级
      "price_range": "1000-5800",    // 自由文本
      "victim_count": 8,             // int ≥ 1
      "notes": "...",                // 自由文本
      "added_at": "ISO8601 UTC"
    }
  ]
}
```

种子数据（4 条）：
| id | platform | nature | ship_from |
|---|---|---|---|
| wxid_antscam_a88 | wechat | 卷款跑路 | 北京 |
| x_dealer_023 | xianyu | 拒不发货 | 北京 |
| wxid_w_156 | wechat | 货不对版 | 云南昆明 |
| 13800138888 | phone | 假货 / 冒充 | 广东深圳 |

## 4. `/api/submit` 验证规则（见 `functions/api/submit.ts::validate`）

| 字段 | 必填？ | 约束 |
|---|---|---|
| `id` | ✅ | string，trim 后 1-100 字 |
| `platform` | ✅ | 必须 ∈ {wechat, xianyu, phone, qq, other} |
| `alt_ids` | 否 | array，最多 10 个，每个 1-100 字 |
| `nature` | ✅ | string，1-50 字 |
| `goods_type` | 否 | string，≤ 200 字 |
| `ship_from` | ✅ | string，1-100 字 |
| `price_range` | 否 | string，≤ 50 字 |
| `victim_count` | 否 | int 1-99999（默认 1） |
| `notes` | ✅ | string，**20-5000 字**（min 20 是关键） |
| `contact` | 否 | string，≤ 200 字 |

错误返回：`{ ok: false, error: "<描述>" }` + HTTP 400。
GitHub API 失败：HTTP 502 + `{ ok: false, error: "...", detail: "..." }`。
方法非 POST：HTTP 405。
环境变量缺失：HTTP 500 + 「服务端未配置 GitHub 凭据」。

---

## 5. 测试任务

按段做。**没浏览器能力（Playwright/Puppeteer）就跳过 B 段，做 C/D/E 即可**。

### A. Smoke test（必做，5 分钟）

| ID | 步骤 | 期望 |
|---|---|---|
| A1 | `curl -sI https://antguatian.pages.dev/` | HTTP 200，Content-Type html，response header 含 `content-security-policy` |
| A2 | `curl -s https://antguatian.pages.dev/data.json \| jq '.records \| length'` | 4 |
| A3 | `curl -sI https://antguatian.pages.dev/disclaimer.html` | HTTP 200 |
| A4 | `curl -sI https://antguatian.pages.dev/robots.txt` | HTTP 200 + body 含 `Disallow: /` |
| A5 | `curl -sX GET https://antguatian.pages.dev/api/submit` | HTTP 405，body `{ok:false, error: ...}` |

### B. 前端交互（仅当你能跑浏览器）

打开 https://antguatian.pages.dev：

| ID | 操作 | 期望 |
|---|---|---|
| B1 | 表格渲染 | 4 行，列顺序：主 ID / 性质 / 发货地 / 商品类型 / 价位 / 受骗人数 |
| B2 | 排序下拉切换「最近录入 ↓」 | 行顺序变化 |
| B3 | 筛选「性质」下拉选「卷款跑路」 | 只剩 1 行 |
| B4 | 筛选「发货地」选「北京」 | 剩 2 行（清空性质筛选） |
| B5 | 搜索框输入 `scammer` | 命中 wxid_antscam_a88（alt_ids 含 x_scammer_88） |
| B6 | 搜索框输入 `北京` | 命中 2 行（搜索覆盖 notes 等字段，可能更多） |
| B7 | 点表格任一行 | 该行下方展开详情（关联 ID + 备注 + 录入时间） |
| B8 | 再点同一行 | 详情收起 |
| B9 | 投稿表单提交（见下方"测试投稿规则"） | 跳出 issue URL 提示，issue 真的在 GitHub repo 出现 |
| B10 | 提交时 notes 留空 | 浏览器 HTML5 必填校验拦下，不发请求 |
| B11 | 提交时 notes < 20 字 | 浏览器 HTML5 `minlength=20` 拦下 **或** 后端 400 返回 + 前端显示「notes 至少 20 字...」，任一即 PASS（前者是 fail-fast 更好的实现） |

### C. `/api/submit` API 测试（必做）

**测试投稿规则**（所有 POST 必须满足）：
- `id` 以 `codex_test_` 开头（例 `codex_test_001`）
- `notes` 第一行写 `[CODEX TEST]`，后面随便，但总长 ≥ 20 字
- 这样站长能一眼识别并 close

| ID | payload | 期望响应 |
|---|---|---|
| C1 happy path | 合法完整字段，UTF-8 中文 | 200 `{ok:true, issue_url, issue_number}`，访问 issue_url 看内容对齐 |
| C2 缺 id | 删 id 字段 | 400 `{ok:false, error: "id 必填..."}` |
| C3 缺 platform | 删 platform | 400 `error: "platform 必须是 ..."` |
| C4 platform 越界 | `"platform": "weibo"` | 400 同上 |
| C5 缺 nature | 删 nature | 400 `error: "nature 必填..."` |
| C6 缺 ship_from | 删 ship_from | 400 `error: "ship_from 必填..."` |
| C7 notes 短 | `"notes": "短"` | 400 `error: "notes 至少 20 字..."` |
| C8 notes 极长 | notes = "x".repeat(5001) | 400 `error: "notes 最长 5000 字"` |
| C9 alt_ids 超 10 | 11 个元素的 alt_ids | 400 `error: "alt_ids 最多 10 个"` |
| C10 victim_count 越界 | `"victim_count": 0` 或 `-1` 或 `100000` | 400 |
| C11 victim_count 非整数 | `"victim_count": 1.5` | 400 |
| C12 alt_ids 非数组 | `"alt_ids": "a,b,c"` | 400 `error: "alt_ids 必须是数组"` |
| C13 非 JSON | `--data-binary "not json"` + JSON header | 400 `error: "请求体不是合法 JSON"` |
| C14 GET 方法 | `curl -sX GET .../api/submit` | 405 |
| C15 OPTIONS preflight | `curl -sX OPTIONS ...` | 405 或 200，看实现（这条仅观察，不算 fail） |
| C16 UTF-8 中文 | nature/notes/ship_from 全中文 | 200 + issue body 里中文显示正确（**用 file + --data-binary，不要直接命令行单引号塞中文**，会被终端 codepage 干扰） |

### D. 静态资源 / HTTP 头（必做）

`curl -sI https://antguatian.pages.dev/` 检查 response headers：

| ID | header | 期望 |
|---|---|---|
| D1 | `X-Robots-Tag` | 含 `noindex, nofollow, noarchive, nosnippet` |
| D2 | `Referrer-Policy` | `no-referrer` |
| D3 | `X-Content-Type-Options` | `nosniff` |
| D4 | `X-Frame-Options` | `DENY` |
| D5 | `Content-Security-Policy` | 含 `default-src 'self'`、`frame-ancestors 'none'` |
| D6 | `Permissions-Policy` | 含 `interest-cohort=()` |

特定路径：

| ID | 路径 | 期望 |
|---|---|---|
| D7 | `/data.json` | `Cache-Control` 含 `max-age=300` + `X-Robots-Tag` noindex |
| D8 | `/styles.css` | Content-Type text/css |
| D9 | `/app.js` | Content-Type application/javascript |

### E. GitHub 集成（必做）

每次 C 段成功投稿后：

| ID | 检查项 | 期望 |
|---|---|---|
| E1 | issue 真存在 | `gh issue view <N> --repo freetabris/antguatian` 不报错 |
| E2 | title | `[投稿] <id> (<nature>)` 格式 |
| E3 | labels | 含 `pending-review` 和 `from-form` |
| E4 | body 字段 | 含「主 ID / 平台 / 性质 / 商品类型 / 发货地 / 价位 / 受骗人数 / 备注 / 来源」 |
| E5 | UTF-8 | 中文字段（C16）非乱码 |
| E6 | 末尾 | 含 `来源: 网页表单 (/api/submit)` |

---

## 6. 你**不要**做的事

- ❌ 不要 `git push`、不要改 main 分支
- ❌ 不要修改 `public/data.json`
- ❌ 不要修改 `.github/`、`functions/`、`tools/` 下任何文件
- ❌ 不要尝试读取 CF Pages 的 `GITHUB_TOKEN`（你拿不到也别试）
- ❌ 不要在测试投稿里写真人信息 / 真实诈骗举报 —— 站长正在用真号审核
- ❌ 不要打开 `pending-review` 标签下的非 `codex_test_*` issue
- ❌ 不要 close 不是你开的 issue

允许做：
- ✅ 任意次 GET / curl 静态资源
- ✅ POST `/api/submit` 投合规测试稿（id 以 `codex_test_` 开头，notes 含 `[CODEX TEST]`）
- ✅ `gh issue view` 任意 issue
- ✅ `git log` / `git diff` / `git status`（只读）
- ✅ 读 repo 内任何文件

---

## 7. 输出格式

把测试结果输出成一份 markdown 报告，文件名 `TESTING_REPORT.md`，结构：

```markdown
# 蚁圈瓜田 测试报告

测试时间：YYYY-MM-DD HH:MM UTC
执行人：Codex（或你的标识）
环境：https://antguatian.pages.dev
浏览器测试：是 / 否（说明原因）

## 总览
- 通过：X
- 失败：Y
- 跳过：Z

## A 段（Smoke test）
- A1 ✅ HTTP 200 + CSP 头出现
- A2 ✅ records 数组长度 4
- ...

## B 段
- B1 ✅ / SKIP（无浏览器）
- ...

## C 段
- C1 ✅ issue #5 已开
- C7 ❌ 期望 400 但返回 200，详情：...
- ...

## D / E 段
...

## 发现的 Bug
1. **[严重度 P0/P1/P2/P3] 标题**
   - 重现：
   - 期望：
   - 实际：
   - 涉及文件 / 行：

## 备注
[任何观察、改进建议、值得跟站长讨论的点]
```

提交方式：直接在 `E:\cc\antguatian\TESTING_REPORT.md` 写入。**不要 push**，站长会自己看。

---

## 8. 提示

- C 段 / E 段会创建一批测试 issue（label `from-form`），站长事后批量 close
- 中文用 UTF-8 文件 + `curl --data-binary @file.json`，**不要**用 shell 单引号直接塞中文，Windows Git Bash 默认 GBK 会乱码
- 用 `gh issue list --repo freetabris/antguatian --label from-form --state open` 看你刚开的所有 issue
- 测试期间如果你的 IP 被 CF 临时限流（429），sleep 30s 重试，不是你 bug
- 如果发现 `error: "服务端未配置 GitHub 凭据"` 类的 500，**先停**，让站长确认 CF Pages 环境变量状态再继续
