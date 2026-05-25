#!/usr/bin/env python3
"""蚁圈交易纠纷查询站 - 录入工具

交互式 CLI：填字段 → 自动哈希 + 脱敏 → 追加到 public/data.json

用法：
  python tools/add-record.py
  python tools/add-record.py --data public/data.json   # 自定义路径
  python tools/add-record.py --dry-run                 # 只看预览不写
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SENSITIVE_WORDS = [
    "camponotus", "formica", "lasius", "solenopsis", "atta", "pheidole",
    "messor", "myrmecia", "oecophylla", "polyrhachis", "paraponera",
    "dorylus", "eciton",
    "走私", "入境", "海关", "检疫", "入侵物种", "国家保护", "三有动物",
    "野生动物保护", "濒危", "保护动物",
    "哥伦比亚", "巴西", "亚马逊", "马达加斯加", "刚果",
    "骗子", "垃圾", "人渣", "傻逼", "废物",
]

ID_TYPES = ["wechat", "xianyu", "phone", "qq", "other"]
DISPUTE_TYPES = ["不发货", "货不对版", "拒不补发", "拒不退款", "失联", "卷款跑路", "other"]
HARD_EVIDENCE = {
    "1": ("police_report", "报案回执"),
    "2": ("court_verdict", "法院判决书"),
    "3": ("regulator_penalty", "监管处罚通知"),
    "4": ("platform_fraud_ruling", "平台诈骗认定"),
}


def check_sensitive(text):
    lower = text.lower()
    for w in SENSITIVE_WORDS:
        if w.lower() in lower:
            return w
    return None


def normalize_id(raw, id_type):
    s = (raw or "").strip().lower()
    if id_type == "phone":
        s = re.sub(r"\D", "", s)
        if s.startswith("86") and len(s) == 13:
            s = s[2:]
    elif id_type == "wechat":
        s = re.sub(r"[\s​-‏]", "", s)
    elif id_type in ("xianyu", "qq"):
        s = re.sub(r"\s", "", s)
    return s


def hash_id(normalized):
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def mask_display_id(raw, id_type):
    s = raw.strip()
    if id_type == "phone":
        digits = re.sub(r"\D", "", s)
        if len(digits) >= 7:
            return digits[:3] + "***" + digits[-2:]
        return "1**" + digits[-2:]
    if len(s) <= 3:
        return s[0].upper() + "**"
    return s[0].upper() + "***" + s[-2:]


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


def ask_amount(prompt):
    return int(ask(
        prompt,
        validator=lambda v: None if v.isdigit() and int(v) > 0 else "金额必须是正整数（元）",
    ))


def ask_month(prompt, default=None):
    pat = re.compile(r"^\d{4}-\d{2}$")
    return ask(
        prompt,
        default=default,
        validator=lambda v: None if pat.match(v) else "格式 YYYY-MM 例 2026-05",
    )


def ask_summary():
    print("摘要（脱敏的事件描述，300-1000 字，按 Ctrl-D / Ctrl-Z 回车结束）：")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    text = "\n".join(lines).strip()
    sens = check_sensitive(text)
    if sens:
        print(f"  ! 摘要含敏感词「{sens}」，请改写后重来")
        return ask_summary()
    if len(text) < 50:
        print(f"  ! 摘要太短（当前 {len(text)} 字，建议至少 300 字）")
        if ask_choice("仍要使用这段摘要吗？", ["y", "n"], default="n") == "n":
            return ask_summary()
    return text


def load_data(path):
    if not path.exists():
        return {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "数据由本站独立编辑人审核后录入。本文件公开，任何人可校验。撤稿/更正请见 disclaimer.html。",
            "merchants": [],
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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


def next_case_number(data, year_month):
    """生成顺位案号 'YYYY-MM-NNN'，扫描已有 complaints 取最大值 +1。"""
    prefix = year_month
    max_seq = 0
    for m in data["merchants"]:
        for c in m.get("complaints", []):
            cn = c.get("case_number", "")
            if cn.startswith(prefix + "-"):
                try:
                    seq = int(cn[len(prefix) + 1:])
                    if seq > max_seq:
                        max_seq = seq
                except ValueError:
                    pass
    return f"{prefix}-{max_seq + 1:03d}"


def recompute_stats(merchant):
    """重算 merchant.stats（基于现有 complaints，排除 withdrawn）。"""
    cs = [c for c in merchant["complaints"] if c.get("status") != "withdrawn"]
    merchant["stats"] = {
        "published": len(cs),
        "fraud": sum(1 for c in cs if c.get("severity") == "fraud"),
        "disputed": sum(1 for c in cs if c.get("status") == "disputed"),
        "total_amount_yuan": sum(c.get("amount_yuan", 0) for c in cs),
    }


def find_or_create_merchant(data, id_hash, id_type, display_id, severity, raw_id_plain):
    """按 id_hash 找现有商家，找不到则新建。如果新投诉是 fraud，升级 display_mode 为 plain。"""
    now_month = datetime.now(timezone.utc).strftime("%Y-%m")
    for m in data["merchants"]:
        if m["id_hash"] == id_hash:
            m["last_updated_month"] = now_month
            # 已存在商家，若本次投诉是 fraud 且当前是 mask，升级为 plain
            if severity == "fraud" and m["display_mode"] == "mask":
                m["display_mode"] = "plain"
                m["raw_id_plain"] = raw_id_plain
                print(f"  ⚠️ 商家 {display_id} 已升级为 fraud 等级 (display_mode: mask → plain)")
            return m, False
    # 新商家
    m = {
        "id_hash": id_hash,
        "id_type": id_type,
        "display_id": display_id,
        "display_mode": "plain" if severity == "fraud" else "mask",
        "raw_id_plain": raw_id_plain if severity == "fraud" else "",
        "alt_hashes": [],
        "first_seen_month": now_month,
        "last_updated_month": now_month,
        "score": 3.0,
        "withdrawn_count": 0,
        "stats": {"published": 0, "fraud": 0, "disputed": 0, "total_amount_yuan": 0},
        "complaints": [],
    }
    data["merchants"].append(m)
    return m, True


def main():
    ap = argparse.ArgumentParser(description="蚁圈纠纷查询站 - 录入工具")
    ap.add_argument(
        "--data", type=Path,
        default=Path(__file__).resolve().parent.parent / "public" / "data.json",
        help="data.json 路径（默认 public/data.json）",
    )
    ap.add_argument("--dry-run", action="store_true", help="只显示预览不写入文件")
    args = ap.parse_args()

    if not args.data.parent.exists():
        print(f"目标目录不存在：{args.data.parent}")
        sys.exit(1)

    data = load_data(args.data)
    print(f"=== 蚁圈纠纷查询站 - 录入工具 ===")
    print(f"data.json: {args.data}")
    print(f"已有商家：{len(data['merchants'])}")
    print()

    raw_id = ask(
        "[1] 商家 ID (raw，仅本地输入，dispute 类不会保存明文)",
        validator=lambda v: None if not check_sensitive(v) else f"含敏感词「{check_sensitive(v)}」",
    )
    id_type = ask_choice("[2] ID 类型", ID_TYPES, default="wechat")

    normalized = normalize_id(raw_id, id_type)
    id_hash = hash_id(normalized)
    display_id = mask_display_id(raw_id, id_type)

    print(f"\n  → 归一化:  {normalized}")
    print(f"  → 哈希:    {id_hash}")
    print(f"  → 脱敏ID:  {display_id}\n")

    severity = ask_choice("[3] 严重度", ["dispute", "fraud"], default="dispute")

    hard_evidence = ""
    if severity == "fraud":
        print("\n硬证据类型（fraud 必填，至少其中一项）：")
        for k, (_code, label) in HARD_EVIDENCE.items():
            print(f"  {k}) {label}")
        choice = ask_choice("[3.5] 选择硬证据", list(HARD_EVIDENCE.keys()))
        hard_evidence = HARD_EVIDENCE[choice][0]

    dispute_type = ask_choice("[4] 纠纷类型", DISPUTE_TYPES, default="不发货")
    amount = ask_amount("[5] 金额 (元)")
    occurred_month = ask_month("[6] 发生月份 (YYYY-MM)", default=datetime.now(timezone.utc).strftime("%Y-%m"))
    summary = ask_summary()
    evidence_count = int(ask(
        "[8] 站方收到的证据数",
        default="5" if severity == "fraud" else "4",
        validator=lambda v: None if v.isdigit() and int(v) >= 1 else "至少 1",
    ))

    now_month = datetime.now(timezone.utc).strftime("%Y-%m")
    case_number = next_case_number(data, now_month)

    complaint = {
        "case_number": case_number,
        "severity": severity,
        "hard_evidence": hard_evidence,
        "dispute_type": dispute_type,
        "amount_yuan": amount,
        "occurred_month": occurred_month,
        "status": "published",
        "summary": summary,
        "evidence_count": evidence_count,
        "appeals": [],
    }

    merchant, is_new = find_or_create_merchant(
        data, id_hash, id_type, display_id, severity, raw_id,
    )
    merchant["complaints"].append(complaint)
    recompute_stats(merchant)

    print()
    print("=" * 50)
    print("录入预览：")
    print(f"  商家:  {merchant['display_id']} ({merchant['id_type']}) - {'新建' if is_new else '追加现有'}")
    if merchant["display_mode"] == "plain":
        print(f"  明文:  {merchant['raw_id_plain']} (fraud 等级公示)")
    print(f"  案号:  {case_number}")
    print(f"  纠纷:  {dispute_type}, ¥{amount}, {occurred_month}, {severity}")
    if hard_evidence:
        print(f"  硬证据: {hard_evidence}")
    print(f"  摘要:  {summary[:80]}{'...' if len(summary) > 80 else ''}")
    print(f"  商家统计: 总 {merchant['stats']['published']} 件 / fraud {merchant['stats']['fraud']} / disputed {merchant['stats']['disputed']} / ¥{merchant['stats']['total_amount_yuan']}")
    print("=" * 50)

    if args.dry_run:
        print("\n[dry-run] 未写入文件")
        return

    if ask_choice("\n确认录入？", ["y", "n"], default="n") != "y":
        print("已取消。")
        return

    save_data(args.data, data)
    print(f"✓ 已写入 {args.data}")
    print(f"  下一步: git add public/data.json && git commit -m '案 {case_number}'")


if __name__ == "__main__":
    main()
