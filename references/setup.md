# gog 授权（headless / 服务器）

脚本依赖 `gog`（[openclaw/gogcli](https://github.com/openclaw/gogcli)，命令名 `gog`）与 `gmail.modify` scope。

## 1. 安装 gog

```bash
# 官方安装脚本 / Homebrew
brew install openclaw/tap/gogcli          # macOS / Linux
# 或下载 release 里对应平台的单文件二进制 gog（无运行时依赖）放到 PATH
gog --version
```

## 2. 创建 OAuth 客户端

`gog` 不用 `gcloud` 的凭据，需要自己的 OAuth client（Desktop 类型）：

1. 打开 https://console.cloud.google.com/apis/credentials
2. 选/建一个项目 → **Create Credentials → OAuth client ID → Desktop app → Download JSON**

## 3. 存入客户端

```bash
mkdir -p ~/.config/gogcli
gog auth credentials ~/client_secret_xxx.json
# 期望落到 ~/.local/share/gogcli/credentials.json
```

Desktop client 的 `client_secret` 不是真正的机密（installed app 没法保密），但仍建议别提交进仓库。

## 4. 授权账号（headless 用 remote 两步法）

```bash
gog auth add you@example.com --remote --step 1 --services gmail,calendar,drive
# 复制打印出的 auth_url，手机/电脑浏览器打开、同意
# 同意后浏览器会跳到打不开的 127.0.0.1:xxxx 页面 —— 正常
# 把地址栏那一整条 URL 复制回来
gog auth add you@example.com --remote --step 2 --services gmail,calendar,drive \
  --auth-url '<把整条 redirect URL 粘这里>'
gog auth list
```

> 直接 `gog auth add <email> --manual` 需要交互式粘贴 redirect URL；非交互环境（CI、agent 子进程）请用 `--remote --step 1/2`。

## 5. keyring（非交互必须）

`gog` 默认把 token 放 keyring。headless / CI / agent 子进程没有 TTY，会报
`no TTY available for keyring file backend password prompt; set GOG_KEYRING_PASSWORD`。

```bash
export GOG_KEYRING_BACKEND=file
export GOG_KEYRING_PASSWORD='你的密码'
```

密码靠环境变量传，**子进程/服务必须继承同一环境**——只在登录 shell 里 export 过，不代表 systemd / agent 也拿得到。想一劳永逸，包一层 wrapper：

```sh
#!/bin/sh
# /usr/local/bin/gog
[ -n "$GOG_KEYRING_PASSWORD" ] || GOG_KEYRING_PASSWORD="$(cat ~/.config/gogcli/keyring.pass)"
export GOG_KEYRING_PASSWORD
export GOG_KEYRING_BACKEND=file
: "${GOG_QUOTA_PROJECT:=your-project-id}"; export GOG_QUOTA_PROJECT
exec /usr/local/bin/gog.bin "$@"
```

`GOG_QUOTA_PROJECT`：用自建 OAuth client / access token 时，部分 API 需要带 `X-Goog-User-Project` 头，填你的 GCP project id。

## 6. 体检

```bash
gog auth list
gog auth doctor --check --no-input     # keyring 健康、refresh token 有效性
gog gmail search "in:inbox" --max 1     # 能列出即授权 OK
```

## 只想读 Drive、不要额外 OAuth client？

`gcloud auth login --enable-gdrive-access` 签发的 token 带 `auth/drive` scope，可直接喂 gog：

```bash
export GOG_ACCESS_TOKEN="$(gcloud auth print-access-token)"
export GOG_QUOTA_PROJECT=your-project-id
gog drive ls --max 3
```

局限：gcloud 客户端只被允许 `cloud-platform` + `drive` 这类 scope，**Gmail / Calendar 拿它调会 403 insufficientPermissions**（`gcloud auth login` 本版没有 `--scopes` 参数）。要 Gmail 就得自己建 client（上面第 2 步）。

## 只读模式（安全阀）

```bash
gog --readonly gmail search ...      # 禁止一切写操作，误跑也不改数据
gog --gmail-no-send ...              # 单独禁发信
```
