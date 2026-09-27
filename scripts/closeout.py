#!/usr/bin/env python3
"""权威收口：逐封 messages.get 判定，只归档确证仍在收件箱的邮件。

为什么必须这样做：gog gmail search 的"匹配结果"与输出里的 LABELS 列都受
Gmail 搜索索引最终一致性影响，会同时产生假阳性（已归档邮件仍被 in:inbox 命中、
LABELS 仍显示 INBOX）。messages.get 返回的 label_ids 是唯一权威口径。

典型用法（补漏 / 二次运行）：
  classify.py --in snapshot.tsv --out manifest.json
  closeout.py --manifest manifest.json            # 只判定并打印
  closeout.py --manifest manifest.json --apply    # 判定后就地归档

环境: GOG_BIN GOG_ACCOUNT GMAIL_TIDY_HOME
      CLOSEOUT_GAP(默认 12s，逐封间隔，避免触发配额风控)
"""
from __future__ import annotations
import argparse, json, os, pathlib, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent
HOME_DIR = pathlib.Path(os.environ.get("GMAIL_TIDY_HOME") or HERE)
GOG = os.environ.get("GOG_BIN", "gog")
ACCT = os.environ.get("GOG_ACCOUNT", "")
GAP = float(os.environ.get("CLOSEOUT_GAP", "12"))
CHUNK = 50


def gog(args: list[str], gap: float = GAP) -> subprocess.CompletedProcess:
    cmd = [GOG] + (["-a", ACCT] if ACCT else []) + args
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=300)


def label_ids(msg_id: str) -> str | None:
    p = gog(["gmail", "get", msg_id])
    if "notFound" in (p.stdout + p.stderr):
        return None                      # 邮件已不存在（被删/被合并进会话）
    for ln in p.stdout.splitlines():
        if ln.startswith("label_ids\t"):
            return ln.split("\t", 1)[1].strip()
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(HOME_DIR / "manifest.json"))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    man = json.loads(pathlib.Path(args.manifest).read_text())
    cats = man.get("categories", {})
    cands = []
    for cat, recs in (man.get("plan") or {}).items():
        cfg = cats.get(cat) or {}
        if not cfg.get("label") or cfg.get("action") == "keep":
            continue                     # keep 类本就该在收件箱
        for r in recs:
            cands.append((r["id"], cfg["label"], cfg.get("action", "archive")))

    print(f"待权威判定 {len(cands)} 封（逐封 messages.get，间隔 {GAP:.0f}s，"
          f"约 {len(cands) * GAP / 60:.0f} 分钟）", flush=True)

    todo: dict[str, list[str]] = {}
    stale = gone = kept = 0
    for i, (mid, label, action) in enumerate(cands, 1):
        labs = label_ids(mid)
        time.sleep(GAP)
        if labs is None:
            gone += 1
            continue
        if "INBOX" in labs.split(","):
            if action == "archive":
                todo.setdefault(label, []).append(mid)
            else:
                kept += 1
        else:
            stale += 1                   # 索引滞后假阳性：其实早就归档了
        if i % 20 == 0:
            print(f"  已判定 {i}/{len(cands)}…", flush=True)

    n_todo = sum(len(v) for v in todo.values())
    print()
    print(f"已归档(索引滞后假阳性) {stale} / 邮件已不存在 {gone} / "
          f"确证在收件箱且需归档 {n_todo}")
    if kept:
        print(f"确证在收件箱且按边界保留（账单/待办 label_only） {kept}")
    for k, v in todo.items():
        print(f"  需归档 {k}: {len(v)} 封")

    if not n_todo:
        print("\n结论：收件箱已无应归档类残留。")
        return 0
    if not args.apply:
        print("\n（dry-run：未改动。加 --apply 就地归档）")
        return 0

    total = 0
    for label, ids in todo.items():
        for i in range(0, len(ids), CHUNK):
            part = ids[i:i + CHUNK]
            p = gog(["gmail", "batch", "modify", *part, f"--add-label={label}",
                     "--remove-label=INBOX", "-y", "--no-input"], gap=20)
            if p.returncode == 0:
                total += len(part)
                print(f"  ✓ {label} {i + len(part)}/{len(ids)}", flush=True)
            else:
                print(f"  ✗ {label}: {(p.stdout + p.stderr).strip()[:140]}", flush=True)
    print(f"\n本次归档 {total} 封")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
