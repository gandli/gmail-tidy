---
name: gmail-tidy
description: 用 gog CLI 把 Gmail 收件箱从通知/订阅/营销/社交邮件堆里清出来，自动打标签、归档，并配服务器端过滤器让新邮件不再刷屏。当用户说"整理邮箱""清理收件箱""gmail 归档""收件箱太多""退订刷屏""重新分类邮件"，或要跑/改这套整理流程时使用。
---

# Gmail 整理（gog 版）

一套**只读盘点 → 规则分类 → 批量归档 → 过滤器兜底**的流水线。核心原则：账单/个人/待办留在收件箱，通知/订阅/营销/社交移出收件箱并打标签。

## 前置

`gog` 已装且账号已授权 `gmail.modify`：

```bash
gog auth list                              # 看是否已授权
gog auth doctor --check --no-input         # keyring/token 健康
```

未授权（新机器/headless）见 [references/setup.md](references/setup.md)。

## 用法

```bash
cd scripts/

./tidy.sh --report     # 只读：抓快照 + 出分类报告，不改任何邮件
./tidy.sh --dry-run    # 同上，明确标出"将要归档哪些"
./tidy.sh              # 执行：归档 + 打标签（幂等，可重复跑）
python3 undo_archive.py   # 回滚上一次归档（放回收件箱、去掉标签）
```

首次建议先 `--report`，看清数字再执行。归档**不是删除**，邮件仍在"所有邮件"里，可随时搜到。

## 流水线

```
fetch_query.sh  →  inbox_raw.tsv        只读，分页拉快照（带限流退避）
classify.py     →  manifest.json        纯本地按规则分档，零 API
apply_archive.py→  archive_manifest.json  gog batch modify 批量归档+打标签
tidy.sh         →  串起上面 + 结果报告
undo_archive.py                          反向：--remove-label 标签 --add-label INBOX
```

## 分类规则

标签体系（扁平 6 档，够用就好）：

| 标签 | 收什么 | 收件箱 |
|---|---|---|
| `通知` | 机器播报：noreply/no-reply/notification/alert | 归档 |
| `订阅` | newsletter、beehiiv、substack、周刊/日报 | 归档 |
| `营销` | promo、discount、活动邀请、产品推送 | 归档 |
| `社交` | discord、linkedin、facebook | 归档 |
| `账单` | 发票/对账单/消费通知/订单 | **保留** |
| `待办` | 需你行动（手动打，脚本不自动填） | **保留** |

`classify.py` 里两层匹配：**EXPLICIT**（具体发件人，最高优先级）+ **PATTERNS**（域名/关键词正则，让新发件人自动命中）。没命中的默认 `KEEP`（安全档，留在收件箱）。改分类只需改这两张表，不用碰归档逻辑。

**默认 KEEP 是刻意的**——宁可漏归档，不可误归档。账单类即使在 PATTERNS 里命中"账单"也强制保留（见 classify.py 的 `b in ("KEEP","账单")`）。

## 归档后怎么验证（重要）

**`gog gmail search "in:inbox from:X"` 不权威。** Gmail 搜索索引最终一致：邮件已经移出收件箱并打好标签了，`search in:inbox` 仍会返回它（本地实测：归档后 14 封 qoder 邮件仍被 `in:inbox` 命中，而 `gog gmail get <id>` 的 `label_ids` 里已无 `INBOX`）。

用这两条代替：

```bash
# 1) 收件箱总量（权威，一次调用）
gog gmail labels get INBOX | awk -F'\t' '/messages_total/{print $2}'

# 2) 单封邮件的真实标签（权威）
gog gmail get <messageId> | grep label_ids      # 不含 INBOX = 已归档
```

只有当第 2 条显示 `label_ids` 里确实还有 `INBOX` 时，才是真的漏归档，重跑 `targeted_clean.py`。

## 配额

Gmail API 按"每分钟查询成本"限流，`--count` 很贵（内部拉 500 封详情），脚本已避开。表现是 `403 rateLimitExceeded`。脚本内置退避（65s→130s→195s，3 次后放弃）。手动调试时 `sleep 60` 再试，别连发。

## 过滤器（服务器端兜底）

归档只清历史；**新邮件靠过滤器**。`./tidy.sh --provision-dry` 看计划，`./tidy.sh --provision` 真正创建（标签缺失会自动建、已存在的过滤器会跳过，幂等）。

```bash
gog gmail settings filters list                 # 看现状
gog gmail settings filters create --query '...' --add-label=通知 --archive --mark-read
gog gmail settings filters delete <filterId>     # 删某条
```

坑：`--add-label` 用**标签名**；改名后旧过滤器指向的是 **label ID**，`gog gmail labels rename` 会保住 ID（因此旧过滤器自动跟随）；但 `delete` 再 `create` 会换 ID，**旧过滤器就指向不存在的标签**。所以要改标签名用 rename，别删了重建。

账单类过滤器**只打标签不加 `--archive`**（要留在收件箱）。同时给"通知"过滤器加排除项（如 `-{from:bank.example.com}`，实际写你的银行/支付方），否则银行邮件会被"通知"和"账单"两条过滤器同时命中而误归档。`provision.py` 会自动从 `rules.json` 的 `label_only` 类别生成这些排除项。
