#!/bin/sh
# 只读：分页拉取 Gmail 查询结果（表头 + TSV 行）到文件。
# 自带限流退避 —— Gmail API 按"每分钟查询成本"限流，连发会 403 rateLimitExceeded。
#
# 用法: fetch_query.sh "<gmail-query>" [out.tsv] [page_size]
# 环境: GOG_BIN(默认 gog) GOG_ACCOUNT(可选,传给 -a) GMAIL_TIDY_HOME(状态目录)
#       PAGE_DELAY(默认 6s) BACKOFF(默认 65s) MAX_PAGES(默认 0=全部)
set -eu

Q=${1:?用法: fetch_query.sh "<gmail-query>" [out.tsv] [page_size]}
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: "${GMAIL_TIDY_HOME:=$HOME/.local/state/gmail-tidy}"
mkdir -p "$GMAIL_TIDY_HOME"
OUT=${2:-$GMAIL_TIDY_HOME/inbox_raw.tsv}
SIZE=${3:-100}
GOG=${GOG_BIN:-gog}
PAGE_DELAY=${PAGE_DELAY:-6}
BACKOFF=${BACKOFF:-65}
MAX_PAGES=${MAX_PAGES:-0}

acct=""
[ -n "${GOG_ACCOUNT:-}" ] && acct="$GOG_ACCOUNT"

run() { # $1 = page token ("" = first page)
  if [ -n "$1" ]; then
    if [ -n "$acct" ]; then $GOG -a "$acct" gmail search "$Q" --max "$SIZE" --page "$1" --plain
    else $GOG gmail search "$Q" --max "$SIZE" --page "$1" --plain; fi
  else
    if [ -n "$acct" ]; then $GOG -a "$acct" gmail search "$Q" --max "$SIZE" --plain
    else $GOG gmail search "$Q" --max "$SIZE" --plain; fi
  fi
}

# dry-run 检查：gog 可用、已授权
if ! command -v "$GOG" >/dev/null 2>&1; then
  echo "找不到 gog（可用 GOG_BIN 指定路径）" >&2; exit 127
fi

: > "$OUT"
page=""; n=0; rows=0; header=0; pages=0
while :; do
  pages=$((pages + 1))
  out=$(run "$page" 2>&1) || true
  if printf '%s' "$out" | grep -q rateLimitExceeded; then
    echo "  page $pages: 触发限流，退避 ${BACKOFF}s" >&2
    sleep "$BACKOFF"
    out=$(run "$page" 2>&1) || true
    if printf '%s' "$out" | grep -q rateLimitExceeded; then
      echo "  page $pages: 仍然限流，停止（已存 $rows 行）" >&2; break
    fi
  fi
  if printf '%s' "$out" | grep -qE 'quota|permission|未经授权|not authorized|error' && \
     ! printf '%s' "$out" | grep -q '^1'; then
    case "$out" in
      *"Google API error"*) echo "  API 错误: $(printf '%s' "$out" | head -1)" >&2; break;;
    esac
  fi

  body=$(printf '%s\n' "$out" | grep -v '^#')
  if [ "$header" -eq 0 ]; then
    printf '%s\n' "$body" | head -1 > "$OUT"
    header=1
    body=$(printf '%s\n' "$body" | tail -n +2)
  fi
  n=$(printf '%s\n' "$body" | grep -c . || true)
  if [ "$n" -gt 0 ]; then printf '%s\n' "$body" >> "$OUT"; rows=$((rows + n)); fi

  page=$(printf '%s\n' "$out" | grep -oE '\-\-page [^ ]+' | head -1 | cut -d' ' -f2 || true)
  echo "  page $pages: +$n 行, 累计 $rows${page:+, 有下一页}" >&2
  [ -z "$page" ] && break
  if [ "$MAX_PAGES" -gt 0 ] && [ "$pages" -ge "$MAX_PAGES" ]; then
    echo "  已达 MAX_PAGES=$MAX_PAGES，停止" >&2; break
  fi
  sleep "$PAGE_DELAY"
done
echo "rows=$rows"
