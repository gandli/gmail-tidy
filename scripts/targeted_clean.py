#!/usr/bin/env python3
"""定向清理：按 rules.json 里 explicit 声明的发件人，逐个查收件箱残留并归档。
比全量翻页省配额（配额按返回结果条数计），适合补漏 / 二次运行。

用法:
  targeted_clean.py [--apply] [--per-domain 100]

默认 dry-run，只报告每个发件人在收件箱还剩几封。
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path(os.environ.get("GMAIL_TIDY_HOME") or HERE)
GOG = os.environ.get("GOG_BIN", "gog")
ACCT = os.environ.get("GOG_ACCOUNT", "")
SLEEP = float(os.environ.get("DOMAIN_DELAY", "15"))
BACKOFF = float(os.environ.get("BACKOFF", "90"))


def gog(args: list[str]) -> subprocess.CompletedProcess:
    cmd = [GOG] + (["-a", ACCT] if ACCT else []) + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=900)


def load_rules() -> dict:
    for p in (HOME / "rules.json", HERE / "rules.json", HERE / "rules.example.json"):
        if p.is_file():
            return json.loads(p.read_text())
    sys.exit("找不到 rules.json（复制 rules.example.json 修改）")


def search_ids(domain: str, cap: int) -> list[str]:
    """返回收件箱里该发件人的 message id。限流则退避重试。"""
    for attempt in range(3):
        p = gog(["gmail", "search", f"in:inbox from:{domain}",
                 "--max", str(cap), "--plain"])
        combined = (p.stdout or "") + (p.stderr or "")
        if "rateLimitExceeded" in combined:
            wait = BACKOFF * (attempt + 1)
            print(f"    {domain}: 限流，退避 {wait:.0f}s", flush=True)
            time.sleep(wait)
            continue
        if "Google API error" in combined:
            print(f"    {domain}: API 错误，跳过", flush=True)
            return []
        ids = []
        for ln in (p.stdout or "").splitlines()[1:]:
            parts = ln.split("\t")
            if not parts or not re.fullmatch(r"[0-9a-f]{16}", parts[0]):
                continue
            labels = parts[4] if len(parts) > 4 else ""
            if "INBOX" in labels:          # 只收确实还在收件箱的
                ids.append(parts[0])
        return ids
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--per-domain", type=int, default=100)
    args = ap.parse_args()

    rules = load_rules()
    cats = rules["categories"]
    explicit = rules.get("explicit") or {}

    todo: dict[str, list[str]] = {}
    print("=== 各发件人在收件箱的残留:")
    for cat, senders in explicit.items():
        cfg = cats.get(cat) or {}
        label, action = cfg.get("label"), cfg.get("action", "keep")
        if not label or action != "archive":
            continue
        for s in senders:
            ids = search_ids(s, args.per_domain)
            if ids:
                print(f"  {s:<42} {len(ids):>3} 封 → {label}")
                todo.setdefault(label, []).extend(ids)
            time.sleep(SLEEP)

    total = sum(len(v) for v in todo.values())
    print(f"合计残留 {total} 封")
    if not args.apply or not todo:
        print("（dry-run：未改动。加 --apply 归档）")
        return 0

    for label, ids in todo.items():
        for i in range(0, len(ids), 50):
            part = ids[i:i + 50]
            r = gog(["gmail", "batch", "modify", *part, f"--add-label={label}",
                     "--remove-label=INBOX", "-y", "--no-input"])
            print(f"  {label} {i+len(part)}/{len(ids)}:",
                  "ok" if r.returncode == 0 else (r.stdout + r.stderr).strip()[:120])
            time.sleep(20)
    print(f"已归档 {total} 封")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
