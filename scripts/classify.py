#!/usr/bin/env python3
"""只读：把 Gmail 快照按规则分类，输出 manifest.json。纯本地，不调 API、不改邮件。

用法:
  classify.py [--in inbox_raw.tsv] [--rules rules.json] [--out manifest.json]

规则默认从 $GMAIL_TIDY_HOME/rules.json 读，没有则用同目录的 rules.example.json。
匹配优先级: explicit(按发件人精确) > patterns(正则) > default_category。
"""
from __future__ import annotations
import argparse, csv, json, os, pathlib, re, sys, collections

HERE = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path(os.environ.get("GMAIL_TIDY_HOME") or (HERE))


def load_rules(path: str | None) -> dict:
    cands = [pathlib.Path(path)] if path else [
        HOME / "rules.json", HERE / "rules.json", HERE / "rules.example.json",
    ]
    for p in cands:
        if p.is_file():
            try:
                return json.loads(p.read_text())
            except json.JSONDecodeError as e:
                sys.exit(f"规则文件 {p} 解析失败: {e}")
    sys.exit("找不到规则文件：请复制 rules.example.json 为 rules.json 并修改")


def addr(field: str) -> str:
    """从 'Name <a@b.com>' 抽出小写邮箱；无尖括号则原样小写。"""
    m = re.search(r"<([^>]+)>", field or "")
    return (m.group(1) if m else (field or "")).lower().strip()


def build_matcher(rules: dict):
    cat_of = {}
    for cat, senders in (rules.get("explicit") or {}).items():
        for s in senders:
            cat_of[s.lower()] = cat
    pats = [(cat, re.compile(p, re.I)) for cat, p in (rules.get("patterns") or [])]

    def match(a: str, sender_full: str) -> str:
        # 1) 精确发件人
        if a in cat_of:
            return cat_of[a]
        # 2) 域名后缀：explicit 里写 'stripe.com' 也应命中 billing@stripe.com
        dom = a.split("@")[-1] if "@" in a else a
        for k, cat in cat_of.items():
            if "@" not in k and (dom == k or dom.endswith("." + k)):
                return cat
        # 3) 正则
        hay = f"{a} {sender_full}".lower()
        for cat, rx in pats:
            if rx.search(hay):
                return cat
        return rules.get("default_category", "personal")

    return match


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=str(HOME / "inbox_raw.tsv"))
    ap.add_argument("--rules", default=None)
    ap.add_argument("--out", default=str(HOME / "manifest.json"))
    args = ap.parse_args()

    rules = load_rules(args.rules)
    cats = rules["categories"]
    match = build_matcher(rules)

    src = pathlib.Path(args.src)
    if not src.is_file():
        sys.exit(f"缺少快照文件 {src}，请先跑 fetch_query.sh")
    rows = [r for r in csv.reader(src.open(), encoding="utf-8") if len(r) >= 6][1:]

    plan: dict[str, list] = collections.defaultdict(list)
    keep: list = []
    seen = 0
    for r in rows:
        mid, date, sender, subject = r[0], r[1], r[2], r[3]
        a = addr(sender)
        if "@" not in a and not any(ch.isalnum() for ch in a):
            continue                      # 表头/异常行
        seen += 1
        rec = {"id": mid, "from": a, "subject": subject[:70], "date": date}
        cat = match(a, sender)
        action = (cats.get(cat) or {}).get("action", "keep")
        (plan[cat] if action != "keep" else keep).append(rec)

    payload = {
        "plan": {c: v for c, v in plan.items() if v},
        "keep": keep,
        "categories": cats,
        "totals": {"scanned": seen, "total": len(rows)},
    }
    pathlib.Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=1))

    print("=== 计划:")
    for cat in sorted(payload["plan"]):
        label = (cats.get(cat) or {}).get("label")
        action = (cats.get(cat) or {}).get("action")
        print(f"  {cat:<9} {len(payload['plan'][cat]):>4} 封  → 标签「{label}」({action})")
    if keep:
        print(f"=== 保留在收件箱: {len(keep)} 封")
    print(f"=== 扫描 {seen} 封, 明细见 {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
