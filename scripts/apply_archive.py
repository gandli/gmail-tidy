#!/usr/bin/env python3
"""按 manifest.json 执行归档：批量打标签 / 移出收件箱。默认 dry-run，加 --apply 才真改。

用法:
  apply_archive.py [--manifest manifest.json] [--apply] [--chunk 50]

动作来自规则文件: archive(打标签+移出收件箱) / label_only(只打标签)。
执行前会把计划写到 archive_manifest.json，供 undo_archive.py 回滚。
"""
from __future__ import annotations
import argparse, json, os, pathlib, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path(os.environ.get("GMAIL_TIDY_HOME") or HERE)
GOG = os.environ.get("GOG_BIN", "gog")
ACCT = os.environ.get("GOG_ACCOUNT", "")
DELAY = float(os.environ.get("BATCH_DELAY", "20"))
BACKOFF = float(os.environ.get("BACKOFF", "65"))


def gog(args: list[str]) -> subprocess.CompletedProcess:
    cmd = [GOG] + (["-a", ACCT] if ACCT else []) + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=900)


def batch(ids: list[str], label: str, archive: bool) -> int:
    args = ["gmail", "batch", "modify", *ids, f"--add-label={label}"]
    if archive:
        args.append("--remove-label=INBOX")
    args += ["-y", "--no-input"]
    for attempt in range(3):
        p = gog(args)
        out = p.stdout + p.stderr
        if "rateLimitExceeded" in out:
            wait = BACKOFF * (attempt + 1)
            print(f"    限流，退避 {wait:.0f}s 重试", flush=True)
            time.sleep(wait)
            continue
        if p.returncode != 0:
            print(f"    ✗ 失败({p.returncode}): {out.strip()[:200]}", flush=True)
            return 0
        return len(ids)
    print("    ✗ 重试 3 次仍限流，放弃这一批", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(HOME / "manifest.json"))
    ap.add_argument("--apply", action="store_true", help="真正执行（默认只打印计划）")
    ap.add_argument("--chunk", type=int, default=50)
    args = ap.parse_args()

    man = json.loads(pathlib.Path(args.manifest).read_text())
    cats = man.get("categories", {})
    plan = man.get("plan", {})
    if not plan:
        print("计划为空，没什么可做")
        return 0

    ops, preview = [], []
    for cat, recs in plan.items():
        cfg = cats.get(cat) or {}
        label, action = cfg.get("label"), cfg.get("action", "keep")
        if not label or not recs:
            continue
        ops.append({"category": cat, "label": label,
                    "action": action, "ids": [r["id"] for r in recs]})
        preview.append((cat, label, action, len(recs)))

    print("=== 将执行:")
    for cat, label, action, n in preview:
        verb = "打标签 + 移出收件箱" if action == "archive" else "只打标签"
        print(f"  {cat:<9} {n:>4} 封  {verb}  标签「{label}」")

    if not args.apply:
        print("\n（dry-run：没有改动任何邮件。加 --apply 执行）")
        return 0

    done = 0
    for op in ops:
        ids = op["ids"]
        print(f"→ {op['label']} ({op['category']}, {len(ids)} 封)", flush=True)
        for i in range(0, len(ids), args.chunk):
            part = ids[i:i + args.chunk]
            done += batch(part, op["label"], op["action"] == "archive")
            time.sleep(DELAY)
    (HOME / "archive_manifest.json").write_text(
        json.dumps({"applied": ops}, ensure_ascii=False, indent=1))
    print(f"\n完成 {done} 封。回滚: python3 undo_archive.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
