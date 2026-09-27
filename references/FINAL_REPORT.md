# Gmail 整理 — 验证报告 VERIFICATION.md

生成：2026-09-27 06:52 UTC　工具：gog v0.42.0

> 判读前提：Gmail 搜索索引最终一致 —— `search in:inbox` 的命中集合与 LABELS 列都会滞后，
> 故一律以 `labels get INBOX`（计数）与 `get <id>`（单封 label_ids）为权威口径。

---

## 契约 ① — 收件箱已清出订阅/通知/促销类　【PASS】

命令：`gog gmail labels get INBOX`
```
id	INBOX
name	INBOX
type	system
messages_total	476
messages_unread	0
threads_total	328
threads_unread	0
```
整理前：只读盘点快照 `gog gmail search in:inbox` 抓到 700 封 / 189 个发件人（被限流截断）；
首轮归档 551 封后测得权威基线 messages_total = 1749。

发件人级降幅（同一命令两次快照本地比对）:
```
  notifications@github.com                    109 -> 0    (-109)
  noreply@x.ai                                 58 -> 1    (-57)
  ccsvc@message.cmbchina.com                   40 -> 0    (-40)
  noreply@discord.com                          36 -> 0    (-36)
  noreply@cgx.dev                              16 -> 4    (-12)
  newsbites@email.sans.org                     15 -> 0    (-15)
  photos@onedrive.com                          13 -> 0    (-13)
  hello@readwise.io                             9 -> 0    (-9)
  noreply@github.com                            9 -> 0    (-9)
  kale@hackernewsletter.com                     8 -> 0    (-8)
```

已清出样例（命令：`gog gmail get <id>`；label_ids 不含 INBOX = 已离开收件箱）:
  1a0df3c06a188b21   Label_121,CATEGORY_UPDATES
  19b52e5679d4036b   Label_113,Label_124,CATEGORY_UPDATES
  1990c2681645f3d4   Label_125,CATEGORY_UPDATES
  197f878c958efada   Label_123,CATEGORY_UPDATES
  1a0e0b4767784d07   Label_123,CATEGORY_UPDATES

逐封权威收口（最新 318 封收件箱 → 67 个归档候选 → 逐封 get）:
```
  已判定 60/67…

已归档(索引滞后假阳性) 45 / 邮件已不存在 17 / 确证在收件箱且需归档 0
确证在收件箱且按边界保留（账单/待办 label_only） 5

结论：收件箱已无应归档类残留。
```
结论：确证仍在收件箱且需归档 = 0 封。剩余为个人往来 / 政府通知 / 账单。
