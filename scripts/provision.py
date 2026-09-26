#!/usr/bin/env python3
"""按 rules.json 自动创建标签与 Gmail 过滤器（服务器端自动归位）。
默认 dry-run，加 --apply 才真改。幂等：已存在的标签/过滤器会跳过。

用法:
  provision.py [--rules rules.json] [--dry-run|--apply]
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path(os.environ.get("GMAIL_TIDY_HOME") or HERE)
GOG = os.environ.get("GOG_BIN", "gog")
ACCT = os.environ.get("GOG_ACCOUNT", "")
GROUP = 12          # 一个过滤器里最多塞几个发件人


def gog(args: list[str]) -> subprocess.CompletedProcess:
    cmd = [GOG] + (["-a", ACCT] if ACCT else []) + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


def find_rules(explicit: str | None) -> pathlib.Path:
    cands = [pathlib.Path(explicit)] if explicit else [
        HOME / "rules.json", HERE / "rules.json", HERE / "rules.example.json"]
    for p in cands:
        if p.is_file():
            return p
    sys.exit("找不到规则文件（复制 rules.example.json 为 rules.json 后修改）")


def existing_labels() -> set[str]:
    out = gog(["gmail", "labels", "list", "--plain"]).stdout
    names = set()
    for line in out.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 3 and parts[2] == "user":
            names.add(parts[1])
    return names


def existing_filter_queries() -> set[str]:
    out = gog(["gmail", "settings", "filters", "list", "--json"]).stdout
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError:
        return set()
    items = data if isinstance(data, list) else data.get("filters", [])
    return {" ".join(sorted(re.findall(r"[\w.@-]+", (f.get("criteria") or {}).get("from", ""))))
            for f in items}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    apply = args.apply and not args.dry_run

    rules = json.loads(find_rules(args.rules).read_text())
    cats = rules["categories"]
    explicit = rules.get("explicit") or {}

    # 要归档的类别，其发件人不得被账单类过滤器误伤
    keep_senders = [s for c, v in explicit.items()
                    if (cats.get(c) or {}).get("action") == "label_only"
                    for s in v]

    labels_have = existing_labels()
    todo_labels = [c["label"] for c in cats.values() if c.get("label")]
    print("=== 标签:")
    for lab in todo_labels:
        mark = "已存在" if lab in labels_have else "将创建"
        print(f"  {mark:<4} {lab}")

    print("=== 过滤器:")
    plans = []
    for cat, cfg in cats.items():
        label, action = cfg.get("label"), cfg.get("action", "keep")
        if not label or action == "keep":
            continue
        senders = [s for s in explicit.get(cat, []) if "@" in s]
        domains = [s for s in explicit.get(cat, []) if "@" not in s]
        groups = [senders[i:i + GROUP] for i in range(0, len(senders), GROUP)]
        if domains:
            groups.append(domains)
        for g in groups:
            q = "from:(" + "|".join(g) + ")"
            if action == "archive" and keep_senders:
                q += " -{" + " ".join(f"from:{s}" for s in keep_senders[:8]) + "}"
            plans.append({"query": q, "label": label, "action": action})
    for p in plans:
        verb = "打标签+移出收件箱" if p["action"] == "archive" else "只打标签"
        print(f"  {p['label']:<6} {verb:<16} {p['query'][:88]}")

    if not apply:
        print("\n（dry-run：未改动。加 --apply 执行）")
        return 0

    for lab in todo_labels:
        if lab not in labels_have:
            r = gog(["gmail", "labels", "create", lab])
            print("  创建标签:", lab, "ok" if r.returncode == 0 else r.stderr.strip()[:120])

    have = existing_filter_queries()
    for p in plans:
        key = " ".join(sorted(re.findall(r"[\w.@-]+", p["query"])))
        if key in have:
            print("  跳过（已存在）:", p["query"][:70])
            continue
        cmd = ["gmail", "settings", "filters", "create", "--query", p["query"],
               f"--add-label={p['label']}", "--mark-read"]
        if p["action"] == "archive":
            cmd.append("--archive")
        r = gog(cmd)
        print(f"  创建过滤器 {p['label']}:", "ok" if r.returncode == 0 else r.stderr.strip()[:160])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
