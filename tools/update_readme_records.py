#!/usr/bin/env python3
"""把 README.md 中「当前在录」段从 public/data.json 自动重生成。

由 .github/workflows/update-readme.yml 在 data.json 变化时触发。
本地也可手动跑测试 / dry-run。

只动 README.md 里被 <!-- BEGIN_RECORDS --> / <!-- END_RECORDS -->
包起来的那段。其它部分一字不动。

依赖：Python stdlib only。
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
DATA = ROOT / "public" / "data.json"

BEGIN = "<!-- BEGIN_RECORDS -->"
END = "<!-- END_RECORDS -->"

PLATFORM_LABELS = {
    "wechat": "微信",
    "xianyu": "闲鱼",
    "phone": "手机",
    "qq": "QQ",
    "other": "其它",
}


def md_escape(s):
    """转义 markdown 表格里会捣乱的字符（| 和换行）。"""
    return str(s).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def build_section(data):
    records = data.get("records", [])
    if not records:
        return "\n> 暂无记录，等候首条投稿。\n"

    records_sorted = sorted(
        records,
        key=lambda r: (-(r.get("victim_count", 0) or 0), r.get("id", "")),
    )
    updated = (data.get("generated_at") or "")[:10]

    lines = [
        "",
        f"当前在录 **{len(records)}** 条 · 数据更新 {updated}",
        "",
        "| 主 ID | 平台 | 性质 | 发货地 | 受骗 | 录入 |",
        "|---|---|---|---|---:|---|",
    ]
    for r in records_sorted:
        platform = PLATFORM_LABELS.get(r.get("platform", ""), r.get("platform", ""))
        added = (r.get("added_at") or "")[:10]
        lines.append(
            f"| `{md_escape(r.get('id', ''))}` "
            f"| {md_escape(platform)} "
            f"| {md_escape(r.get('nature', ''))} "
            f"| {md_escape(r.get('ship_from', ''))} "
            f"| {r.get('victim_count', 0) or 0} "
            f"| {added} |"
        )
    lines.append("")
    return "\n".join(lines)


def update_readme(section, dry_run=False):
    content = README.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(BEGIN) + r".*?" + re.escape(END),
        re.DOTALL,
    )
    if not pattern.search(content):
        print(
            f"! README 缺标记 {BEGIN} / {END}，无法定位段落",
            file=sys.stderr,
        )
        return False, "missing_markers"
    new_block = f"{BEGIN}{section}{END}"
    new_content = pattern.sub(new_block, content)
    if new_content == content:
        return False, "no_change"
    if dry_run:
        return True, "would_change"
    README.write_text(new_content, encoding="utf-8")
    return True, "updated"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只 print 不写")
    args = ap.parse_args()

    if not DATA.exists():
        print(f"! data.json 不存在: {DATA}", file=sys.stderr)
        sys.exit(1)
    if not README.exists():
        print(f"! README.md 不存在: {README}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(DATA.read_text(encoding="utf-8"))
    section = build_section(data)

    if args.dry_run:
        print("--- generated section ---")
        print(section)
        print("--- end ---")
        return

    changed, why = update_readme(section)
    n = len(data.get("records", []))
    if changed:
        print(f"✓ README.md 已更新（{n} 条记录, status={why}）")
    else:
        print(f"- README.md 无变化（{n} 条记录, status={why}）")
        if why == "missing_markers":
            sys.exit(2)


if __name__ == "__main__":
    main()
