#!/usr/bin/env python3
"""回滚 apply_archive.py 归档的邮件：移除自动打的标签，并把归档的放回收件箱。
幂等：已经不在收件箱的邮件不会被重复加 INBOX。
"""
from __future__ import annotations
import argparse, json, os, pathlib, subprocess, time

HOME = pathlib.Path(os.environ.get("GMAIL_TIDY_HOME") or pathlib.Path(__file__).resolve().parent)
GOG = os.environ.get("GOG_BIN", "gog")
ACCT = os.environ.get("GOG_ACCOUNT", "")
DELAY = float(os.environ.get("BATCH_DELAY", "4"))


def gog(args: list[str]) -> subprocess.CompletedProcess:
    cmd = [GOG] + (["-a", ACCT] if ACCT else []) + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=900)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-manifest", default=str(HOME / "archive_manifest.json"))
    ap.add_argument("--chunk", type=int, default=50)
    args = ap.parse_args()

    path = pathlib.Path(args.archive_manifest)
    if not path.is_file():
        raise SystemExit(f"找不到 {path}（没有可回滚的归档记录）")
    ops = json.loads(path.read_text())["applied"]

    total = 0
    for op in ops:
        ids, label = op["ids"], op["label"]
        for i in range(0, len(ids), args.chunk):
            part = ids[i:i + args.chunk]
            # 归档过的要加回 INBOX；只打标签的仅去标签
            cmd = ["gmail", "batch", "modify", *part, f"--remove-label={label}"]
            if op["action"] == "archive":
                cmd.append("--add-label=INBOX")
            cmd += ["-y", "--no-input"]
            p = gog(cmd)
            if p.returncode == 0:
                total += len(part)
                print(f"  ↩ {label} {min(i+args.chunk,len(ids))}/{len(ids)}", flush=True)
            else:
                print(f"  ✗ {label} {i}: {(p.stdout+p.stderr).strip()[:160]}", flush=True)
            time.sleep(DELAY)
    print(f"已回滚 {total} 封")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
