// 蚁圈交易纠纷查询 - 纯前端
// 数据源：/data.json（公开 JSON，下载也只能拿到 dispute 类的 ID 哈希）
// 查询流程：用户输入 → normalize → sha256[:16] → 在 data.json 找匹配 merchant
//
// 注意：fraud 类商家的 raw_id_plain 是明文公示的（已有报案/判决/监管处罚硬证据），
// dispute 类只存 id_hash 和脱敏 display_id，下载 data.json 无法还原原 ID。

const SENSITIVE_WORDS = [
  "camponotus", "formica", "lasius", "solenopsis", "atta", "pheidole",
  "messor", "myrmecia", "oecophylla", "polyrhachis", "paraponera",
  "dorylus", "eciton",
  "走私", "入境", "海关", "检疫", "入侵物种", "国家保护", "三有动物",
  "野生动物保护", "濒危", "保护动物",
  "哥伦比亚", "巴西", "亚马逊", "马达加斯加", "刚果",
  "骗子", "垃圾", "人渣", "傻逼", "废物",
];

let cachedData = null;

async function loadData() {
  if (cachedData) return cachedData;
  const r = await fetch("/data.json", { cache: "no-store" });
  if (!r.ok) throw new Error(`data.json HTTP ${r.status}`);
  cachedData = await r.json();
  return cachedData;
}

function containsSensitive(text) {
  const lower = text.toLowerCase();
  for (const w of SENSITIVE_WORDS) {
    if (lower.includes(w.toLowerCase())) return w;
  }
  return null;
}

function normalizeId(rawId, idType) {
  let s = (rawId || "").trim().toLowerCase();
  if (idType === "phone") {
    s = s.replace(/\D/g, "");
    if (s.startsWith("86") && s.length === 13) s = s.slice(2);
  } else if (idType === "wechat") {
    s = s.replace(/[\s​-‏]/g, "");
  } else if (idType === "xianyu" || idType === "qq") {
    s = s.replace(/\s/g, "");
  }
  return s;
}

async function sha256Prefix16(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 16);
}

async function lookupMerchant(rawId, idType) {
  const data = await loadData();
  const normalized = normalizeId(rawId, idType);
  if (!normalized) return null;
  const hash = await sha256Prefix16(normalized);
  for (const m of data.merchants) {
    if (m.id_hash === hash) return m;
    if (Array.isArray(m.alt_hashes) && m.alt_hashes.includes(hash)) return m;
  }
  return null;
}

const form = document.getElementById("qf");
const resultEl = document.getElementById("result");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("qid").value.trim();
  const type = document.getElementById("qtype").value;
  if (!id) return;

  const sensitive = containsSensitive(id);
  if (sensitive) {
    resultEl.classList.remove("hidden");
    resultEl.innerHTML = `
      <div class="result-card">
        <p>查询内容含敏感词「${escapeHtml(sensitive)}」，本站不接受涉及物种名、走私/监管、原产地等关键词的查询。</p>
      </div>`;
    return;
  }

  resultEl.classList.remove("hidden");
  resultEl.innerHTML = '<div class="result-card"><p>查询中…</p></div>';

  try {
    const m = await lookupMerchant(id, type);
    resultEl.innerHTML = m ? renderFound(m) : renderNotFound();
  } catch (err) {
    resultEl.innerHTML = `<div class="result-card"><p>数据加载失败：${escapeHtml(String(err))}</p></div>`;
  }
});

function renderNotFound() {
  return `
    <div class="result-card no-record">
      <h2>圈内无该 ID 纠纷记录</h2>
      <p>本站收录的是已被独立编辑人审核的圈内交易纠纷。「无记录」≠「可信」，请仍按证据保全规则交易（聊天/转账/物流/可识别 ID 截图）。</p>
    </div>`;
}

function renderFound(m) {
  const stats = m.stats || { published: 0, fraud: 0, disputed: 0, total_amount_yuan: 0 };
  const isFraud = m.display_mode === "plain" || stats.fraud > 0;
  const displayName = isFraud && m.raw_id_plain ? m.raw_id_plain : m.display_id;

  const cardClass = isFraud ? "fraud-record" : "has-record";
  const fraudBanner = isFraud
    ? `<div class="fraud-banner">⚠️ 该商家被认定为涉嫌纯诈骗（含报案 / 判决 / 监管处罚类硬证据），ID 已明文展示。详见下方 fraud 案件的硬证据类型。</div>`
    : "";

  const head = `
    <div class="result-card ${cardClass}">
      ${fraudBanner}
      <h2>查询结果：<span class="display-id ${isFraud ? "plain" : ""}">${escapeHtml(displayName)}</span>（${escapeHtml(idTypeLabel(m.id_type))}）</h2>
      <div class="summary-row">
        <span>已发布投诉：<strong>${stats.published}</strong> 件</span>
        ${stats.fraud > 0 ? `<span class="fraud-stat">其中诈骗类：<strong>${stats.fraud}</strong> 件</span>` : ""}
        ${stats.disputed > 0 ? `<span>商家申诉中：<strong>${stats.disputed}</strong> 件</span>` : ""}
        <span>累计纠纷金额：<strong>¥${(stats.total_amount_yuan || 0).toLocaleString()}</strong></span>
        <span>首次入库：<strong>${escapeHtml(m.first_seen_month)}</strong></span>
        <span>最近更新：<strong>${escapeHtml(m.last_updated_month)}</strong></span>
      </div>
      ${m.withdrawn_count > 0 ? `<p class="muted" style="font-size:0.85rem;">注：另有 ${m.withdrawn_count} 件已撤稿（商家提供有效反证）。</p>` : ""}
    </div>`;

  const cards = (m.complaints || []).map(renderComplaint).join("");
  return head + cards;
}

function renderComplaint(c) {
  const isFraud = c.severity === "fraud";
  const statusClass = isFraud
    ? "fraud"
    : (c.status === "disputed" ? "disputed" : "published");
  const statusLabel = c.status === "disputed" ? "商家申诉中" : (c.status === "withdrawn" ? "已撤稿" : "已发布");
  const severityLabel = isFraud ? "诈骗" : "商家纠纷";
  const hardLabel = {
    police_report: "📄 报案回执",
    court_verdict: "⚖️ 法院判决书",
    regulator_penalty: "🚫 监管处罚通知",
    platform_fraud_ruling: "💬 平台诈骗认定",
  }[c.hard_evidence] || "";
  const appeals = (c.appeals || []).map(renderAppeal).join("");
  return `
    <div class="complaint ${statusClass}">
      <div class="meta">
        <span class="case-num">${escapeHtml(c.case_number)}</span>
        ${isFraud ? `｜ <span class="badge-fraud">${escapeHtml(severityLabel)}</span>` : `｜ <span class="badge-dispute">${escapeHtml(severityLabel)}</span>`}
        ｜ ${escapeHtml(c.dispute_type)}
        ｜ ¥${(c.amount_yuan || 0).toLocaleString()}
        ｜ 发生于 ${escapeHtml(c.occurred_month)}
        ｜ 状态：${escapeHtml(statusLabel)}
        ${hardLabel ? `｜ 硬证据：${escapeHtml(hardLabel)}` : ""}
      </div>
      <div class="summary">${escapeHtml(c.summary)}</div>
      ${appeals}
    </div>`;
}

function renderAppeal(a) {
  const typeLabel = {
    not_happened: "称该交易不存在",
    fulfilled: "称已正常履约",
    misrepresented: "称投诉有重大失实",
    settled: "称双方已和解",
    identity_misuse: "称投稿人身份冒用",
  }[a.appeal_type] || a.appeal_type;
  const resolutionLabel = {
    withdrawn: "本站已撤稿",
    modified: "本站已修改细节",
    appended: "本站已追加更正声明",
    rejected: "本站审核后未采信",
    pending: "处理中",
  }[a.resolution] || a.resolution;
  return `
    <div class="appeal">
      <span class="label">商家申诉：</span>
      ${escapeHtml(typeLabel)}（${escapeHtml(a.filed_month)}）→ ${escapeHtml(resolutionLabel)}
      <div style="margin-top:0.3rem;">${escapeHtml(a.note)}</div>
    </div>`;
}

function idTypeLabel(t) {
  return { wechat: "微信", xianyu: "闲鱼", phone: "手机", qq: "QQ", other: "其它" }[t] || t;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
