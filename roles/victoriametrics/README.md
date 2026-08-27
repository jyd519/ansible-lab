# victoriametrics

从 GitHub Releases 下载 **单机版 VictoriaMetrics**（`victoria-metrics-prod`）并以 **加固后的 systemd 服务**方式安装。
默认单机运行，可选安装 `vmutils` 工具（`vmbackup-prod` / `vmrestore-prod`）并配置 **数据备份定时任务**（默认关闭）。

## 设计决策

### 安装方式：二进制下载（单机版）

与 pushgateway / alertmanager 角色一致，选择从 GitHub Releases 直接下载二进制，而非 apt/yum：

- 单机版 VictoriaMetrics 官方不提供 deb/rpm 仓库，发行版自带的版本通常滞后
- 二进制下载可精确控制版本，跨发行版行为一致
- 下载前通过 `victoria-metrics-prod --version` 做版本比对，实现幂等，避免重复下载

单机版只包含一个二进制 `victoria-metrics-prod`，集成了存储、写入、查询、UI、Prometheus 远程读写等全部能力，
适合中小规模与实验室场景。集群版（vmselect/vminsert/vmstorage）不在本角色范围内。

### 目录布局

| 路径 | 用途 | 属主 | 权限 | 说明 |
|---|---|---|---|---|
| `/usr/share/victoriametrics/` | 二进制安装目录 | `root:root` | `0755` | 二进制只读，遵循 FHS |
| `/etc/victoriametrics/` | 配置目录 | `root:victoriametrics` | `0750` | root 可写，进程可读，其他用户不可访问 |
| `/var/lib/victoriametrics/` | 数据目录(时序数据) | `victoriametrics:victoriametrics` | `0700` | 仅进程可访问 |
| `/var/backups/victoriametrics/` | 本地备份目录（fs:// 时） | `victoriametrics:victoriametrics` | `0700` | 仅备份进程可访问 |

二进制通过软链接到 `/usr/local/bin/`，使 `victoria-metrics-prod`、`vmbackup-prod`、`vmrestore-prod` 在 PATH 中可用。

### 安全加固

**专用系统用户**：创建 `victoriametrics` 用户/组（`system=true`, `shell=/usr/sbin/nologin`,
`create_home=false`），最小权限运行，不可登录。

**systemd 沙箱**：与 pushgateway / alertmanager 角色一致（`ProtectSystem=full`、`NoNewPrivileges=true`、
`PrivateTmp=true`、清空 capabilities、`RestrictAddressFamilies` 限制网络地址族等），
仅放开数据目录的 `ReadWritePaths`。

**监听地址**：默认 `0.0.0.0:8428` 对外监听。VictoriaMetrics 默认无鉴权、无 TLS，
**一旦对外暴露请前置反向代理（如 nginx+victoriametrics 的 web 配置）开启鉴权与加密**，
否则指标接口将明文无鉴权暴露。

### 数据保留与自抓取

- 通过 `-retentionPeriod` 控制数据保留期（单位：月，默认 `4`）。
- `-selfScrapeInterval` 默认 `0`（关闭自抓取），避免把 VictoriaMetrics 自身指标写回自己造成循环写入。

### 备份与恢复（vmutils，默认关闭）

备份工具 `vmbackup-prod` 来自 `vmutils` 包。它通过 **快照** 机制做增量/全量备份，**无需停止 VictoriaMetrics 服务**：

- `-storageDataPath`：必须与 VictoriaMetrics 的 `-storageDataPath` 一致
- `-snapshot.createURL=http://localhost:8428/snapshot/create`：vmbackup 自动创建快照，备份完成后自动删除
- `-dst`：备份目标，支持多种后端
  - 本地文件系统：`fs:///var/backups/victoriametrics`
  - S3 / 兼容存储：`s3://<bucket>/<path>`（可用 `-customS3Endpoint` 指向 MinIO 等）
  - GCS：`gs://<bucket>/<path>`
  - Azure Blob：`azblob://<container>/<path>`

注意：`vmbackup` 禁止把备份写到 `storageDataPath` 所在目录；本地备份目录必须独立。

恢复使用 `vmrestore-prod`（同属 vmutils，本角色默认一并安装）：

```bash
vmrestore-prod -src=fs:///var/backups/victoriametrics -storageDataPath=/var/lib/victoriametrics
```

备份定时任务由 `victoriametrics_backup_enabled: false` 控制（默认关闭）；
开启后会渲染 `/usr/local/bin/victoriametrics-backup.sh` 并注册 cron（默认每天 02:00，以 `victoriametrics` 用户运行）。

### 架构自动检测

通过 `ansible_architecture` 自动映射到发布包架构名（`x86_64 -> amd64`, `aarch64 -> arm64`），
开箱支持 x86 与 ARM 服务器。

## 变量说明

```yaml
# 版本
victoriametrics_version: "1.150.0"

# 目录
victoriametrics_install_dir: /usr/share/victoriametrics   # 二进制安装位置
victoriametrics_data_dir: /var/lib/victoriametrics        # 数据存储目录
victoriametrics_config_dir: /etc/victoriametrics          # 配置文件目录

# 监听地址（默认对外）
victoriametrics_http_listen_address: "0.0.0.0:8428"

# 数据保留期（月）与存储路径
victoriametrics_retention_period: "4"
victoriametrics_storage_data_path: "{{ victoriametrics_data_dir }}"
victoriametrics_self_scrape_interval: "0"                # 0 关闭自抓取

# vmutils 工具（vmbackup-prod / vmrestore-prod）
victoriametrics_install_vmutils: true

# 备份定时任务（默认关闭）
victoriametrics_backup_enabled: false
victoriametrics_backup_dst: "fs:///var/backups/victoriametrics"
victoriametrics_backup_snapshot_create_url: "http://localhost:8428/snapshot/create"
victoriametrics_backup_minute: "0"
victoriametrics_backup_hour: "2"
victoriametrics_backup_day: "*"
victoriametrics_backup_month: "*"
victoriametrics_backup_weekday: "*"
```

## 运行

```bash
# 通过 deploy playbook（需指定 --limit 目标主机）
ansible-playbook -i inventory/<name>.ini deploy-victoriametrics.yaml -l <host>

# 本地冒烟测试
ansible-playbook -i roles/victoriametrics/tests/inventory roles/victoriametrics/tests/test.yml
```

## 验证

```bash
curl -s http://<host>:8428/-/ready    # 应返回 "OK"
curl -s http://<host>:8428/-/health   # 健康检查
curl -s http://<host>:8428            # 打开 Web UI
```

## 备份验证

```bash
# 手动触发一次备份（本地 fs）
/usr/local/bin/victoriametrics-backup.sh

# 查看日志
tail -f /var/log/victoriametrics-backup.log

# 恢复示例
vmrestore-prod -src=fs:///var/backups/victoriametrics -storageDataPath=/var/lib/victoriametrics
```
