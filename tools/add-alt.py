#!/usr/bin/env python3
"""蚁圈瓜田 - 追加关联 ID 到现有 record

用法:
  python tools/add-alt.py <主ID> <alt1> [alt2] [alt3] ...

例:
  python tools/add-alt.py 端离 桑榆非晚 半晴天蚁商
  python tools/add-alt.py 蚂飞飞蚁 x***0
  python tools/add-alt.py --dry-run 端离 测试号

行为:
- 找到主 ID 对应的 record（id 完全匹配 / 或在已有 alt_ids 里）
- 追加未存在的关联号（去重，手机号自动 mask 中间四位）
- 原子写回 public/data.json
- 提示 commit + push 命令

依赖：Python stdlib only。
"""

import argparse
import json
import os
import re
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

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "public" / "data.json"


def mask_phone(s):
    """11 位手机号中间四位脱敏。其它原样。"""
    return re.sub(r"^(1\d{2})\d{4}(\d{4})$", r"\1****\2", (s or "").strip())


def find_record(records, key):
    """根据主 ID 或已有 alt_id 找到 record。"""
    for r in records:
        if r["id"] == key:
            return r
    for r in records:
        if key in r.get("alt_ids", []):
            return r
    return None


def save_data(path, data):
    """原子写入。"""
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


def main():
    ap = argparse.ArgumentParser(
        description="追加关联 ID 到现有 record",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n", 2)[1],  # 把上面的「用法」段也显示出来
    )
    ap.add_argument("main_id", help="主 ID（必须已在 data.json 里）")
    ap.add_argument("alt_ids", nargs="+", help="要追加的关联号，一个或多个")
    ap.add_argument("--dry-run", action="store_true", help="只显示预览不写入")
    args = ap.parse_args()

    if not DATA.exists():
        print(f"! {DATA} 不存在", file=sys.stderr)
        sys.exit(1)

    data = json.loads(DATA.read_text(encoding="utf-8"))
    target = find_record(data["records"], args.main_id)
    if not target:
        print(f"! 找不到主 ID '{args.main_id}'", file=sys.stderr)
        print(f"  现有 records:")
        for r in data["records"]:
            print(f"    - {r['id']} ({len(r.get('alt_ids', []))} 个马甲)")
        sys.exit(1)

    target.setdefault("alt_ids", [])
    existing = {target["id"]} | set(target["alt_ids"])

    added, skipped = [], []
    for raw in args.alt_ids:
        masked = mask_phone(raw)
        if masked != raw:
            print(f"  → 手机号自动脱敏: {raw} → {masked}")
        if masked in existing:
            skipped.append(masked)
        else:
            target["alt_ids"].append(masked)
            existing.add(masked)
            added.append(masked)

    print()
    print(f"主档:  {target['id']} ({target.get('nature', '?')}, {target.get('ship_from', '?')})")
    print(f"现马甲: {target['alt_ids']}")
    if added:
        print(f"✓ 本次新增: {added}")
    if skipped:
        print(f"- 已存在跳过: {skipped}")

    if not added:
        print("\n无变化，不写文件。")
        return

    if args.dry_run:
        print("\n[dry-run] 未写入文件")
        return

    save_data(DATA, data)
    print(f"\n✓ 已写入 {DATA}")
    print(f"  下一步:")
    print(f"    git add public/data.json")
    msg = f"{target['id']} 新增马甲: {', '.join(added)}"
    print(f'    git commit -m "{msg}"')
    print(f"    git push")


if __name__ == "__main__":
    main()
