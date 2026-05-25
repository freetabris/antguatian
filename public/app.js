// 蚁圈诈骗黑名单 - 前端
// 数据源：/data.json (version 2，扁平 records 数组)
// 投稿：POST /api/submit → CF Pages Function 调 GitHub Issues API 开单

const PLATFORM_LABELS = {
  wechat: "微信",
  xianyu: "闲鱼",
  phone: "手机",
  qq: "QQ",
  other: "其它",
};

const state = {
  records: [],
  generated_at: null,
  view: [],     // 应用筛选/排序后的视图
  expanded: new Set(),
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
    $("#meta-count").textContent = `数据加载失败：${err.message}`;
    return;
  }
  populateFilters();
  attachListeners();
  refresh();
}

function populateFilters() {
  const natures = uniq(state.records.map((r) => r.nature)).sort();
  const ships = uniq(state.records.map((r) => r.ship_from)).sort();

  const nSel = $("#f-nature");
  natures.forEach((n) => nSel.appendChild(new Option(`性质：${n}`, n)));

  const sSel = $("#f-ship");
  ships.forEach((s) => sSel.appendChild(new Option(`发货地：${s}`, s)));
}

function attachListeners() {
  ["#q", "#f-nature", "#f-ship", "#sort"].forEach((sel) => {
    $(sel).addEventListener("input", refresh);
    $(sel).addEventListener("change", refresh);
  });
  $("#sf").addEventListener("submit", handleSubmit);
}

function refresh() {
  const q = $("#q").value.trim().toLowerCase();
  const fn = $("#f-nature").value;
  const fs = $("#f-ship").value;
  const sort = $("#sort").value;

  let list = state.records.slice();

  if (fn) list = list.filter((r) => r.nature === fn);
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

  renderMeta();
  renderTable();
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

function strCmp(a, b) {
  return (a || "").localeCompare(b || "", "zh-Hans-CN");
}

function uniq(arr) {
  return Array.from(new Set(arr.filter((x) => x != null && x !== "")));
}

function renderMeta() {
  const total = state.records.length;
  const shown = state.view.length;
  $("#meta-count").textContent =
    shown === total ? `共 ${total} 条记录` : `${shown} / ${total} 条`;
  const updated = state.generated_at ? state.generated_at.slice(0, 10) : "";
  $("#meta-updated").textContent = updated ? `· 数据更新 ${updated}` : "";
}

function renderTable() {
  const tb = $("#tb");
  tb.innerHTML = "";
  if (state.view.length === 0) {
    $("#empty").hidden = false;
    return;
  }
  $("#empty").hidden = true;

  state.view.forEach((r) => {
    const tr = document.createElement("tr");
    tr.className = "row-main";
    tr.dataset.id = r.id;
    tr.innerHTML = `
      <td>
        <code class="id">${escapeHtml(r.id)}</code>
        <span class="platform-tag">${escapeHtml(PLATFORM_LABELS[r.platform] || r.platform)}</span>
      </td>
      <td>${escapeHtml(r.nature)}</td>
      <td>${escapeHtml(r.ship_from)}</td>
      <td class="truncate">${escapeHtml(r.goods_type || "—")}</td>
      <td>${escapeHtml(r.price_range || "—")}</td>
      <td class="num"><strong>${r.victim_count || 0}</strong></td>
    `;
    tr.addEventListener("click", () => toggle(r.id));
    tb.appendChild(tr);

    const dtr = document.createElement("tr");
    dtr.className = "row-detail";
    dtr.hidden = !state.expanded.has(r.id);
    dtr.innerHTML = `<td colspan="6">${renderDetail(r)}</td>`;
    tb.appendChild(dtr);
  });
}

function toggle(id) {
  if (state.expanded.has(id)) {
    state.expanded.delete(id);
  } else {
    state.expanded.add(id);
  }
  renderTable();
}

function renderDetail(r) {
  const parts = [];
  if (r.alt_ids && r.alt_ids.length > 0) {
    parts.push(
      `<div class="detail-row"><span class="lbl">关联 ID：</span>${r.alt_ids.map((x) => `<code>${escapeHtml(x)}</code>`).join(" / ")}</div>`,
    );
  }
  parts.push(
    `<div class="detail-row"><span class="lbl">备注：</span><div class="notes">${escapeHtml(r.notes || "").replace(/\n/g, "<br>")}</div></div>`,
  );
  if (r.added_at) {
    parts.push(`<div class="detail-row muted">录入：${escapeHtml(r.added_at.slice(0, 10))}</div>`);
  }
  return parts.join("");
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
    msg.innerHTML = `✓ 已提交，等待站长审核：<a href="${escapeAttr(j.issue_url)}" target="_blank" rel="noopener">issue #${j.issue_number}</a>`;
    msg.className = "ok";
    e.target.reset();
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
function escapeAttr(s) {
  return escapeHtml(s);
}

init();
