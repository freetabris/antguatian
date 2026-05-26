#!/usr/bin/env python3
"""蚁圈瓜田 - 录入工具

交互式 CLI：填字段 → 追加到 public/data.json

用法：
  python tools/add-record.py
  python tools/add-record.py --dry-run
  python tools/add-record.py --from-issue 16     从 GitHub issue 拉字段预填，按回车确认或改
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Windows console 默认 GBK，让 stdout 走 UTF-8 才能 print ✓ ⚠ 等字符
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass  # Python < 3.7

REPO = "freetabris/antguatian"


def mask_phone(s):
    """11 位手机号（1 开头）中间四位脱敏为 ****。其它格式原样返回。
    例：13800138888 → 138****8888；wxid_xxx → wxid_xxx
    """
    return re.sub(r"^(1\d{2})\d{4}(\d{4})$", r"\1****\2", (s or "").strip())


PLATFORMS = ["wechat", "xianyu", "phone", "qq", "other"]
PLATFORM_LABELS = {
    "wechat": "微信",
    "xianyu": "闲鱼",
    "phone": "手机",
    "qq": "QQ",
    "other": "其它",
}
NATURE_PRESETS = [
    "卷款跑路", "拒不发货", "假货 / 冒充", "货不对版",
    "拒不退款", "拉黑失联", "其它",
]


# ========================================================================
# 从 GitHub issue 拉字段
# ========================================================================

def fetch_issue(num):
    """用 gh CLI 拉 issue body 和 labels。返回 (body_str, labels_list) 或 (None, None)。"""
    try:
        r = subprocess.run(
            ["gh", "issue", "view", str(num),
             "--repo", REPO,
             "--json", "body,labels,title,state"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        data = json.loads(r.stdout)
        labels = [l.get("name", "") for l in data.get("labels", [])]
        return data, labels
    except subprocess.CalledProcessError as e:
        print(f"! 拉 issue #{num} 失败: {e.stderr.strip()}", file=sys.stderr)
        return None, None
    except FileNotFoundError:
        print("! gh CLI 未安装或不在 PATH，无法用 --from-issue", file=sys.stderr)
        return None, None
    except json.JSONDecodeError as e:
        print(f"! 解析 gh 输出失败: {e}", file=sys.stderr)
        return None, None


def parse_form_body(body):
    """解析网页表单（/api/submit）生成的 issue body。
    格式见 functions/api/submit.ts::buildIssueBody。
    """
    fields = {}
    patterns = {
        "id":           r"\*\*主 ID\*\*:\s*`([^`]+)`",
        "platform":     r"\*\*平台\*\*:\s*(\w+)",
        "nature":       r"\*\*性质\*\*:\s*([^\n]+)",
        "goods_type":   r"\*\*商品类型\*\*:\s*([^\n]+)",
        "ship_from":    r"\*\*发货地\*\*:\s*([^\n]+)",
        "price_range":  r"\*\*价位\*\*:\s*([^\n]+)",
        "victim_count": r"\*\*受骗人数\*\*:\s*(\d+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, body)
        if m:
            val = m.group(1).strip()
            if key == "victim_count":
                try: val = int(val)
                except ValueError: val = 1
            fields[key] = val

    # 关联 ID（多个，反引号包裹，逗号分）
    m = re.search(r"\*\*关联 ID\*\*:\s*([^\n]+)", body)
    if m:
        alts = re.findall(r"`([^`]+)`", m.group(1))
        if not alts:
            alts = [x.strip() for x in re.split(r"[,/，、]", m.group(1)) if x.strip()]
        if alts:
            fields["alt_ids"] = alts

    # 备注段
    m = re.search(
        r"##\s*备注[^\n]*\n+(.+?)(?:\n---|\n联系方式|\n提交时间|\Z)",
        body, re.DOTALL,
    )
    if m:
        fields["notes"] = m.group(1).strip()

    return fields


def parse_issue_form_body(body):
    """解析 GitHub Issue Form (.github/ISSUE_TEMPLATE/submit.yml) 生成的 issue body。
    Issue Form 渲染格式：### 字段名\\n\\n值\\n\\n### 下一个字段...
    """
    fields = {}

    def grab(label_pat, multiline=False):
        flags = re.DOTALL if multiline else 0
        m = re.search(
            r"###\s*" + label_pat + r"\s*\n+(.+?)(?=\n###|\Z)",
            body, flags,
        )
        if not m: return None
        val = m.group(1).strip()
        if val == "_No response_": return None
        return val

    if v := grab(r"主 ID"): fields["id"] = v
    if v := grab(r"平台"): fields["platform"] = v.strip()
    if v := grab(r"性质"): fields["nature"] = v
    if v := grab(r"商品类型"): fields["goods_type"] = v
    if v := grab(r"发货地"): fields["ship_from"] = v
    if v := grab(r"价位"): fields["price_range"] = v
    if v := grab(r"受骗人数（估算）"):
        try: fields["victim_count"] = int(v.strip())
        except ValueError: pass
    if v := grab(r"关联 ID[^\n]*", multiline=True):
        alts = [x.strip() for x in v.split("\n") if x.strip()]
        if alts: fields["alt_ids"] = alts
    if v := grab(r"备注[^\n]*", multiline=True):
        fields["notes"] = v

    return fields


def parse_issue_body(body, labels):
    """根据 labels 自动选解析器。"""
    if "from-form" in labels:
        return parse_form_body(body)
    if "from-issue-form" in labels:
        return parse_issue_form_body(body)
    # 没 label 时两个都试，取字段多的
    f1 = parse_form_body(body)
    f2 = parse_issue_form_body(body)
    return f1 if len(f1) >= len(f2) else f2


# ========================================================================
# 交互式 ask 辅助
# ========================================================================

def ask(prompt, default=None, validator=None, allow_empty=False):
    while True:
        suffix = f" [{default}]" if default else ""
        try:
            val = input(f"{prompt}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            sys.exit(1)
        if not val and default is not None:
            val = default
        if not val and not allow_empty:
            print("  ! 不能为空")
            continue
        if validator:
            err = validator(val)
            if err:
                print(f"  ! {err}")
                continue
        return val


def ask_choice(prompt, choices, default=None):
    return ask(
        f"{prompt} ({'/'.join(choices)})",
        default=default,
        validator=lambda v: None if v in choices else f"必须是 {choices} 之一",
    )


def ask_int(prompt, default=None, min_val=0):
    return int(ask(
        prompt,
        default=str(default) if default is not None else None,
        validator=lambda v: None if v.lstrip("-").isdigit() and int(v) >= min_val else f"必须是 ≥ {min_val} 的整数",
    ))


def ask_alt_ids(prefill=None):
    """让用户多行输入 alt_ids。

    prefill 给的话先展示，问 y 采用 / n 重输。
    """
    if prefill:
        print(f"[关联 ID] 从 issue 预填: {' / '.join(prefill)}")
        ans = ask_choice("    采用？(y 采用 / n 重新逐个输入)", ["y", "n"], default="y")
        if ans == "y":
            return list(prefill)
        # n 则走下面手动输入

    print("[关联 ID] 同一卖家的其它账号，一行一个，回车确认，最后空行结束（没有可直接回车跳过）：")
    ids = []
    while True:
        try:
            line = input(f"  alt_id {len(ids)+1}: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        ids.append(line)
    return ids


def ask_nature(default=None):
    print("[性质] 常用预设：")
    for i, n in enumerate(NATURE_PRESETS, 1):
        print(f"  {i}) {n}")
    raw = ask("选择编号或直接输入自定义性质", default=default)
    if raw.isdigit() and 1 <= int(raw) <= len(NATURE_PRESETS):
        return NATURE_PRESETS[int(raw) - 1]
    return raw


def ask_notes(default=None):
    if default:
        print("[备注] 从 issue 预填:")
        for line in default.split("\n"):
            print(f"  > {line}")
        ans = ask_choice("    采用？(y 采用 / n 重新输入 / e 进编辑模式补充)", ["y", "n", "e"], default="y")
        if ans == "y":
            return default
        if ans == "e":
            print(f"[备注] 当前 {len(default)} 字。再输入要补充的内容，Ctrl-Z 回车结束：")
            lines = [default, "", "--- 补充 ---"]
            try:
                while True:
                    lines.append(input())
            except EOFError:
                pass
            return "\n".join(lines).strip()
        # n 则走下面手动输入

    print("[备注] 自由文本：诈骗手法 / 闲鱼差评数 / 群证词 / 其它佐证（Ctrl-D 或 Ctrl-Z 回车结束）：")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    text = "\n".join(lines).strip()
    if len(text) < 20:
        print(f"  ! 备注太短（当前 {len(text)} 字）")
        if ask_choice("仍要使用？", ["y", "n"], default="n") == "n":
            return ask_notes()
    return text


# ========================================================================
# data.json 读写
# ========================================================================

def load_data(path):
    if not path.exists():
        return {
            "version": 2,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "蚁圈瓜田。由 freetabris 公开维护，投稿通过 GitHub Issue / 邮件 / 微信，审核通过后录入。",
            "records": [],
        }
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("version") != 2:
        print(f"! data.json version 不是 2 (实际 {data.get('version')})。请先迁移再录入。")
        sys.exit(1)
    return data


def save_data(path, data):
    """原子写入：先写临时文件，再 rename。"""
    data["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False,
        dir=path.parent, suffix=".tmp",
    )
    try:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        os.unlink(tmp.name)
        raise


def find_existing(records, main_id, alt_ids):
    """查 main_id 或任一 alt_id 是否已存在。"""
    targets = {main_id} | set(alt_ids)
    for r in records:
        existing = {r["id"]} | set(r.get("alt_ids", []))
        if targets & existing:
            return r
    return None


# ========================================================================
# main
# ========================================================================

def main():
    ap = argparse.ArgumentParser(description="蚁圈瓜田 - 录入工具")
    ap.add_argument(
        "--data", type=Path,
        default=Path(__file__).resolve().parent.parent / "public" / "data.json",
        help="data.json 路径",
    )
    ap.add_argument("--dry-run", action="store_true", help="只显示预览不写入")
    ap.add_argument("--from-issue", type=int, default=None,
                    help="从 GitHub issue 拉字段预填到提示里，按回车采用 / 输入新值覆盖")
    args = ap.parse_args()

    prefill = {}
    issue_meta = None
    if args.from_issue is not None:
        print(f"从 GitHub issue #{args.from_issue} 拉取...")
        issue_data, labels = fetch_issue(args.from_issue)
        if issue_data is None:
            print("拉取失败，回退到全手动录入。")
            print()
        else:
            issue_meta = issue_data
            prefill = parse_issue_body(issue_data.get("body", ""), labels)
            print(f"✓ issue #{args.from_issue}: {issue_data.get('title', '')}")
            print(f"  state={issue_data.get('state', '?')}, labels={labels}")
            print(f"  解析到 {len(prefill)} 个字段：{', '.join(prefill.keys())}")
            print(f"  下面提示中括号 [] 里的值就是 issue 内容，按回车采用 / 输入新值覆盖。")
            print()

    if not args.data.parent.exists():
        print(f"目标目录不存在：{args.data.parent}")
        sys.exit(1)

    data = load_data(args.data)
    print(f"=== 蚁圈瓜田 - 录入工具 ===")
    print(f"data.json: {args.data} (当前 {len(data['records'])} 条记录)")
    print()

    main_id_raw = ask(
        "[1] 主 ID (微信号 / 闲鱼 ID / 手机号 / QQ号)",
        default=prefill.get("id"),
    )
    main_id = mask_phone(main_id_raw)
    if main_id != main_id_raw:
        print(f"  → 手机号自动脱敏: {main_id}")

    platform = ask_choice(
        "[2] 平台", PLATFORMS,
        default=prefill.get("platform") if prefill.get("platform") in PLATFORMS else "wechat",
    )

    alt_ids_raw = ask_alt_ids(prefill=prefill.get("alt_ids"))
    alt_ids = [mask_phone(a) for a in alt_ids_raw]
    for raw, masked in zip(alt_ids_raw, alt_ids):
        if raw != masked:
            print(f"  → 关联号手机自动脱敏: {raw} → {masked}")

    existing = find_existing(data["records"], main_id, alt_ids)
    if existing:
        print(f"\n⚠️  ID 已存在：{existing['id']} ({existing['nature']}, {existing['ship_from']})")
        action = ask_choice("(a)ppend 到现有记录的 notes / (n)ew 新建 / (q)uit", ["a", "n", "q"], default="a")
        if action == "q":
            print("已取消。")
            return
        merge_into = existing if action == "a" else None
    else:
        merge_into = None

    nature = ask_nature(default=prefill.get("nature"))
    goods_type = ask(
        "[4] 商品类型 (自由文本，例：活体 / 配件 / 食物 / 具体物种名)",
        default=prefill.get("goods_type"),
        allow_empty=True,
    )
    ship_from = ask(
        "[5] 发货地 (城市级，例：北京 / 云南昆明 / 海外集货 / 未知)",
        default=prefill.get("ship_from"),
    )
    price_range = ask(
        "[6] 价位 (单笔金额或区间，例：5800 / 1000-3000)",
        default=prefill.get("price_range"),
        allow_empty=True,
    )
    victim_count = ask_int(
        "[7] 受骗人数 (估算，备注里写来源)",
        default=prefill.get("victim_count"),
        min_val=1,
    )
    notes = ask_notes(default=prefill.get("notes"))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if merge_into:
        merge_into["notes"] = merge_into["notes"] + f"\n\n--- 补充 {now[:10]} ---\n" + notes
        merge_into["victim_count"] += victim_count
        for a in alt_ids:
            if a not in merge_into["alt_ids"] and a != merge_into["id"]:
                merge_into["alt_ids"].append(a)
        record = merge_into
        action_label = f"合并到 {merge_into['id']}"
    else:
        record = {
            "id": main_id,
            "platform": platform,
            "alt_ids": alt_ids,
            "nature": nature,
            "goods_type": goods_type,
            "ship_from": ship_from,
            "price_range": price_range,
            "victim_count": victim_count,
            "notes": notes,
            "added_at": now,
        }
        data["records"].append(record)
        action_label = "新建"

    print()
    print("=" * 50)
    print(f"操作: {action_label}")
    print(f"  ID:     {record['id']} ({PLATFORM_LABELS.get(record['platform'], record['platform'])})")
    if record["alt_ids"]:
        print(f"  关联:   {' / '.join(record['alt_ids'])}")
    print(f"  性质:   {record['nature']}")
    print(f"  商品:   {record['goods_type']}")
    print(f"  发货地: {record['ship_from']}")
    print(f"  价位:   {record['price_range']}")
    print(f"  人数:   {record['victim_count']}")
    print(f"  备注:   {record['notes'][:80]}{'...' if len(record['notes']) > 80 else ''}")
    print("=" * 50)

    if args.dry_run:
        print("\n[dry-run] 未写入文件")
        return

    if ask_choice("\n确认录入？", ["y", "n"], default="n") != "y":
        print("已取消。")
        return

    save_data(args.data, data)
    print(f"✓ 已写入 {args.data}")
    print(f"  下一步: git add public/data.json && git commit -m '录入 {record['id']}'")
    if args.from_issue is not None and issue_meta:
        print(f"  录入完别忘记 close issue #{args.from_issue}：")
        print(f"    gh issue close {args.from_issue} --repo {REPO} --comment '已录入'")


if __name__ == "__main__":
    main()
