# 蚁圈瓜田 / Formica Watch  
**只记录交易行为，不评价交易标的。**

> 一个针对蚂蚁圈私下交易欺诈的公开黑名单，无商业利益，无公关豁免。

## 为什么有这个站

蚂蚁圈活体与配件交易高度依赖私下转账（微信、闲鱼、手机号），没有担保平台，没有官方维权渠道。圈内反复出现卷款跑路、假货冒充、拒不发货的卖家。单个买家被骗只能在小群内口口相传，下一个买家照样掉坑。本站把经过独立编辑核实的诈骗案例做成可查询的黑名单，让圈内人在交易前查一下避雷。

本站不替代任何合法渠道，不是消费维权机构，不是舆论审判台。只是圈内一个相互避坑的信息汇总点。

## 运营立场

- **不收费**：投稿费、删帖费、广告、捐赠一概不接
- **不撮合交易**，不为任何商家背书
- **公开实名维护**：freetabris，不躲不藏
- **永久撤稿权** + 72 小时申诉期：被曝光方或任何第三方提供有效反证，即撤
- **不在国内社交媒体主动宣传**：不发朋友圈、微博、贴吧
- **不评价交易标的合法性**，只记录交易行为（付款、发货、拉黑、退款……）

## 三类用户怎么用

### 访客

打开 [antguatian.pages.dev](https://antguatian.pages.dev)，搜索 ID 或浏览黑名单。如果对方有记录，自己判断是否继续交易。

本站“无记录”不等于“可信”。

### 投稿者

提供三条渠道：

1. 网页表单（首页底部，自动开通 GitHub Issue）—— 最方便
2. GitHub Issue 模板：`github.com/freetabris/antguatian/issues/new`
3. 邮件或圈内私聊

#### 投稿门槛

- 至少带一条佐证（闲鱼差评页、微信聊天截图、转账记录、群证等）
- 涉案金额 ≥ 200 元
- 事发时间在 24 个月以内
- 涉事方为国内圈内卖家
- 事实陈述，不写主观定性（写“未发货”，不写“他就是骗子”）

### 站长

审核通过后，本地执行：

```bash
python tools/add-record.py
```

交互式填写字段，完成后提交推送。Cloudflare Pages 自动部署，约 60 秒上线。

## 技术栈

- 纯静态前端，部署于 Cloudflare Pages
- 唯一后端为 Pages Function `functions/api/submit.ts`，调用 GitHub Issues API 将表单转为 Issue
- 数据源 `public/data.json` 公开维护，Schema v2 扁平 records 数组
- Git 历史即审计日志
- GitHub Action `auto-label.yml` 对新 Issue 自动添加 `pending-review` 与 `from-form` 标签
### 部署（Cloudflare Pages）

1. CF Pages 连接 GitHub repo `freetabris/antguatian`，build output 设为 `public`
2. 在项目 Settings → Variables and Secrets 配三个变量：
   - `GITHUB_TOKEN`：fine-grained PAT，权限只勾 Issues: Read and write，repo 选本仓库
   - `GITHUB_OWNER`：`freetabris`
   - `GITHUB_REPO`：`antguatian`
3. push 触发自动部署，~60s 上线

## 数据与许可

- 代码：MIT
- `data.json` 内容：CC BY-NC-ND 4.0（署名 - 非商业 - 禁演绎）

## 状态

当前记录 0 条，等候真实投稿。
