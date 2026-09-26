#!/bin/sh
# 只读：分页拉取 Gmail 查询结果（表头 + TSV 行）。
#
# 节流原则（2026-09 实测：consumer Gmail + 自建 OAuth client）：
#   配额按"返回结果条数"计，不是按请求数。实测 --max 10 连续 16 次成功
#   （≈160 条 / 33 秒）后被限流；大页(100)常在第 2 页就撞限流。
#   → 每分钟预算约 200~300 条结果。宁可小页慢拉，也不追风控。
#   命中限流：90s 起退避，每次 ×2（上限 300s）+ 随机抖动；连续 3 次仍失败则停止。
#   连续 3 页成功才把间隔降回基准。
#
# 用法: fetch_query.sh "<gmail-query>" [out.tsv] [page_size]
# 环境: GOG_BIN GOG_ACCOUNT GMAIL_TIDY_HOME
#       PAGE_DELAY(默认 30s) MAX_DELAY(300) BACKOFF(90) MAX_PAGES(0=全部) RESUME(1)
# 断点续拉: 进度存 $GMAIL_TIDY_HOME/.fetch_state.<hash>，重跑自动从上次 token 继续。
set -eu

Q=${1:?用法: fetch_query.sh "<gmail-query>" [out.tsv] [page_size]}
: "${GMAIL_TIDY_HOME:=$HOME/.local/state/gmail-tidy}"
mkdir -p "$GMAIL_TIDY_HOME"
OUT=${2:-$GMAIL_TIDY_HOME/inbox_raw.tsv}
SIZE=${3:-50}
GOG=${GOG_BIN:-gog}

BASE_DELAY=${PAGE_DELAY:-30}
MAX_DELAY=${MAX_DELAY:-300}
BACKOFF=${BACKOFF:-90}
MAX_PAGES=${MAX_PAGES:-0}
RESUME=${RESUME:-1}

STATE="$GMAIL_TIDY_HOME/.fetch_state.$(printf '%s' "$Q" | cksum | cut -d' ' -f1)"

command -v "$GOG" >/dev/null 2>&1 || { echo "找不到 gog（可用 GOG_BIN 指定）" >&2; exit 127; }

# 0~40% 随机抖动，避免固定节奏
jitter() { awk -v s="$1" 'BEGIN{srand();print int(s*0.4*rand())}'; }

run() {
  if [ -n "${GOG_ACCOUNT:-}" ]; then
    if [ -n "$1" ]; then $GOG -a "$GOG_ACCOUNT" gmail search "$Q" --max "$SIZE" --page "$1" --plain
    else $GOG -a "$GOG_ACCOUNT" gmail search "$Q" --max "$SIZE" --plain; fi
  else
    if [ -n "$1" ]; then $GOG gmail search "$Q" --max "$SIZE" --page "$1" --plain
    else $GOG gmail search "$Q" --max "$SIZE" --plain; fi
  fi
}

page=""; rows=0; fresh=1
if [ "$RESUME" = "1" ] && [ -s "$STATE" ] && [ -s "$OUT" ]; then
  page=$(sed -n 's/^token=//p' "$STATE")
  rows=$(sed -n 's/^rows=//p' "$STATE")
  fresh=0
  echo "断点续拉：已有 $rows 行，从 ${page:-首页} 继续" >&2
fi
if [ "$fresh" -eq 1 ]; then
  : > "$OUT"
  printf 'token=\nrows=0\n' > "$STATE"
fi

delay=$BASE_DELAY
clean=0
pages=0
while :; do
  pages=$((pages + 1))
  out=$(run "$page" 2>&1) || true

  attempt=0
  while printf '%s' "$out" | grep -q rateLimitExceeded; do
    if [ "$attempt" -ge 3 ]; then
      echo "连续 3 次退避仍限流，停止（进度已保存，重跑可续）" >&2
      exit 0
    fi
    w=$(( BACKOFF * (1 << attempt) ))
    [ "$w" -gt "$MAX_DELAY" ] && w=$MAX_DELAY
    w=$(( w + $(jitter "$w") ))
    echo "  page $pages: 限流，退避 ${w}s" >&2
    sleep "$w"
    out=$(run "$page" 2>&1) || true
    attempt=$((attempt + 1))
  done

  body=$(printf '%s\n' "$out" | grep -v '^#' || true)
  if [ "$fresh" -eq 1 ]; then
    printf '%s\n' "$body" | head -1 > "$OUT"
    body=$(printf '%s\n' "$body" | tail -n +2)
    fresh=0
  fi
  n=$(printf '%s\n' "$body" | grep -c . || true)
  if [ "$n" -gt 0 ]; then
    printf '%s\n' "$body" >> "$OUT"
    rows=$((rows + n))
  fi

  page=$(printf '%s\n' "$out" | grep -oE '\-\-page [^ ]+' | head -1 | cut -d' ' -f2 || true)
  printf 'token=%s\nrows=%s\n' "$page" "$rows" > "$STATE"
  echo "  page $pages: +$n 行, 累计 $rows, 间隔 ${delay}s${page:+, 有下一页}" >&2

  [ -z "$page" ] && break
  if [ "$MAX_PAGES" -gt 0 ] && [ "$pages" -ge "$MAX_PAGES" ]; then
    echo "  已达 MAX_PAGES=$MAX_PAGES，停止（进度已保存）" >&2
    break
  fi

  clean=$((clean + 1))
  if [ "$clean" -ge 3 ]; then
    nd=$(( delay * 4 / 5 ))
    [ "$nd" -lt "$BASE_DELAY" ] && nd=$BASE_DELAY
    delay=$nd
    clean=0
  fi
  sleep $(( delay + $(jitter "$delay") ))
done

echo "rows=$rows"
