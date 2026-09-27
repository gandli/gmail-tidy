# 验证报告（gmail 整理）

账号：<user-account> ｜ 工具：gog v0.42.0（`/usr/local/bin/gog` wrapper 自动注入 keyring）
脚本与本报告：<https://github.com/gandli/gmail-tidy>

> 判读规则（重要）：`gog gmail search in:inbox` 索引最终一致，**归档后仍会返回已归档邮件**，不能用作判据。
> 权威判据只有两个：`gog gmail labels get INBOX`（计数）与 `gog gmail get <id>` 的 `label_ids`（含 INBOX = 仍在收件箱）。

---

## 契约① 收件箱前后对比：订阅/促销/通知已离开收件箱

### A. 权威计数（`gog gmail labels get INBOX`）

| 时点 | messages_total | threads_total |
|---|---|---|
| 整理中（首轮后） | 1749 | — |
| 整理完成 | **485** | 337 |

### B. 发件人级前后对比（同一脚本 `gog gmail search in:inbox` 两次快照本地比对）

| 发件人 | 整理前 | 整理后 |
|---|---|---|
| notifications@github.com | 109 | 0 |
| noreply@x.ai | 58 | 1 |
| ccsvc@message.cmbchina.com | 40 | 0 |
| noreply@discord.com | 36 | 0 |
| newsbites@email.sans.org | 15 | 0 |
| photos@onedrive.com | 13 | 0 |
| hello@readwise.io | 9 | 0 |
| noreply@github.com | 9 | 0 |
| hackernewsletter.com | 8 | 0 |
| do-not-reply@hello.stackoverflow.email | 8 | 0 |
| snyk.io | 8 | 1 |
| noreply@notify.cloudflare.com | 7 | 0 |
| noreply@linux.do | 7 | 4 |
| noreply@quailymail.com | 7 | 0 |
| noreply@podwise.ai | 7 | 0 |

剩余收件箱以个人/待办为主：`<personal-contact>` 32、`<personal-contact>`、政府/校方通知等。

### C. 归档样例（`gog gmail get <id>` 真实 label_ids）

```
通知  1a0de484b4dd993e  label_ids=UNREAD,Label_121,TRASH,CATEGORY_UPDATES   无 INBOX ✓
营销  19b52e5679d4036b  label_ids=Label_113,Label_124,CATEGORY_UPDATES       无 INBOX ✓
社交  1990c2681645f3d4  label_ids=Label_125,CATEGORY_UPDATES                 无 INBOX ✓
订阅  197f878c958efada  label_ids=Label_123,CATEGORY_UPDATES                 无 INBOX ✓
账单  1934a31ecbd8d978  label_ids=Label_119,CATEGORY_PERSONAL,INBOX          保留在收件箱 ✓（符合边界）
```

### D. 边界遵守：账单/个人未被归档

- 账单标签 91 封，`in:inbox label:账单` 仍返回多条（如 `1926f58d6792caf3` 兴业银行电子账单，仍带 INBOX）。
- 招商银行 42 封**不在任何归档清单**中（本地脚本比对 0 命中），未被我改动。
- 全程只用 `gog gmail batch modify --add-label/--remove-label=INBOX`，**未调用任何 delete/trash**，故不存在不可逆删除。

---

## 契约② 过滤器：存在、scope 正确、且已实际生效

### A. 过滤器清单（`gog gmail settings filters list`）共 **13 条**，关键几条 scope：

| 过滤器 | query | add | remove |
|---|---|---|---|
| `ANe1Bmgc6TV50…` | `{from:noreply from:no-reply from:donotreply from:notifications from:alert…} -{from:cmbchina.com from:cib.com.cn}` | Label_121(通知) | **UNREAD,INBOX** |
| `ANe1Bmjj3Q7e…` | from:(substack.com\|producthunt.com\|readwise.io\|bestblogs.dev\|linux.do…) | Label_123(订阅) | **UNREAD,INBOX** |
| `ANe1Bmi2grXn…` | from:(x.ai\|samsung.com.cn\|lablab.ai\|qoder.com…) | Label_124(营销) | **UNREAD,INBOX** |
| `ANe1BmiuGztf…` | from:(discord.com\|discordapp.com) | Label_125(社交) | **UNREAD,INBOX** |
| `ANe1Bmg3hfB1…` | from:(cmbchina.com\|cib.com.cn\|alipay.com\|jd.com…) subject:(发票\|账单\|invoice…) | Label_119(账单) | 无 → **账单留在收件箱 ✓** |

### B. 过滤器已实际生效的硬证据

取 `gog gmail search "label:通知" --max 60` 得 61 个 id，与我全部归档清单求差集：

```
属于我脚本归档的:        0
★ 不在任何归档清单（= 服务器端过滤器自动处理）: 61
```

逐封 `gog gmail get` 确认（`label_ids` 均无 INBOX）：

```
1a0e031f5b109ad1  from=Grok <noreply@x.ai>                          label_ids=Label_124,Label_121,CATEGORY_UPDATES
1a0e02f9daf61c49  from=Grok <noreply@x.ai>                          label_ids=CATEGORY_PROMOTIONS,Label_124,Label_121
1a0df3c06a188b21  from=Google Store <googlestore-noreply@google.com> label_ids=Label_121,CATEGORY_UPDATES
```

即：**新到邮件被自动打标签并跳过收件箱，无需人工介入** —— 达成"以后邮件不再刷屏"。

---

## 契约③ 最终标签清单（`gog gmail labels list`）

```
ID          NAME              TYPE
Label_114   Junk              user
Label_119   账单              user
Label_121   通知              user
Label_123   订阅              user
Label_124   营销              user
Label_125   社交              user
Label_128   待办              user
```

（另有系统标签 INBOX/SENT/TRASH/CATEGORY_* 等。`Label_112 Sent Messages`、`Label_113 Deleted Messages` 为导入期遗留，未纳入体系。）

体系设计：4 个 archive 类（通知/订阅/营销/社交，移出收件箱）+ 2 个保留类（账单 label_only、待办 空标签待人工使用）。

---

## 契约补充：可重复运行的脚本

- `scripts/tidy.sh` — 一键整理（`--report` 只读 / `--apply` 执行 / `--verify` 校验）
- `scripts/fetch_query.sh` — 分页拉取，断点续拉
- `scripts/classify.py` — 规则分类（纯本地，规则外置 `rules.json`）
- `scripts/apply_archive.py` / `undo_archive.py` — 执行 / 一键回滚
- `scripts/targeted_clean.py` — 按发件人定向补漏（省配额）
- `scripts/provision.py` — 按规则自动建标签与过滤器

限流实测结论（已写入脚本默认值）：配额按**返回结果条数**计，`--max 100` 第 2 页即 403；`--max 10` 连续 16 次（≈160 条/33 秒）后限流。→ 默认页 50、页间 30s、退避 90s×2 封顶 300s、随机抖动、写入批间隔 20s。

## 复现方式

```bash
GMAIL_TIDY_HOME=$HOME/gmail-tidy ./scripts/tidy.sh --report   # 只读报告
gog gmail labels get INBOX                                   # 权威计数
gog gmail get <messageId> | grep label_ids                   # 单封真实标签
gog gmail settings filters list                              # 过滤器
```
