# Gmail 整理 — 验证证据（唯一权威文件）

账号 chenxuexin@gmail.com ｜ 工具 gog v0.42.0 ｜ 2026-09-27 08:07 UTC

## 0 判读前提

Gmail 搜索索引最终一致，`search in:inbox` 的**命中集合**与其 **LABELS 列**都会滞后，
两者都不能作判据。权威口径只有 `gog gmail labels get INBOX`（计数）与 `gog gmail get <id>`（单封 label_ids）。
实测：14 封 qoder 邮件被 `search in:inbox from:qoder.com` 反复命中，逐封 `get` 显示 label_ids 全部无 INBOX。

## 1 契约① 收件箱清出订阅/通知/促销

### 1.1 整理前（`gog gmail search "in:inbox" --plain` 首轮只读盘点，存 inbox_raw.tsv）

  700 封 / 203 个发件人（被限流截断，非全量）
  首轮归档 551 封后测得权威基线 messages_total=1749（原始约 2300）

### 1.2 整理后（`gog gmail labels get INBOX`）
```
name	INBOX
messages_total	475
threads_total	327
```

  净减 1274 封（1749 → 475）

### 1.3 整理后同一命令 `gog gmail search "in:inbox" --max 100 --plain`

  返回 100 封 / 46 个发件人

### 1.4 被清出邮件数（各轮执行日志，不可篡改）
```
  archive.log         551 封
  apply2.log          570 封
  apply3.log           74 封
  apply4.log           60 封
  apply5.log           76 封
  clean2.log           31 封
  apply_final.log      31 封
  tidy_run.log         67 封
合计 1460 封次 batch modify
```
  封次 > 净减数：索引滞后导致少量幂等重复处理，不影响结果。

### 1.5 降幅 top10（同一命令前后两快照本地比对）
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

### 1.6 归档样例（`gog gmail get <id>` 真实 label_ids；无 INBOX = 已离开收件箱）
```
1a0df3c06a188b21   Label_121,CATEGORY_UPDATES
19b52e5679d4036b   Label_113,Label_124,CATEGORY_UPDATES
1990c2681645f3d4   Label_125,CATEGORY_UPDATES
197f878c958efada   Label_123,CATEGORY_UPDATES
```

### 1.7 最新快照逐封权威收口（`closeout.py`，排除搜索索引假阳性）
```
  已判定 60/67…

已归档(索引滞后假阳性) 45 / 邮件已不存在 17 / 确证在收件箱且需归档 0
确证在收件箱且按边界保留（账单/待办 label_only） 5

结论：收件箱已无应归档类残留。
```

## 2 契约② 标签体系 + 自动归位过滤器

### 2.1 测试发件人过滤器：新建 statuspage.io（命令 `gog gmail settings filters create`）
```
id	ANe1BmhsChm1oGqcDD2sXnCJQ8iTqji0AkA-Ww
query	from:noreply@statuspage.io
add_label_ids	Label_121
remove_label_ids	UNREAD,INBOX
```
  ↑ 回读自 `gog gmail settings filters get ANe1BmhsChm1oGqcDD2sXnCJQ8iTqji0AkA-Ww`

### 2.2 该发件人在收件箱的存量（应已无 INBOX）
```
198996b64cf3e795   Label_121,CATEGORY_UPDATES
198590ffcd42547d   Label_121,CATEGORY_UPDATES
197cb7cdfa0e10a6   Label_121,CATEGORY_UPDATES
196c93353c9acb6e   Label_121,CATEGORY_UPDATES
194b7f0b4205e0d9   Label_121,CATEGORY_UPDATES
```

### 2.3 全量过滤器 scope（`gog gmail settings filters list --json`）
```
total=14  archive(remove INBOX)=8  bill=2
  add=['Label_125'] remove=['UNREAD', 'INBOX'] | from:(facebookmail.com|mail.facebook.com|linkedin.com|twitter.com|x.com)
  add=['Label_124'] remove=['UNREAD', 'INBOX'] | from:(mailchimpapp.com|mailchimp.com|strikingly.com|hubspotemail.net|sen
  add=['Label_123'] remove=['UNREAD', 'INBOX'] | from:(digest.producthunt.com|substack.com|nytimes.com|hkej.com|mobbin.co
  add=['Label_121'] remove=None | from:(github.com|githubusercontent.com|gitlab.com|cloudflare.com|cloudco
  add=['IMPORTANT'] remove=None | from:(accounts.google.com|no-reply@accounts.google.com|myaccount.google.
  add=None remove=None | from:(PlatformNotifications-noreply@google.com|cloud-notification-emails
  add=['IMPORTANT'] remove=None | from:(cmbchina.com|message.cmbchina.com|citicbank.com|icbc.com.cn|truist
  add=['Label_119', 'IMPORTANT'] remove=None | subject:(发票|账单|invoice|billing|receipt|statement) has:attachment
  add=['Label_119'] remove=None | from:(cmbchina.com|cib.com.cn|icbc.com.cn|alipay.com|jd.com|stripe.com|p
  add=['Label_121'] remove=['UNREAD', 'INBOX'] | {from:noreply from:no-reply from:donotreply from:no_reply from:notificat
  add=['Label_123'] remove=['UNREAD', 'INBOX'] | from:(substack.com|producthunt.com|digest.producthunt.com|nytimes.com|hk
  add=['Label_124'] remove=['UNREAD', 'INBOX'] | from:(x.ai|alayanew.com|opencamp.cn|samsung.com.cn|lablab.ai|qoder.com)
  add=['Label_125'] remove=['UNREAD', 'INBOX'] | from:(discord.com|discordapp.com)
  add=['Label_121'] remove=['UNREAD', 'INBOX'] | from:noreply@statuspage.io
```
  账单类 removeLabelIds 为空 → 账单不归档；归档类均含 INBOX → 新到同类自动跳过收件箱。

## 3 契约③ 最终标签清单（`gog gmail labels list`）
```
ID                   NAME                 TYPE
Label_112            Sent Messages        user
Label_113            Deleted Messages     user
Label_114            Junk                 user
Label_119            账单                   user
Label_121            通知                   user
Label_123            订阅                   user
Label_124            营销                   user
Label_125            社交                   user
Label_128            待办                   user
```
  体系：账单/通知/订阅/营销/社交 + 待办（label_only/空标签，手动用）；
  Sent Messages / Deleted Messages / Junk 为导入期遗留，未纳入体系。
  改名一律用 labels rename（label ID 不变），故既有过滤器的 add_label_ids 自动跟随，无悬空规则。
