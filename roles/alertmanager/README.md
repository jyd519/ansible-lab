# alertmanager

从 GitHub Releases 下载 Prometheus Alertmanager 并以 **加固后的 systemd 服务**方式安装。
默认单机（单节点）部署，支持通过变量覆盖下载地址、监听地址，并可选地启用 Web TLS + BasicAuth。

## 设计决策

### 安装方式：二进制下载 vs 包管理器

与 etcd 角色一致，选择从 GitHub Releases 直接下载二进制，而非 apt/yum：

- Alertmanager 官方不提供 deb/rpm 仓库，发行版自带的版本通常滞后
- 二进制下载可精确控制版本，跨发行版行为一致
- 下载前通过 `alertmanager --version` 做版本比对，实现幂等，避免重复下载

### 目录布局

| 路径 | 用途 | 属主 | 权限 | 说明 |
|---|---|---|---|---|
| `/usr/share/alertmanager/` | 二进制安装目录 | `root:root` | `0755` | 二进制只读，遵循 FHS |
| `/etc/alertmanager/` | 配置目录 | `root:alertmanager` | `0750` | root 可写，进程可读，其他用户不可访问 |
| `/etc/alertmanager/alertmanager.yml` | 主配置 | `root:alertmanager` | `0640` | 可能包含 webhook/SMTP 等敏感信息，禁止 world-read |
| `/etc/alertmanager/alertmanager.web.yml` | Web 安全配置(TLS/BasicAuth) | `root:alertmanager` | `0640` | 同上为敏感文件 |
| `/var/lib/alertmanager/` | 数据目录(nflog/silences) | `alertmanager:alertmanager` | `0700` | 仅进程可访问 |

二进制通过软链接到 `/usr/local/bin/`，使 `alertmanager` 和 `amtool` 在 PATH 中可用。

### 安全加固

**专用系统用户**：创建 `alertmanager` 用户/组（`system=true`, `shell=/usr/sbin/nologin`,
`create_home=false`），最小权限运行，不可登录。

**systemd 沙箱**：

| 指令 | 作用 |
|---|---|
| `ProtectSystem=full` | `/usr`, `/boot`, `/etc` 只读挂载 |
| `ProtectHome=true` | `/home`, `/root`, `/run/user` 不可访问 |
| `NoNewPrivileges=true` | 禁止通过 execve 提升权限 |
| `PrivateTmp=true` | 隔离 `/tmp` 命名空间 |
| `ReadWritePaths=/var/lib/alertmanager` | 仅允许写入数据目录 |
| `CapabilityBoundingSet=` / `AmbientCapabilities=` | 清空全部 Linux capabilities |
| `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX` | 仅允许网络/Unix socket 地址族 |
| `ProtectKernelTunables/Modules/ControlGroups=true` | 禁止篡改内核与 cgroup |
| `SystemCallArchitectures=native` | 禁止非本机架构的系统调用 |
| `LimitNOFILE=65536` | 提高文件描述符上限 |

**Web 传输安全（可选，推荐开启）**：通过 `--web.config.file` 启用 HTTPS 与
HTTP BasicAuth。证书路径与 BasicAuth 用户（bcrypt）由变量注入，配置文件权限 `0640`。
默认 `alertmanager_web_listen_address: "0.0.0.0:9093"` 对外监听，**一旦对外暴露务必开启 TLS+BasicAuth**，
否则 UI 与 API 将明文无鉴权暴露。

### 幂等性

- `alertmanager --version` 比对已装版本，版本一致时跳过下载/安装
- 临时下载文件安装后自动清理
- 主配置 / Web 安全配置 / 服务文件变更时通过 handler 触发 `daemon-reload` + `restart`

### 单机 vs 集群

- 默认单机：`--cluster.listen-address=0.0.0.0:9094"` 仍会尝试组建单成员集群（告警可正常去重/静默）
- 若需彻底关闭集群能力，将 `alertmanager_cluster_listen_address: ""` 即可（`--cluster.listen-address=`）

### 架构自动检测

通过 `ansible_architecture` 自动映射到发布包架构名（`x86_64 -> amd64`, `aarch64 -> arm64`），
开箱支持 x86 与 ARM 服务器。


## 变量说明

```yaml
# 版本
alertmanager_version: "0.34.0"

# 目录
alertmanager_install_dir: /usr/share/alertmanager   # 二进制安装位置
alertmanager_data_dir: /var/lib/alertmanager        # 数据持久化目录
alertmanager_config_dir: /etc/alertmanager          # 配置文件目录

# 运行用户
alertmanager_user: alertmanager
alertmanager_group: alertmanager

# 完整下载 URL：可整体覆盖以使用内网镜像
alertmanager_download_url: >-
  https://github.com/prometheus/alertmanager/releases/download/v{{ alertmanager_version }}/alertmanager-{{ alertmanager_version }}.linux-{{ alertmanager_arch }}.tar.gz

# 监听地址（默认对外）
alertmanager_web_listen_address: "0.0.0.0:9093"
alertmanager_web_external_url: ""        # 反向代理子路径时填，如 /alertmanager

# 集群（单机默认开启单成员集群；置空关闭）
alertmanager_cluster_listen_address: "0.0.0.0:9094"

# 主配置模板（如需自定义可改为自己的模板路径）
alertmanager_config_template: alertmanager.yml.j2

# --- Web TLS + BasicAuth ---
alertmanager_web_config_enabled: false   # 设为 true 启用
alertmanager_tls_cert_file: ""           # PEM 证书路径
alertmanager_tls_key_file: ""            # PEM 私钥路径
alertmanager_basic_auth_users: []        # 列表，每项 "user:$2y$05$..."（bcrypt）
```


## 使用示例

### 1. 单机 + 明文（仅本机/内网可信网络）

```yaml
- name: Install Alertmanager
  hosts: all
  become: yes
  roles:
    - alertmanager
```

### 2. 指定版本 / 内网镜像

```yaml
- name: Install Alertmanager from mirror
  hosts: all
  become: yes
  roles:
    - role: alertmanager
      alertmanager_version: "0.33.1"
      alertmanager_download_url: "https://mirror.example.com/alertmanager/alertmanager-0.33.1.linux-amd64.tar.gz"
```

### 3. 对外暴露 + TLS + BasicAuth（推荐）

生成 BasicAuth 凭据（bcrypt）：

```bash
htpasswd -nbB admin 'StrongPassword'
# admin:$2y$05$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

将证书与凭据通过变量传入（证书建议用 `ansible-vault` 加密后放 group_vars）：

```yaml
- name: Install secure Alertmanager
  hosts: all
  become: yes
  roles:
    - role: alertmanager
      alertmanager_web_listen_address: "0.0.0.0:9093"
      alertmanager_web_config_enabled: true
      alertmanager_tls_cert_file: /etc/alertmanager/tls.crt
      alertmanager_tls_key_file: /etc/alertmanager/tls.key
      alertmanager_basic_auth_users:
        - "admin:$2y$05$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

启用后访问：`https://<host>:9093/`，浏览器/客户端需带 BasicAuth 凭证。

### 4. 自定义告警路由（真实 receiver）

覆盖 `alertmanager_config_template` 指向你自己的模板，或在 `group_vars` 中维护：

```yaml
- role: alertmanager
  alertmanager_config_template: my-alertmanager.yml.j2
```


## 安装后验证

```bash
# 服务状态
systemctl status alertmanager

# 版本
alertmanager --version

# 集群/健康状态（amtool）
amtool status
amtool alert query

# 明文模式访问 UI
curl -s http://localhost:9093/-/ready

# TLS + BasicAuth 模式
curl -k -u admin:StrongPassword https://localhost:9093/-/ready

# 推送一条测试告警（需 Prometheus 客户端，或经 Alertmanager v2 API）
```

数据目录（静默规则、nflog）位于 `/var/lib/alertmanager`，升级版本不会丢失。


## 文件结构

```
roles/alertmanager/
├── defaults/main.yaml              # 默认变量
├── handlers/main.yaml              # daemon-reload / restart
├── meta/main.yaml                  # Galaxy 元数据
├── tasks/main.yaml                 # 安装任务流
├── templates/
│   ├── alertmanager.service.j2     # systemd 单元（含沙箱加固）
│   ├── alertmanager.yml.j2         # 主配置（默认空 receiver）
│   └── alertmanager.web.yml.j2     # Web TLS + BasicAuth 配置
└── README.md                       # 本文档

deploy-alertmanager.yaml            # 顶层 playbook
```


## 依赖

无外部依赖。仅要求目标主机为 Linux + systemd。


## 运行 playbook

```bash
# 必须带 -l/--limit 限定目标主机
ansible-playbook -l <host> deploy-alertmanager.yaml
```
