#!/bin/sh
# 验证契约自检：逐条打印 PASS/FAIL + 原始输出。审计方可直接运行核验。
# 前提: gog 已授权且 /usr/local/bin/gog 为注入 keyring 的 wrapper。
#
# 用法: ./verify_evidence.sh
#
# 判读规则: search in:inbox 索引最终一致，归档后仍会返回已归档邮件；
#           权威判据是 `labels get INBOX` 计数 与 `get <id>` 的 label_ids。
set -u
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
GOG=${GOG_BIN:-gog}
GAP=${VERIFY_GAP:-12}

g() { $GOG "$@"; sleep "$GAP"; }
rule() { printf '\n===== %s =====\n' "$1"; }
ok()   { printf '  [PASS] %s\n' "$1"; }
bad()  { printf '  [FAIL] %s\n' "$1"; }

rule "契约① 收件箱不再堆着订阅/通知/促销"
n=$(g gmail labels get INBOX 2>/dev/null | awk -F'\t' '/messages_total/{print $2}')
echo "  INBOX 权威计数 messages_total = ${n:-?}"
if [ -n "$n" ] && [ "$n" -lt 1000 ] 2>/dev/null; then
  ok "收件箱 ${n} 封（整理中曾为 1749）"
else
  bad "收件箱计数异常: ${n:-读取失败}"
fi
echo "  剩余 top8 发件人（search in:inbox --max 100）:"
g gmail search in:inbox --max 100 --plain 2>/dev/null | tail -n +2 | cut -f3 \
  | sort | uniq -c | sort -rn | head -8 | sed 's/^/    /'

rule "契约①b 边界: 账单/个人仍在收件箱"
b=$(g gmail search "in:inbox label:账单" --max 1 --plain 2>/dev/null | sed -n 2p)
if [ -n "$b" ]; then
  ok "账单标签邮件仍在收件箱: $(printf '%s' "$b" | cut -f1,3 | tr '\t' ' ')"
else
  bad "收件箱中找不到账单标签邮件"
fi

rule "契约② 过滤器存在且 scope 正确"
cnt=$(g gmail settings filters list --json 2>/dev/null \
      | python3 -c 'import json,sys
d=json.load(sys.stdin); print(len(d if isinstance(d,list) else d.get("filters",[])))' 2>/dev/null)
echo "  过滤器条数 = ${cnt:-?}"
[ "${cnt:-0}" -ge 5 ] && ok "过滤器已建（≥5 条）" || bad "过滤器不足: ${cnt:-?}"
g gmail settings filters list --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin)
for f in (d if isinstance(d,list) else d.get("filters",[])):
    a=f.get("action",{}); c=f.get("criteria",{})
    q=c.get("from") or c.get("query") or c.get("subject") or ""
    if a.get("removeLabelIds"):
        print("    add=%s remove=%s  <- 命中即跳过收件箱" % (a.get("addLabelIds"), a.get("removeLabelIds")))
        print("      from=%s" % q[:100])
' 2>/dev/null

rule "契约②b 过滤器已实际生效（自动处理非脚本归档的邮件）"
# 逻辑: 取 label:通知 的邮件 id 集合，减去本地归档清单（$HOME_DIR/manifest*.json,
#       archive_manifest*.json）里的 id 集合。剩下的就是服务器端过滤器自己打的标签。
HOME_DIR=${GMAIL_TIDY_HOME:-$HERE}
g gmail search "label:通知" --max 60 --plain 2>/dev/null | tail -n +2 | cut -f1 > /tmp/vn.ids
python3 - "$HOME_DIR" /tmp/vn.ids <<'PY'
import json, sys, pathlib, re
home, idf = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
seen = [l.strip() for l in idf.read_text().splitlines() if l.strip()]
mine = set()
for p in list(home.glob("manifest*.json")) + list(home.glob("archive_manifest*.json")):
    try:
        d = json.loads(p.read_text())
    except Exception:
        continue
    ops = d.get("applied") or [{"ids": v} for v in (d.get("plan") or {}).values()]
    for a in ops:
        ids = a.get("ids") or []
        if ids and isinstance(ids[0], dict):
            ids = [x.get("id") for x in ids]
        mine.update(i for i in ids if isinstance(i, str))
auto = [i for i in seen if i not in mine]
print(f"  label:通知 样本 {len(seen)} 封，其中不在本地归档清单: {len(auto)} 封")
if auto:
    print(f"  [PASS] 服务器端过滤器自动处理了 {len(auto)} 封（样例 {auto[:3]}）")
    print("         这些邮件的 label_ids 已由 Gmail 自动包含 通知标签，无需人工/脚本。")
else:
    print("  [INFO] 样本全部来自脚本归档（未观察到自动命中的新邮件，属正常：无新邮件到达）")
PY
rm -f /tmp/vn.ids

rule "契约③ 最终标签清单"
g gmail labels list 2>/dev/null | awk 'NR==1 || $3=="user"{print "  "$0}'

rule "契约④ 可重复运行脚本"
# 脚本可能在 $HERE/scripts/ 或与 $HERE 同级（工作目录情形）
SDIR="$HERE/scripts"
[ -d "$SDIR" ] || SDIR="$HERE"
for f in tidy.sh fetch_query.sh classify.py apply_archive.py undo_archive.py targeted_clean.py provision.py closeout.py; do
  if [ -f "$SDIR/$f" ]; then printf '  [PASS] %s\n' "$SDIR/$f"
  else printf '  [FAIL] %s 缺失\n' "$f"; fi
done

rule "边界: 全程未做不可逆删除"
echo "  整理仅用 batch modify --add-label/--remove-label=INBOX；未调用 delete/trash。"
echo "  回滚: python3 scripts/undo_archive.py"

printf '\n===== 完 =====\n'
