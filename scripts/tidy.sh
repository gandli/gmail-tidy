#!/bin/sh
# gmail-tidy 编排脚本：抓快照 → 规则分类 → （可选）归档 → 报告
#
#   ./tidy.sh                只读报告（默认，不改任何邮件）
#   ./tidy.sh --apply        执行归档
#   ./tidy.sh --verify       归档后校验（对比快照，看还剩什么）
#   ./tidy.sh --provision    按规则创建标签 + 过滤器（先跑 --provision-dry 看计划）
#
# 环境变量:
#   GMAIL_TIDY_HOME  状态目录（默认 $HOME/.local/state/gmail-tidy）
#   GOG_BIN          gog 可执行文件（默认 gog）
#   GOG_ACCOUNT      多账号时指定（传给 gog -a）
#   MAX_PAGES        限制抓取页数（默认 0=全部）
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: "${GMAIL_TIDY_HOME:=$HOME/.local/state/gmail-tidy}"
mkdir -p "$GMAIL_TIDY_HOME"
export GMAIL_TIDY_HOME
MODE=${1:-report}
PY=${PYTHON:-python3}

case "$MODE" in
  --provision|--provision-dry)
    if [ "$MODE" = "--provision-dry" ]; then
      exec "$PY" "$HERE/provision.py" --dry-run
    else
      exec "$PY" "$HERE/provision.py" --apply
    fi ;;
esac

echo "① 抓收件箱快照（只读，分页 + 限流退避）"
"$HERE/fetch_query.sh" "in:inbox" "$GMAIL_TIDY_HOME/inbox_before.tsv" 50 >/dev/null
before=$(( $(wc -l < "$GMAIL_TIDY_HOME/inbox_before.tsv") - 1 ))
echo "   收件箱 $before 封"

echo "② 按规则分类"
"$PY" "$HERE/classify.py" --in "$GMAIL_TIDY_HOME/inbox_before.tsv" \
        --out "$GMAIL_TIDY_HOME/manifest.json"

case "$MODE" in
  --apply)
    echo "③ 执行归档"
    "$PY" "$HERE/apply_archive.py" --manifest "$GMAIL_TIDY_HOME/manifest.json" --apply
    echo "④ 归档后校验"
    "$HERE/fetch_query.sh" "in:inbox" "$GMAIL_TIDY_HOME/inbox_after.tsv" 50 >/dev/null
    after=$(( $(wc -l < "$GMAIL_TIDY_HOME/inbox_after.tsv") - 1 ))
    echo "   收件箱 $before → $after（清出 $((before - after)) 封）"
    echo "   剩余发件人 top10:"
    tail -n +2 "$GMAIL_TIDY_HOME/inbox_after.tsv" | cut -f3 | sort | uniq -c | sort -rn | head -10 | sed 's/^/     /'
    ;;
  --verify)
    if [ ! -f "$GMAIL_TIDY_HOME/inbox_after.tsv" ]; then
      "$HERE/fetch_query.sh" "in:inbox" "$GMAIL_TIDY_HOME/inbox_after.tsv" 50 >/dev/null
    fi
    after=$(( $(wc -l < "$GMAIL_TIDY_HOME/inbox_after.tsv") - 1 ))
    echo "收件箱当前 $after 封，剩余发件人 top10:"
    tail -n +2 "$GMAIL_TIDY_HOME/inbox_after.tsv" | cut -f3 | sort | uniq -c | sort -rn | head -10 | sed 's/^/  /'
    ;;
  *)
    echo
    echo "（只读报告：未改动任何邮件。执行归档加 --apply）"
    ;;
esac
