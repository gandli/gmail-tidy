# Gmail 过滤器速查

归档只清历史，**新邮件靠过滤器**。用 `provision.py` 从 `rules.json` 自动生成，别手抄。

## 手动操作

```bash
gog gmail settings filters list                    # 现状
gog gmail settings filters get <filterId>           # 单条详情（看 add_label_ids / remove_label_ids）
gog gmail settings filters create \
  --query 'from:(noreply@x.com|no-reply@y.org)' \
  --add-label=通知 --archive --mark-read
gog gmail settings filters delete <filterId>
gog gmail settings filters export                  # 导出成 Gmail 网页版可导入的 XML
```

常用动作 flag：`--add-label` `--remove-label` `--archive`（跳过收件箱）`--mark-read` `--star` `--important` `--never-spam`。`--trash` 也能加，但本工具默认不删邮件。

## 匹配语法（Gmail search）

- `from:(a@x.com|b@y.com)` — 或
- `{from:noreply from:no-reply from:alert}` — 或一组
- `-{from:bank.com}` — 排除
- `subject:(发票|invoice|receipt)`
- `has:attachment` `-category:promotions`

## 关键坑：标签 ID vs 名字

`gog gmail settings filters get` 返回的是 `add_label_ids`（`Label_121` 这种），**不是名字**。

- `gog gmail labels rename` 只改显示名，**label ID 不变** → 旧过滤器自动跟着改名后的标签走。改名用 rename。
- `gog gmail labels delete` + `create` 会**换 ID** → 旧过滤器指向一个不存在的 ID，静默失效。所以永远别"删了重建"来改名。

本项目改标签体系时用的是 rename（把 `通知/技术` 改成 `通知`），因此历史过滤器无需重建。

## 多条过滤器冲突

Gmail 会**同时应用**所有命中的过滤器。若不处理，一封银行账单可能既被"账单"（保留）又被"通知"（归档）命中 → 归档动作生效 → 误移出收件箱。

解法：给所有 `archive` 类过滤器加 `-{from:...}` 排除掉 `label_only`（账单/待办）类的发件人。`provision.py` 已自动从 `rules.json` 的 `label_only` 类别生成这些排除项。
