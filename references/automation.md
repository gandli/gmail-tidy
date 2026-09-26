# 自动化整理（定时跑）

`tidy.sh` 是幂等的，可以交给 cron / systemd timer 定期跑。

## cron

```bash
crontab -e
# 每天 07:20 整理一次（错开整点，避免和别人的定时任务撞一起被限流）
20 7 * * * cd /path/to/scripts && ./tidy.sh --apply >> ~/gmail-tidy.log 2>&1
```

cron 的环境极简，`gog` 若依赖 keyring 密码或自定义 PATH，记得在脚本里显式给：

```cron
GOG_BIN=/usr/local/bin/gog GOG_KEYRING_PASSWORD_FILE=~/.config/gogcli/keyring.pass 20 7 * * * ...
```

若用 §setup.md 里的 wrapper（把 keyring 密码注入好），cron 直接调 `gog` 即可。

## systemd timer（用户级）

`~/.config/systemd/user/gmail-tidy.service`：

```ini
[Unit]
Description=Gmail inbox tidy

[Service]
Type=oneshot
Environment=GOG_BIN=/usr/local/bin/gog
WorkingDirectory=/path/to/scripts
ExecStart=/path/to/scripts/tidy.sh --apply
```

`~/.config/systemd/user/gmail-tidy.timer`：

```ini
[Unit]
Description=Daily Gmail inbox tidy

[Timer]
OnCalendar=*-*-* 07:20:00
RandomizedDelaySec=1800        # 随机偏移，别固定在同一秒
Persistent=true                # 关机错过的会补跑

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now gmail-tidy.timer
systemctl --user list-timers | grep gmail
```

systemd 服务**不读 shell profile**，`GOG_KEYRING_PASSWORD` 必须注入到 unit 的 `Environment=`（或用 §setup.md 里的 wrapper 把密码读进环境）。用 wrapper 时 unit 里只需 `Environment=GOG_BIN=/usr/local/bin/gog`。

## 风控：定时任务的节奏

Gmail API 按"返回结果条数"计配额（实测每分钟约 200–300 条，见 §filters.md 顶部说明）。定时任务要注意：

- **别设成每 10 分钟跑一次**——收件箱没变化时会白拉一遍，白烧配额。
- 每天一次足够；过滤器本身已经让新邮件自动归位，定时任务只是兜底清理漏网的。
- `RandomizedDelaySec` 让多次运行不撞在同一秒，降低被风控概率。
- 拉取有断点续拉：中途被限流不会丢进度，重跑接着上次继续。

## 只跑过滤器（不改已有邮件）

新邮件的自动归位是服务器端过滤器做的，与定时任务无关。想只更新过滤器：

```bash
./tidy.sh --provision
```
