# etcd

从 GitHub Releases 下载 etcd 稳定版并以 systemd 服务方式安装。

## 设计决策

### 安装方式：二进制下载 vs 包管理器

选择从 GitHub Releases 直接下载二进制，而非 apt/yum：

- etcd 官方不提供 deb/rpm 仓库，发行版自带的版本通常滞后严重
- 二进制下载可精确控制版本，跨发行版行为一致
- 下载后通过版本检查实现幂等，避免重复下载

### 目录布局

| 路径 | 用途 | 属主 | 权限 | 说明 |
|---|---|---|---|---|
| `/usr/share/etcd/` | 二进制安装目录 | `root:root` | `0755` | 遵循 FHS，非系统管理程序放 `/usr/share`；二进制只读 |
| `/etc/etcd/` | 配置目录 | `root:etcd` | `0750` | root 可写，etcd 进程可读，其他用户不可访问 |
| `/etc/etcd/etcd.conf.yaml` | 配置文件 | `root:etcd` | `0640` | 配置中可能包含敏感信息（如证书路径），禁止 world-read |
| `/var/etcd/` | 数据目录 | `etcd:etcd` | `0700` | 仅 etcd 进程可访问，防止数据泄露 |

二进制文件通过软链接到 `/usr/local/bin/`，使 `etcd` 和 `etcdctl` 在 PATH 中可用。

### 安全加固

**专用系统用户**：创建 `etcd` 用户/组（`system=true`, `shell=/usr/sbin/nologin`, `create_home=false`），
最小权限运行，不可被登录。

**systemd 沙箱**：

| 指令 | 作用 |
|---|---|
| `ProtectSystem=full` | `/usr`, `/boot`, `/etc` 只读挂载 |
| `ProtectHome=true` | `/home`, `/root`, `/run/user` 不可访问 |
| `NoNewPrivileges=true` | 禁止通过 execve 提升权限 |
| `PrivateTmp=true` | 隔离 `/tmp` 命名空间 |
| `ReadWritePaths=/var/etcd` | 仅允许写入数据目录 |
| `LimitNOFILE=65536` | etcd 需要大量文件描述符 |

### 幂等性

- 通过 `etcd --version` 检查已安装版本，版本一致时跳过下载/安装
- 下载的临时文件安装完成后自动清理
- 配置/服务文件变更时通过 handler 触发 `daemon-reload` + `restart`

### 配置格式

使用 etcd 原生 YAML 配置文件（`--config-file`），而非环境变量或命令行参数：

- YAML 格式更易读、易维护
- Ansible template 渲染 YAML 比拼接环境变量更安全
- 便于后续扩展 TLS、认证等高级配置

### 架构自动检测

通过 `ansible_architecture` 自动映射到 etcd 发布包的架构名：

```yaml
etcd_arch_map:
  x86_64: amd64
  aarch64: arm64
```

无需手动指定，开箱支持 x86 和 ARM 服务器。


## 变量说明

```yaml
# etcd 版本
etcd_version: "3.5.21"

# 目录
etcd_install_dir: /usr/share/etcd    # 二进制安装位置
etcd_data_dir: /var/etcd             # 数据持久化目录
etcd_config_dir: /etc/etcd           # 配置文件目录

# 运行用户
etcd_user: etcd
etcd_group: etcd

# 监听地址（单节点默认值，仅监听 loopback）
etcd_listen_client_urls: "http://127.0.0.1:2379"
etcd_advertise_client_urls: "http://127.0.0.1:2379"
etcd_listen_peer_urls: "http://127.0.0.1:2380"
etcd_initial_advertise_peer_urls: "http://127.0.0.1:2380"

# 集群配置
etcd_name: "{{ inventory_hostname }}"
etcd_initial_cluster: "{{ etcd_name }}=http://127.0.0.1:2380"
etcd_initial_cluster_state: new
etcd_initial_cluster_token: etcd-cluster

# 存储调优
etcd_auto_compaction_retention: "1"       # 自动压缩保留 1 小时
etcd_quota_backend_bytes: 8589934592      # 后端存储配额 8GB
```


## 使用示例

### 单节点（默认）

```yaml
- name: Install etcd
  hosts: all
  become: yes
  roles:
    - etcd
```

### 指定版本

```yaml
- name: Install etcd 3.5.17
  hosts: all
  become: yes
  roles:
    - role: etcd
      etcd_version: "3.5.17"
```

### 对外暴露客户端端口

```yaml
- name: Install etcd with external access
  hosts: all
  become: yes
  roles:
    - role: etcd
      etcd_listen_client_urls: "http://0.0.0.0:2379"
      etcd_advertise_client_urls: "http://{{ ansible_default_ipv4.address }}:2379"
```

### 三节点集群

```yaml
- name: Install etcd cluster
  hosts: etcd_nodes
  become: yes
  roles:
    - role: etcd
      etcd_listen_client_urls: "http://0.0.0.0:2379"
      etcd_advertise_client_urls: "http://{{ ansible_default_ipv4.address }}:2379"
      etcd_listen_peer_urls: "http://0.0.0.0:2380"
      etcd_initial_advertise_peer_urls: "http://{{ ansible_default_ipv4.address }}:2380"
      etcd_initial_cluster: >-
        node1=http://10.0.0.1:2380,
        node2=http://10.0.0.2:2380,
        node3=http://10.0.0.3:2380
```


## 安装后验证

```bash
# 检查服务状态
systemctl status etcd

# 检查集群健康
etcdctl endpoint health

# 查看成员列表
etcdctl member list

# 写入/读取测试
etcdctl put /test/key "hello"
etcdctl get /test/key
```


## 文件结构

```
roles/etcd/
├── defaults/main.yaml          # 默认变量
├── handlers/main.yaml          # daemon-reload / restart
├── meta/main.yaml              # Galaxy 元数据
├── tasks/main.yaml             # 安装任务流
├── templates/
│   ├── etcd.conf.yaml.j2       # etcd YAML 配置
│   └── etcd.service.j2         # systemd 单元文件
└── README.md                   # 本文档
```


## 依赖

无外部依赖。仅要求目标主机为 Linux + systemd。
