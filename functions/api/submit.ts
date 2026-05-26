/**
 * Cloudflare Pages Function: POST /api/submit
 *
 * 接前端投稿表单 → 字段校验 → 调 GitHub Issues API 开 Issue → 返回 issue URL。
 *
 * 部署：放在仓库根的 functions/api/submit.ts，CF Pages 自动识别并路由到 /api/submit。
 *
 * 环境变量（在 CF Pages dashboard 配置，不要写在代码里）：
 *   GITHUB_TOKEN  - fine-grained PAT，权限只勾 'Issues: Read and write'，repo 选 freetabris/antguatian
 *   GITHUB_OWNER  - 'freetabris'
 *   GITHUB_REPO   - 'antguatian'
 */

interface Env {
  GITHUB_TOKEN: string;
  GITHUB_OWNER: string;
  GITHUB_REPO: string;
}

interface SubmissionPayload {
  id?: unknown;
  platform?: unknown;
  alt_ids?: unknown;
  nature?: unknown;
  goods_type?: unknown;
  ship_from?: unknown;
  price_range?: unknown;
  victim_count?: unknown;
  notes?: unknown;
  contact?: unknown;
}

interface Submission {
  id: string;
  platform: string;
  alt_ids: string[];
  nature: string;
  goods_type: string;
  ship_from: string;
  price_range: string;
  victim_count: number;
  notes: string;
  contact: string;
}

const PLATFORMS = new Set(["wechat", "xianyu", "phone", "qq", "other"]);

const LIMITS = {
  id: 100,
  alt_id: 100,
  alt_ids_count: 10,
  nature: 50,
  goods_type: 200,
  ship_from: 100,
  price_range: 50,
  notes_min: 20,
  notes_max: 5000,
  contact: 200,
  victim_count_max: 99999,
};

function jsonResponse(status: number, body: Record<string, unknown>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

function trimStr(v: unknown, max: number): string | null {
  if (typeof v !== "string") return null;
  const t = v.trim();
  if (t.length === 0 || t.length > max) return null;
  return t;
}

function validate(body: SubmissionPayload): { ok: true; data: Submission } | { ok: false; error: string } {
  const id = trimStr(body.id, LIMITS.id);
  if (!id) return { ok: false, error: "id 必填且长度 1-100" };

  if (typeof body.platform !== "string" || !PLATFORMS.has(body.platform)) {
    return { ok: false, error: "platform 必须是 wechat / xianyu / phone / qq / other" };
  }
  const platform = body.platform;

  let alt_ids: string[] = [];
  if (body.alt_ids !== undefined && body.alt_ids !== null) {
    if (!Array.isArray(body.alt_ids)) return { ok: false, error: "alt_ids 必须是数组" };
    if (body.alt_ids.length > LIMITS.alt_ids_count) {
      return { ok: false, error: `alt_ids 最多 ${LIMITS.alt_ids_count} 个` };
    }
    for (const a of body.alt_ids) {
      const t = trimStr(a, LIMITS.alt_id);
      if (!t) return { ok: false, error: "alt_ids 含空值或过长项" };
      alt_ids.push(t);
    }
  }

  const nature = trimStr(body.nature, LIMITS.nature);
  if (!nature) return { ok: false, error: "nature 必填且长度 1-50" };

  const goods_type = trimStr(body.goods_type, LIMITS.goods_type) ?? "";
  const ship_from = trimStr(body.ship_from, LIMITS.ship_from);
  if (!ship_from) return { ok: false, error: "ship_from 必填且长度 1-100" };

  const price_range = trimStr(body.price_range, LIMITS.price_range) ?? "";

  let victim_count = 1;
  if (body.victim_count !== undefined && body.victim_count !== null) {
    const n = Number(body.victim_count);
    if (!Number.isInteger(n) || n < 1 || n > LIMITS.victim_count_max) {
      return { ok: false, error: `victim_count 必须是 1-${LIMITS.victim_count_max} 的整数` };
    }
    victim_count = n;
  }

  const notes = typeof body.notes === "string" ? body.notes.trim() : "";
  if (notes.length < LIMITS.notes_min) {
    return { ok: false, error: `notes 至少 ${LIMITS.notes_min} 字（说明诈骗手法 / 证据来源）` };
  }
  if (notes.length > LIMITS.notes_max) {
    return { ok: false, error: `notes 最长 ${LIMITS.notes_max} 字` };
  }

  const contact = trimStr(body.contact, LIMITS.contact) ?? "";

  return {
    ok: true,
    data: { id, platform, alt_ids, nature, goods_type, ship_from, price_range, victim_count, notes, contact },
  };
}

function buildIssueBody(s: Submission, submittedAtIso: string): string {
  const lines: string[] = [];
  lines.push(`**主 ID**: \`${s.id}\``);
  lines.push(`**平台**: ${s.platform}`);
  if (s.alt_ids.length > 0) {
    lines.push(`**关联 ID**: ${s.alt_ids.map((x) => `\`${x}\``).join(", ")}`);
  }
  lines.push(`**性质**: ${s.nature}`);
  if (s.goods_type) lines.push(`**商品类型**: ${s.goods_type}`);
  lines.push(`**发货地**: ${s.ship_from}`);
  if (s.price_range) lines.push(`**价位**: ${s.price_range}`);
  lines.push(`**受骗人数**: ${s.victim_count}`);
  lines.push("");
  lines.push("## 备注 / 证据 / 来源");
  lines.push("");
  lines.push(s.notes);
  lines.push("");
  lines.push("---");
  if (s.contact) lines.push(`联系方式: ${s.contact}`);
  lines.push(`提交时间: ${submittedAtIso}`);
  lines.push(`来源: 网页表单 (/api/submit)`);
  return lines.join("\n");
}

export const onRequestPost: PagesFunction<Env> = async (context) => {
  const { request, env } = context;

  if (!env.GITHUB_TOKEN || !env.GITHUB_OWNER || !env.GITHUB_REPO) {
    return jsonResponse(500, { ok: false, error: "服务端未配置 GitHub 凭据，请联系站长" });
  }

  let body: SubmissionPayload;
  try {
    body = await request.json();
  } catch {
    return jsonResponse(400, { ok: false, error: "请求体不是合法 JSON" });
  }

  const v = validate(body);
  if (!v.ok) return jsonResponse(400, { ok: false, error: v.error });
  const s = v.data;

  const submittedAt = new Date().toISOString();
  const title = `[投稿] ${s.id} (${s.nature})`;
  const issueBody = buildIssueBody(s, submittedAt);

  const ghUrl = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/issues`;
  const ghRes = await fetch(ghUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "antguatian-submit-bot",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title,
      body: issueBody,
      // labels 由 .github/workflows/auto-label.yml 在 issues.opened 事件里加
      // (fine-grained PAT 在 create-issue 时附 labels 会被静默忽略，权限模型问题)
    }),
  });

  if (!ghRes.ok) {
    const detail = await ghRes.text().catch(() => "");
    return jsonResponse(502, {
      ok: false,
      error: `GitHub Issue 创建失败 (${ghRes.status})`,
      detail: detail.slice(0, 500),
    });
  }

  const issue = (await ghRes.json()) as { html_url: string; number: number };
  return jsonResponse(200, {
    ok: true,
    issue_url: issue.html_url,
    issue_number: issue.number,
  });
};

export const onRequest: PagesFunction<Env> = async () => {
  return jsonResponse(405, { ok: false, error: "Method Not Allowed (use POST)" });
};
