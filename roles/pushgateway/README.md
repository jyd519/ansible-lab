# pushgateway

从 GitHub Releases 下载 Prometheus Pushgateway 并以 **加固后的 systemd 服务**方式安装。
默认单机部署，支持通过变量覆盖下载地址、监听地址、持久化，并可选地启用 Web TLS + BasicAuth。

## 设计决策

### 安装方式：二进制下载

与 alertmanager / etcd 角色一致，选择从 GitHub Releases 直接下载二进制，而非 apt/yum：

- Pushgateway 官方不提供 deb/rpm 仓库，发行版自带的版本通常滞后
- 二进制下载可精确控制版本，跨发行版行为一致
- 下载前通过 `pushgateway --version` 做版本比对，实现幂等，避免重复下载

### 目录布局

| 路径 | 用途 | 属主 | 权限 | 说明 |
|---|---|---|---|---|
| `/usr/share/pushgateway/` | 二进制安装目录 | `root:root` | `0755` | 二进制只读，遵循 FHS |
| `/etc/pushgateway/` | 配置目录 | `root:pushgateway` | `0750` | root 可写，进程可读，其他用户不可访问 |
| `/etc/pushgateway/pushgateway.web.yml` | Web 安全配置(TLS/BasicAuth) | `root:pushgateway` | `0640` | 敏感文件 |
| `/var/lib/pushgateway/` | 数据目录(持久化指标) | `pushgateway:pushgateway` | `0700` | 仅进程可访问 |

二进制通过软链接到 `/usr/local/bin/`，使 `pushgateway` 在 PATH 中可用。

### 安全加固

**专用系统用户**：创建 `pushgateway` 用户/组（`system=true`, `shell=/usr/sbin/nologin`,
`create_home=false`），最小权限运行，不可登录。

**systemd 沙箱**：与 alertmanager 角色一致（`ProtectSystem=full`、`NoNewPrivileges=true`、
`PrivateTmp=true`、清空 capabilities、`RestrictAddressFamilies` 限制网络地址族等）。
仅当启用持久化时才放开数据目录的 `ReadWritePaths`。

**Web 传输安全（可选，推荐开启）**：通过 `--web.config.file` 启用 HTTPS 与
HTTP BasicAuth。证书路径与 BasicAuth 用户（bcrypt）由变量注入，配置文件权限 `0640`。
默认 `pushgateway_web_listen_address: "0.0.0.0:9091"` 对外监听，**一旦对外暴露务必开启 TLS+BasicAuth**，
否则 Pushgateway（及其中转的指标）将明文无鉴权暴露。

### 持久化

默认开启：通过 `--persistence.file` + `--persistence.interval` 将指标落地到
`/var/lib/pushgateway/pushgateway.data`，进程重启后指标不丢失。设为
`pushgateway_persistence_enabled: false` 可关闭（纯内存模式）。

### 架构自动检测

通过 `ansible_architecture` 自动映射到发布包架构名（`x86_64 -> amd64`, `aarch64 -> arm64`），
开箱支持 x86 与 ARM 服务器。

## 变量说明

```yaml
# 版本
pushgateway_version: "1.11.0"

# 目录
pushgateway_install_dir: /usr/share/pushgateway    # 二进制安装位置
pushgateway_data_dir: /var/lib/pushgateway         # 数据持久化目录
pushgateway_config_dir: /etc/pushgateway           # 配置文件目录

# 监听地址（默认对外）
pushgateway_web_listen_address: "0.0.0.0:9091"

# 持久化
pushgateway_persistence_enabled: true
pushgateway_persistence_file: "/var/lib/pushgateway/pushgateway.data"
pushgateway_persistence_interval: 5m

# Web TLS + BasicAuth（可选）
pushgateway_web_config_enabled: false
pushgateway_tls_cert_file: ""
pushgateway_tls_key_file: ""
pushgateway_basic_auth_users: []
```

## 运行

```bash
# 通过 deploy playbook（需指定 --limit 目标主机）
ansible-playbook -i inventory/<name>.ini deploy-pushgateway.yaml -l <host>

# 本地冒烟测试
ansible-playbook -i roles/pushgateway/tests/inventory roles/pushgateway/tests/test.yml
```

## 验证

```bash
curl -s http://<host>:9091/-/ready   # 应返回 "OK"
```
