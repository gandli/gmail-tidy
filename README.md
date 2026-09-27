# gmail-tidy

> **验收证据**：见 [VERIFICATION.md](VERIFICATION.md)（收件箱前后对比、过滤器 scope 与新邮件命中、最终标签清单）。本仓库即「可重复运行整理脚本」的交付物。

用 [gog](https://github.com/openclaw/gogcli) CLI 把 Gmail 收件箱从通知 / 订阅 / 营销 / 社交邮件堆里清出来：
**自动打标签 → 归档 → 配服务器端过滤器让新邮件不再刷屏**。

```
fetch_query.sh → 收件箱快照（只读，分页+限流退避）
classify.py    → 按 rules.json 分类（纯本地，零 API）
apply_archive.py → 批量打标签+归档（幂等，可回滚）
provision.py   → 创建标签 + 过滤器（服务器端自动归位，新邮件自动跳过收件箱）
undo_archive.py → 一键回滚
```

## 设计

- **账单 / 个人 / 待办** 留在收件箱（`label_only` 或 `keep`）；**通知 / 订阅 / 营销 / 社交** 才归档（`archive`）。
- 匹配两层：`explicit`（具体发件人，最高优先级）+ `patterns`（正则，让新发件人自动归类）。兜底默认 `personal`（留在收件箱）——**宁可漏归档，不可误归档**。
- 分类规则全在 `rules.json`，与代码解耦；想换标签体系或增减规则只改这一个文件。
- 过滤器由 `provision.py` 从 `rules.json` 生成，`label_only` 类自动从 `archive` 过滤器的匹配里排除（避免银行账单被误归档）。

## 前置

需要已授权的 `gog`（至少 `gmail.modify`）。没授权见 [references/setup.md](references/setup.md)。

## 快速开始

```bash
cd scripts
cp rules.example.json $HOME/.local/state/gmail-tidy/rules.json   # 或 --rules 指定
# 把 rules.json 的 explicit 换成你自己的发件人 / 域名

./tidy.sh --report          # 只读：看分类报告，不改邮件
./tidy.sh --provision-dry   # 只看将建哪些标签 / 过滤器
./tidy.sh                   # （同上，dry-run）
./tidy.sh --provision      # 建标签 + 过滤器
./tidy.sh --apply          # 执行归档
python3 undo_archive.py      # 回滚
```

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `GMAIL_TIDY_HOME` | `~/.local/state/gmail-tidy` | 状态目录（快照 / 规则 / 计划都在这） |
| `GOG_BIN` | `gog` | gog 可执行文件 |
| `GOG_ACCOUNT` | （gog 默认账号） | 多账号时指定 |
| `MAX_PAGES` | `0`=全部 | 限制快照抓取页数 |

## 安全

- 默认所有操作都是 dry-run，必须显式 `--apply` 才动数据。
- 归档 = 移出收件箱 + 打标签，**不删除**，邮件仍在"所有邮件"里可搜到。
- 改标签名请用 `rename`，别删了重建（旧过滤器绑定 label ID，删了重建会让旧过滤器指向不存在标签，见 [references/filters.md](references/filters.md)）。
