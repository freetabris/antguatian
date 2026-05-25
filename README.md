# hei-zine：蚁圈交易纠纷查询站

> 用户输入商家 ID（微信 / 闲鱼 / 手机 / QQ），返回圈内人工核实的纠纷记录。
> 纯静态站，部署在 Cloudflare Pages，每月费用 $0。

## 一、为什么存在

蚂蚁爱好者圈子里的二手活体 / 配件交易高度依赖私下转账，没有担保平台、没有官方维权渠道。圈内会反复出现「卷款跑路」「货不对版拉黑」的案例，但单个买家被骗后只能在小群里口口相传，下一个买家照样掉坑。

本站尝试做一件小事：把圈内已经发生且经独立编辑人核实的交易纠纷整合成一张**可查询的脱敏表**，让圈外的潜在买家在交易前用对方 ID 查一下，避开已知的高风险商家。

**本站不是消费维权平台，也不是法律渠道**。它只是一份用静态网页托管的、有持续更新责任的圈内黑名单。

---

## 二、运营原则（这些不会改）

- **匿名运营**：编辑人通过 freetabris GitHub 账号维护代码，但站点本身不署名、不卖货、不接广告
- **不收钱**：投稿费、会员费、删帖费、捐赠（含加密货币）一律拒绝
- **不撮合交易**：本站不做中介、不背书任何商家
- **永久撤稿权**：商家或第三方任何时候提供有效反证，立即撤稿
- **72 小时申诉期**：发布前主动联系被曝光商家
- **双轨曝光**：
  - **dispute**（商家纠纷）—— 默认，**仅哈希 + 脱敏 ID** 入库，下载 `data.json` 也拿不到原文
  - **fraud**（纯诈骗）—— 需有报案回执 / 判决书 / 监管处罚 / 平台诈骗认定 4 选 1 硬证据，整个商家档案升明文
- **敏感词拦截**：物种学名 / 走私 / 海关 / 检疫 / 原产地 / 侮辱词全部在录入和查询两层过滤
- **不在国内社媒宣传**：朋友圈 / 微博 / 贴吧不发链接

详细规则见 [public/disclaimer.html](public/disclaimer.html)。

---

## 三、技术栈

```
[用户浏览器]
   ↓
[Cloudflare CDN / Pages]
   ├─ index.html / styles.css / app.js
   └─ data.json   ← 唯一数据源，前端 fetch 后客户端 hash 比对
```

- **零后端**：所有查询逻辑在浏览器里跑（SHA-256 由 `crypto.subtle` 算）
- **零运行时账单**：CF Pages 免费层覆盖蚂蚁圈这点流量
- **编辑流程**：本地 `python tools/add-record.py` 录入 → git commit + push → CF Pages 自动部署

---

## 四、目录结构

```
hei/
├── README.md
├── public/                    Cloudflare Pages 部署目录
│   ├── index.html             查询主页
│   ├── styles.css
│   ├── app.js                 客户端查询（normalize + sha256 + JSON 匹配）
│   ├── data.json              唯一数据源（公开）
│   ├── disclaimer.html        投稿/申诉/免责一站式说明
│   ├── robots.txt             禁止所有爬虫
│   └── _headers               CF Pages HTTP 头规则（X-Robots-Tag 等）
└── tools/
    └── add-record.py          交互式录入工具（hash + 脱敏 + 追加 JSON）
```

---

## 五、本地预览

任何静态服务器都能跑。例如：

```bash
cd hei
python -m http.server --directory public 8000
# 浏览器打开 http://127.0.0.1:8000
```

测试 ID（来自 `data.json` 种子数据）：

| 输入 | 类型 | 预期结果 |
|---|---|---|
| `wxid_l_023` | wechat | dispute / 脱敏 W***23 / 2 件投诉 |
| `x_088` | xianyu | dispute / 脱敏 X***88 / 1 件投诉 |
| `wxid_antscam_a88` | wechat | **fraud / 明文** / 3 件投诉（含 2 件硬证据 fraud） |
| `wxid_w_156` | wechat | 圈内无该 ID 纠纷记录 |

---

## 六、录入新纠纷（编辑人专用）

```bash
python tools/add-record.py
```

引导式填字段：商家 ID → 类型 → 严重度（dispute / fraud）→ 纠纷类型 → 金额 → 月份 → 摘要 → 证据数。

工具会：
- 自动跑敏感词检查
- 算 `sha256(normalized)[:16]` 哈希
- 算脱敏 `display_id`（W***23 等）
- 找现有商家或新建
- 算下个月度顺位案号（`YYYY-MM-NNN`）
- 原子写入 `public/data.json`
- 提示 `git add + commit` 一行命令

fraud 必须选硬证据类型（报案回执 / 判决书 / 监管处罚 / 平台诈骗认定）。dispute 不需要。

可选 `--dry-run` 只看预览不写。

---

## 七、部署到 Cloudflare Pages

### 一次性配置

1. 把这个 repo 推到 GitHub（私有或公开都行）
2. 登录 [dash.cloudflare.com](https://dash.cloudflare.com) → Workers & Pages → Create → Pages → Connect to Git
3. 选 `hei` 仓库
4. 配置：
   - **Production branch**: `main`
   - **Build command**: (留空)
   - **Build output directory**: `public`
5. Deploy。CF 会给一个 `*.pages.dev` 域名。
6. （可选）Custom domains → 绑你的自定义域名。

### 日常更新

```bash
python tools/add-record.py              # 录入新案
git add public/data.json
git commit -m "案 2026-05-007 wxid_xxx dispute 不发货"
git push                                # CF Pages 自动重新部署
```

整个发布链路在 30 秒内完成。

---

## 八、数据结构

`public/data.json`：

```json
{
  "version": 1,
  "generated_at": "ISO8601 UTC",
  "merchants": [
    {
      "id_hash": "0890c0ffd19a049f",       // sha256(normalize(raw_id))[:16]
      "id_type": "wechat",                 // wechat/xianyu/phone/qq/other
      "display_id": "W***23",              // 脱敏 ID
      "display_mode": "mask",              // mask(默认) | plain(fraud 等级)
      "raw_id_plain": "",                  // 仅 plain 模式填明文
      "alt_hashes": [],                    // 同一商家的其它账号 hash
      "first_seen_month": "2026-04",
      "last_updated_month": "2026-05",
      "score": 2.0,                        // 1-5 综合评分（保留字段）
      "withdrawn_count": 0,
      "stats": {                           // 由 add-record.py 自动重算
        "published": 2, "fraud": 0,
        "disputed": 1, "total_amount_yuan": 2080
      },
      "complaints": [
        {
          "case_number": "2026-05-001",
          "severity": "dispute",           // dispute | fraud
          "hard_evidence": "",             // fraud 时必填硬证据类型
          "dispute_type": "不发货",
          "amount_yuan": 1280,
          "occurred_month": "2026-04",
          "status": "published",           // published | disputed | withdrawn
          "summary": "...",
          "evidence_count": 4,
          "appeals": [/* 商家或第三方的反证 */]
        }
      ]
    }
  ]
}
```

归一化规则（与 `app.js` / `add-record.py` 一致）：

| id_type | normalize | 说明 |
|---|---|---|
| wechat | trim → lower → 去 `\s` 及 U+200B-200F | 微信号大小写不敏感 |
| xianyu / qq | trim → lower → 去空白 | 同上 |
| phone | 仅留数字，去 86 国际前缀（13 位时） | 适配各种 +86 / 086 写法 |
| other | trim → lower | 兜底 |

---

## 九、二期可考虑

只在「真有人用 + 有运营压力」时再做：

- 跨账号合并工具（一个商家用微信 + 闲鱼 + 手机 3 个账号）
- 公示 PGP 邮箱接收匿名投稿
- 撤稿 / 申诉的版本化（git 历史本身已经够用）
- 站方公告页（pgp 指纹 / 最新撤稿 / 月度统计）

---

## 十、License

代码：MIT。
内容（data.json 的纠纷记录文本）：CC BY-NC-ND 4.0。

详见 [public/disclaimer.html](public/disclaimer.html)。
