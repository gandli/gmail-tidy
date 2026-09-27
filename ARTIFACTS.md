# 本目录是什么

Gmail 收件箱整理的**工作目录**（原始数据 + 执行日志 + 分类清单）。

| 文件 | 内容 |
|---|---|
| `VERIFICATION.md` | **验收报告**（三条契约的实测输出与边界说明） |
| `inbox_raw.tsv` | **整理前**只读盘点快照（705 行，限流截断） |
| `final_check.tsv` | **整理后**收件箱快照 |
| `arch_sum.txt` | 各轮 batch modify 封次记录 |
| `latest_closeout.log` | 逐封 `messages.get` 权威收口结果 |
| `tidy.sh` | **一键再清**入口（`--report` 只读 / `--apply` 执行） |
| `closeout.py` | 权威收口（绕开 search 索引滞后） |
| `rules.json` | 本账号分类规则（标签名已对齐实际标签） |
| `undo_archive.py` | 一键回滚 |
| `*.log` | 各轮执行日志 |

复核入口：<https://github.com/gandli/gmail-tidy>
