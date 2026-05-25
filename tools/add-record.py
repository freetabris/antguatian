#!/usr/bin/env python3
"""蚁圈交易诈骗黑名单 - 录入工具

交互式 CLI：填字段 → 追加到 public/data.json

用法：
  python tools/add-record.py
  python tools/add-record.py --dry-run
  python tools/add-record.py --from-issue 42      (TODO: 从 GitHub issue 拉数据，未实现)
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

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


def ask_alt_ids():
    """让用户多行输入 alt_ids（同一人的其它账号），空行结束。"""
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


def ask_nature():
    """让用户从预设里选或自由输入。"""
    print("[性质] 常用预设：")
    for i, n in enumerate(NATURE_PRESETS, 1):
        print(f"  {i}) {n}")
    raw = ask("选择编号或直接输入自定义性质")
    if raw.isdigit() and 1 <= int(raw) <= len(NATURE_PRESETS):
        return NATURE_PRESETS[int(raw) - 1]
    return raw


def ask_notes():
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


def load_data(path):
    if not path.exists():
        return {
            "version": 2,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "蚁圈交易诈骗黑名单。由 freetabris 公开维护，投稿通过 GitHub Issue / 邮件 / 微信，审核通过后录入。",
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


def main():
    ap = argparse.ArgumentParser(description="蚁圈诈骗黑名单 - 录入工具")
    ap.add_argument(
        "--data", type=Path,
        default=Path(__file__).resolve().parent.parent / "public" / "data.json",
        help="data.json 路径",
    )
    ap.add_argument("--dry-run", action="store_true", help="只显示预览不写入")
    ap.add_argument("--from-issue", type=int, default=None, help="(TODO 未实现) 从 GitHub issue 拉字段")
    args = ap.parse_args()

    if args.from_issue is not None:
        print("--from-issue 暂未实现，先手动输入字段。")

    if not args.data.parent.exists():
        print(f"目标目录不存在：{args.data.parent}")
        sys.exit(1)

    data = load_data(args.data)
    print(f"=== 蚁圈诈骗黑名单 - 录入工具 ===")
    print(f"data.json: {args.data} (当前 {len(data['records'])} 条记录)")
    print()

    main_id = ask("[1] 主 ID (微信号 / 闲鱼 ID / 手机号 / QQ号)")
    platform = ask_choice("[2] 平台", PLATFORMS, default="wechat")
    alt_ids = ask_alt_ids()

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

    nature = ask_nature()
    goods_type = ask("[4] 商品类型 (自由文本，例：活体 / 配件 / 食物 / 具体物种名)")
    ship_from = ask("[5] 发货地 (城市级，例：北京 / 云南昆明 / 海外集货 / 未知)")
    price_range = ask("[6] 价位 (单笔金额或区间，例：5800 / 1000-3000)")
    victim_count = ask_int("[7] 受骗人数 (估算，备注里写来源)", min_val=1)
    notes = ask_notes()

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


if __name__ == "__main__":
    main()
