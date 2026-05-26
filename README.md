# 蚁圈瓜田 (antguatian)

> 蚂蚁圈交易诈骗黑名单。访客查 ID / 关联 ID / 备注，按受骗人数 · 发货地 · 性质排序筛选。
> 投稿走网页表单（自动开 GitHub Issue）/ 邮件 / 圈内私聊；站长审核后录入。

完整说明在 [public/disclaimer.html](public/disclaimer.html)。

## 技术栈

- **前端**：纯静态站（HTML / CSS / 原生 JS），部署在 Cloudflare Pages
- **后端**：Cloudflare Pages Function (`functions/api/submit.ts`)，唯一作用是把前端表单转成 GitHub Issue
- **数据**：`public/data.json`（version 2 扁平 records 数组）公开维护，git 历史即审计日志

## 目录结构

```
.
├── public/                       CF Pages 部署目录
│   ├── index.html                列表 + 搜索 + 排序 + 投稿表单
│   ├── app.js / styles.css
│   ├── data.json                 唯一数据源（公开）
│   ├── disclaimer.html           投稿/申诉/免责说明
│   ├── _headers / robots.txt
├── functions/api/submit.ts       Pages Function：表单 → GitHub Issue
├── .github/ISSUE_TEMPLATE/       Issue Form 模板
└── tools/add-record.py           站长录入 CLI（审核通过后跑）
```

## 本地预览

```bash
python -m http.server --directory public 8000
# 浏览器 http://127.0.0.1:8000
# 注意：本地起的 http.server 不会跑 /api/submit Function，
# 投稿表单本地测不了，要 push 到 CF Pages 才能完整跑。
```

## 部署

CF Pages 连接 GitHub repo `freetabris/antguatian`，build output 选 `public`。
需要在 CF Pages **Settings → Variables and Secrets** 配三个变量：

| 变量名 | 类型 | 值 |
|---|---|---|
| `GITHUB_TOKEN` | Secret | Fine-grained PAT，权限只勾 `Issues: Read and write`，repo 选 `freetabris/antguatian` |
| `GITHUB_OWNER` | Plaintext | `freetabris` |
| `GITHUB_REPO` | Plaintext | `antguatian` |

## 录入新档案（站长用）

```bash
python tools/add-record.py
# 交互式填字段 → 写入 public/data.json
git add public/data.json && git commit -m "录入 wxid_xxx" && git push
# CF Pages 自动重新部署
```

## License

- 代码：MIT
- `data.json` 内容：CC BY-NC-ND 4.0

---

*页面视觉风格、文案调子还在迭代，本 README 也待重写。*
