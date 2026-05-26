// 蚁圈瓜田 - 主站前端
// 数据源：/data.json (version 2，扁平 records 数组)
// 投稿：POST /api/submit → CF Pages Function 调 GitHub Issues API 开单

const PLATFORM_LABELS = {
  wechat: "微信",
  xianyu: "闲鱼",
  phone:  "手机",
  qq:     "QQ",
  other:  "其它",
};

// 性质 → emoji 前缀 + 等级（决定 chip 颜色）
const NATURE_RULES = [
  { test: /卷款|跑路|失联|诈骗/, emoji: "🚩", level: "critical" },
  { test: /假货|冒充|仿冒/,       emoji: "🎭", level: "critical" },
  { test: /不发货|拉黑/,          emoji: "❌", level: "high"     },
  { test: /不对版|不补发/,        emoji: "📦", level: "medium"   },
  { test: /不退款/,               emoji: "💰", level: "medium"   },
];
function natureMeta(nature) {
  const s = String(nature || "");
  for (const r of NATURE_RULES) {
    if (r.test.test(s)) return { emoji: r.emoji, level: r.level, text: s };
  }
  return { emoji: "⚠️", level: "low", text: s };
}

const state = {
  records: [],
  generated_at: null,
  view: [],
  expanded: new Set(),
  activeNature: "",
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function init() {
  try {
    const r = await fetch("/data.json", { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    state.records = data.records || [];
    state.generated_at = data.generated_at;
  } catch (err) {
    $("#tb").innerHTML = `<div class="empty-state">数据加载失败：${escapeHtml(err.message)}</div>`;
    return;
  }
  populateChips();
  populateShipFilter();
  renderTicker();
  renderHeroStats();
  renderFooterMeta();
  attachListeners();
  refresh();
}

function populateChips() {
  const chips = $("#nature-chips");
  // 「全部」chip 已在 HTML 中
  $("#chip-count-all").textContent = pad2(state.records.length);

  // 按出现频次排序 nature
  const counts = {};
  state.records.forEach((r) => {
    const m = natureMeta(r.nature);
    const key = m.text;
    counts[key] = counts[key] || { count: 0, emoji: m.emoji };
    counts[key].count += 1;
  });
  const sorted = Object.entries(counts).sort((a, b) => b[1].count - a[1].count);

  sorted.forEach(([nature, info]) => {
    const btn = document.createElement("button");
    btn.className = "chip";
    btn.dataset.nature = nature;
    btn.innerHTML = `${info.emoji} ${escapeHtml(nature)} <span class="count">${pad2(info.count)}</span>`;
    chips.appendChild(btn);
  });

  chips.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    $$(".chips .chip").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.activeNature = btn.dataset.nature || "";
    refresh();
  });
}

function populateShipFilter() {
  const ships = uniq(state.records.map((r) => r.ship_from)).sort();
  const sel = $("#f-ship");
  ships.forEach((s) => {
    const opt = new Option(`📍 ${s}`, s);
    sel.appendChild(opt);
  });
}

function renderTicker() {
  const train = $("#ticker-train");
  const beijing = state.records.filter((r) => /北京/.test(r.ship_from || "")).length;
  const totalVictims = state.records.reduce((s, r) => s + (r.victim_count || 0), 0);
  const latest = state.records.slice().sort((a, b) =>
    (b.added_at || "").localeCompare(a.added_at || "")
  )[0];
  const latestMonth = latest && latest.added_at ? latest.added_at.slice(0, 7) : "—";

  const items = [];
  if (beijing > 0) items.push(`<span class="danger">📍 北京发货 ×${beijing}</span> · 圈内退货红线`);
  items.push(`最新档案 <b>${escapeHtml(latest ? displayId(latest.id) : "—")}</b> · ${escapeHtml(latestMonth)}`);
  items.push(`在录 <b>${state.records.length}</b> 例 · 受害合计 <b>${totalVictims}</b> 人`);
  items.push(`<span class="warn">永久撤稿权 · 申诉即查</span>`);
  items.push(`数据源 <b>/data.json</b> · 公开 · git 历史即审计`);

  // 重复一份保证无缝循环
  const html = [...items, ...items]
    .map((x) => `<span>${x}</span>`)
    .join('<span class="sep">⨯</span>');
  train.innerHTML = html;
}

function renderHeroStats() {
  const records = state.records;
  const total = records.length;
  const victims = records.reduce((s, r) => s + (r.victim_count || 0), 0);
  const beijing = records.filter((r) => /北京/.test(r.ship_from || "")).length;
  const amount = estimateAmount(records);

  $("#stat-records").innerHTML = `${pad2(total)}<span class="unit">人</span>`;
  $("#stat-victims").innerHTML = `${pad2(victims)}<span class="unit">人</span>`;
  $("#stat-amount").innerHTML = amount === null ? "—" : amount;
  $("#stat-beijing").innerHTML = `${pad2(beijing)}<span class="unit">例</span>`;

  $("#stat-records-trend").textContent = "已收档案";
  $("#stat-victims-trend").innerHTML = `<span class="arrow">▲</span> 平均 ${
    total ? Math.round(victims / total) : 0
  } 人/例`;
  $("#stat-amount-trend").textContent = "基于备注估算";
}

/** 从 price_range 文本里提取数字估算总金额 */
function estimateAmount(records) {
  let total = 0;
  let countWithPrice = 0;
  for (const r of records) {
    const s = String(r.price_range || "");
    // 提取所有数字（含 "1000-5800" 这种区间，取上限当估计）
    const nums = (s.match(/\d+/g) || []).map(Number);
    if (nums.length === 0) continue;
    const upper = Math.max(...nums);
    total += upper * (r.victim_count || 1);
    countWithPrice += 1;
  }
  if (countWithPrice === 0) return null;
  if (total >= 10000) return `¥${(total / 10000).toFixed(1)}w+`;
  return `¥${total.toLocaleString()}+`;
}

function renderFooterMeta() {
  const el = $("#footer-last-update");
  if (state.generated_at) {
    const date = state.generated_at.slice(0, 10);
    el.innerHTML = `last_update <b>${escapeHtml(date)}</b>`;
  }
}

function attachListeners() {
  ["#q", "#f-ship", "#sort"].forEach((sel) => {
    const el = $(sel);
    if (el) {
      el.addEventListener("input", refresh);
      el.addEventListener("change", refresh);
    }
  });
  $("#sf").addEventListener("submit", handleSubmit);
}

function refresh() {
  const q = $("#q").value.trim().toLowerCase();
  const fs = $("#f-ship").value;
  const sort = $("#sort").value;
  const fn = state.activeNature;

  let list = state.records.slice();

  if (fn) list = list.filter((r) => natureMeta(r.nature).text === fn);
  if (fs) list = list.filter((r) => r.ship_from === fs);

  if (q) {
    list = list.filter((r) => {
      const hay = [
        r.id,
        ...(r.alt_ids || []),
        r.notes || "",
        r.goods_type || "",
        r.nature || "",
        r.ship_from || "",
      ].join(" ").toLowerCase();
      return hay.includes(q);
    });
  }

  list.sort(comparator(sort));
  state.view = list;
  renderBoardMeta();
  renderBoard();
}

function comparator(key) {
  switch (key) {
    case "victim_count_desc":
      return (a, b) => (b.victim_count || 0) - (a.victim_count || 0) || strCmp(a.id, b.id);
    case "added_at_desc":
      return (a, b) => (b.added_at || "").localeCompare(a.added_at || "");
    case "ship_from_asc":
      return (a, b) => strCmp(a.ship_from, b.ship_from) || strCmp(a.id, b.id);
    case "nature_asc":
      return (a, b) => strCmp(a.nature, b.nature) || (b.victim_count || 0) - (a.victim_count || 0);
    default:
      return () => 0;
  }
}

function renderBoardMeta() {
  const total = state.records.length;
  const shown = state.view.length;
  const updated = state.generated_at ? state.generated_at.slice(0, 10) : "—";
  $("#board-meta").innerHTML = `last_updated: <b>${escapeHtml(updated)}</b> · ${shown}/${total} records`;
}

function renderBoard() {
  const tb = $("#tb");
  tb.innerHTML = "";

  if (state.view.length === 0) {
    tb.innerHTML = `<div class="empty-state">无匹配记录 · 试试清空筛选条件</div>`;
    return;
  }

  // 找最大 victim_count 作为进度条基准
  const maxVictim = Math.max(1, ...state.view.map((r) => r.victim_count || 0));

  state.view.forEach((r, idx) => {
    const rank = idx + 1;
    const rankClass = rank <= 3 ? `r${rank}` : "";
    const meta = natureMeta(r.nature);
    const isBeijing = /北京/.test(r.ship_from || "");
    const isExpanded = state.expanded.has(r.id);
    const victimPct = Math.round((100 * (r.victim_count || 0)) / maxVictim);
    const victimClass = r.victim_count >= 5 ? "hot" : (r.victim_count >= 2 ? "mid" : "");
    const fireEmoji = r.victim_count >= 5 ? '<span class="fire">🔥</span>' : "";

    // evidence chips：alt_ids 数 / 备注里有数字佐证就显示
    const evChips = [];
    if (r.alt_ids && r.alt_ids.length > 0) {
      evChips.push(`<span class="ev">关联号 ×${r.alt_ids.length}</span>`);
    }
    // 从 notes 文本启发抽取证据点（regex 双侧匹配，数字可在关键词前后）
    const notesStr = r.notes || "";

    // 闲鱼差评：「N 条差评」/「差评 N 条」/「N 个差评」
    const diffMatch = notesStr.match(/(\d+)\s*[条个]?\s*差评|差评[^\d]{0,8}(\d+)/);
    if (diffMatch) {
      const n = diffMatch[1] || diffMatch[2];
      evChips.push(`<span class="ev alt">闲鱼差评 ×${n}</span>`);
    }

    // 群证 / 对账：「N 名圈友/买家/对账/证人」/「微信群…N 名」
    const witMatch = notesStr.match(/(\d+)\s*[名人位个]\s*(?:圈友|买家|玩家|对账|证人|对帐)|(?:微信群|群里|群内|对账)[^\d]{0,20}(\d+)\s*[名人位个]/);
    if (witMatch) {
      const n = witMatch[1] || witMatch[2];
      evChips.push(`<span class="ev alt">群证 ×${n}</span>`);
    }

    // 首曝时间：优先从 notes 抽最早的 YYYY-MM，没有则 fallback 到 added_at
    const dateMatch = notesStr.match(/(\d{4}-\d{2})/);
    const firstSeen = dateMatch ? dateMatch[1] : (r.added_at ? r.added_at.slice(0, 7) : null);
    if (firstSeen) {
      evChips.push(`<span class="ev">首曝 ${escapeHtml(firstSeen)}</span>`);
    }

    const article = document.createElement("article");
    article.className = `entry ${rankClass} ${isExpanded ? "expanded" : ""}`.trim();
    article.dataset.id = r.id;
    article.innerHTML = `
      <div class="entry-main">
        <div class="row1">
          <code class="id">${escapeHtml(displayId(r.id))}</code>
          <span class="plat">${escapeHtml(PLATFORM_LABELS[r.platform] || r.platform || "?")}</span>
          <span class="nature ${meta.level}">${meta.emoji} ${escapeHtml(meta.text)}</span>
        </div>
        <div class="row2">
          <span class="ship ${isBeijing ? "beijing" : ""}">${escapeHtml(r.ship_from || "—")}</span>
          ${r.goods_type ? `<span class="goods">${escapeHtml(r.goods_type)}</span>` : ""}
          ${r.price_range ? `<span class="price">¥${escapeHtml(r.price_range)}</span>` : ""}
        </div>
        ${evChips.length > 0 ? `<div class="ev-bar">${evChips.join("")}</div>` : ""}
        <div class="entry-detail">
          ${r.alt_ids && r.alt_ids.length > 0 ? `
            <div class="dt-row">
              <span class="lbl">关联 ID</span>
              ${r.alt_ids.map((x) => `<code>${escapeHtml(displayId(x))}</code>`).join(" ")}
            </div>` : ""}
          <div class="dt-row">
            <span class="lbl">备注</span>
            <div class="notes-full">${escapeHtml(r.notes || "")}</div>
          </div>
          ${r.added_at ? `<div class="dt-row"><span class="lbl">录入时间</span> ${escapeHtml(r.added_at.slice(0, 10))}</div>` : ""}
        </div>
      </div>
      <div class="entry-victim">
        <div class="l">已知受害</div>
        <div class="n ${victimClass}">${r.victim_count || 0}${fireEmoji}</div>
        ${r.price_range ? `<div class="amount">¥${escapeHtml(r.price_range)}</div>` : ""}
        <div class="bar"><div class="fill" style="width:${victimPct}%; animation-delay:${0.3 + idx * 0.08}s"></div></div>
      </div>
    `;
    article.addEventListener("click", () => toggle(r.id));
    tb.appendChild(article);
  });
}

function toggle(id) {
  if (state.expanded.has(id)) state.expanded.delete(id);
  else state.expanded.add(id);
  renderBoard();
}

function strCmp(a, b) {
  return (a || "").localeCompare(b || "", "zh-Hans-CN");
}

function uniq(arr) {
  return Array.from(new Set(arr.filter((x) => x != null && x !== "")));
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

async function handleSubmit(e) {
  e.preventDefault();
  const btn = $("#sf-btn");
  const msg = $("#sf-msg");
  btn.disabled = true;
  msg.textContent = "提交中…";
  msg.className = "";

  const fd = new FormData(e.target);
  const altIdsRaw = (fd.get("alt_ids") || "").toString().trim();
  const payload = {
    id: fd.get("id"),
    platform: fd.get("platform"),
    alt_ids: altIdsRaw ? altIdsRaw.split(/\r?\n/).map((s) => s.trim()).filter(Boolean) : [],
    nature: fd.get("nature"),
    goods_type: fd.get("goods_type") || "",
    ship_from: fd.get("ship_from"),
    price_range: fd.get("price_range") || "",
    victim_count: Number(fd.get("victim_count") || 1),
    notes: fd.get("notes"),
    contact: fd.get("contact") || "",
  };

  try {
    const r = await fetch("/api/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const j = await r.json();
    if (!r.ok || !j.ok) {
      msg.textContent = `提交失败：${j.error || `HTTP ${r.status}`}`;
      msg.className = "err";
      btn.disabled = false;
      return;
    }
    msg.innerHTML = `✓ 已提交 · <a href="${escapeAttr(j.issue_url)}" target="_blank" rel="noopener">issue #${j.issue_number}</a>`;
    msg.className = "ok";
    e.target.reset();
    btn.disabled = false;
  } catch (err) {
    msg.textContent = `网络错误：${err.message}`;
    msg.className = "err";
    btn.disabled = false;
  }
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
function escapeAttr(s) { return escapeHtml(s); }

// 防御层：data.json 里手机号应在录入工具就脱敏；这里再 mask 一次，
// 防止有人手动改了 JSON 漏掉，或老数据残留明文。
function displayId(s) {
  s = String(s ?? "");
  return /^1\d{10}$/.test(s) ? s.slice(0, 3) + "****" + s.slice(-4) : s;
}

init();
