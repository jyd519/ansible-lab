# Ansible Role: confd

Install and configure [confd](https://github.com/kelseyhightower/confd) as a systemd service.

> **Note**: confd's latest release is v0.16.0 (2018-05). The project is stable but no longer actively maintained. Evaluate alternatives (e.g., consul-template) if you need active upstream support.

## How It Works

1. Creates a dedicated `confd` system user/group (nologin, no home) to avoid running as root
2. Downloads the confd binary from GitHub releases (version and URL are configurable)
3. Deploys the main config (`/etc/confd/confd.toml`) pointing to a backend (etcd by default)
4. Copies user-supplied template resources (`conf.d/`) and templates (`templates/`) to the target
5. Manages confd as a systemd service with security hardening (ProtectSystem, NoNewPrivileges, etc.)

## Requirements

- Ansible >= 2.10
- A running backend (etcd, consul, etc.) that confd can connect to
- Target: Linux with systemd (Debian/Ubuntu, RHEL/CentOS 8+)

## Role Variables

### Core

| Variable | Default | Description |
|---|---|---|
| `confd_version` | `0.16.0` | Version to install |
| `confd_download_url` | GitHub releases URL | Override to use a mirror or local file server |
| `confd_install_dir` | `/usr/share/confd` | Binary install directory |
| `confd_config_dir` | `/etc/confd` | Root config directory |
| `confd_user` / `confd_group` | `confd` | Dedicated service user |

### Backend

| Variable | Default | Description |
|---|---|---|
| `confd_backend` | `etcd` | Backend type: etcd, consul, env, file, redis, vault, dynamodb, zookeeper |
| `confd_backend_nodes` | `["http://127.0.0.1:2379"]` | List of backend endpoint URLs |
| `confd_scheme` | `http` | Connection scheme |
| `confd_prefix` | `/` | Key prefix in backend |
| `confd_watch` | `true` | Use watch mode (long-poll). Set `false` for interval polling |
| `confd_interval` | `300` | Polling interval in seconds (when watch is false) |
| `confd_log_level` | `info` | Log level: debug, info, warn, error |

### Authentication (optional)

| Variable | Default | Description |
|---|---|---|
| `confd_auth_token` | `""` | Bearer token for backend auth |
| `confd_basic_auth` | `false` | Enable basic auth |
| `confd_username` / `confd_password` | `""` | Basic auth credentials |
| `confd_client_cert` / `confd_client_key` | `""` | TLS client certificate paths |
| `confd_client_ca_keys` | `""` | CA certificate path |

### Systemd Sandbox & Filesystem ACL

| Variable | Default | Description |
|---|---|---|
| `confd_extra_readwrite_paths` | `[]` | Extra paths confd is allowed to write (added to systemd `ReadWritePaths=`) |
| `confd_acl_write_dirs` | `[]` | Directories to grant confd write access via POSIX ACL (requires `acl` package on target) |

### Template Deployment

| Variable | Default | Description |
|---|---|---|
| `confd_template_resources` | `[]` | List of `{name, src}` for TOML resource files → `conf.d/` |
| `confd_templates` | `[]` | List of `{name, src}` for Go template files → `templates/` |

## Usage Example

### 1. Prepare template resource and template files

Template resource (`files/confd/conf.d/myapp.toml`):

```toml
[template]
src = "myapp.conf.tmpl"
dest = "/etc/myapp/myapp.conf"
keys = ["/myapp/database/host", "/myapp/database/port"]
reload_cmd = "systemctl reload myapp"
```

Go template (`files/confd/templates/myapp.conf.tmpl`):

```
# Managed by confd
database_host = {{getv "/myapp/database/host"}}
database_port = {{getv "/myapp/database/port"}}
```

### 2. Playbook

```yaml
- name: Install confd
  hosts: app_servers
  become: yes
  roles:
    - role: confd
      confd_backend: etcd
      confd_backend_nodes:
        - "http://etcd1:2379"
        - "http://etcd2:2379"
      confd_extra_readwrite_paths:
        - /etc/myapp
      confd_acl_write_dirs:
        - /etc/myapp
      confd_template_resources:
        - name: myapp.toml
          src: files/confd/conf.d/myapp.toml
      confd_templates:
        - name: myapp.conf.tmpl
          src: files/confd/templates/myapp.conf.tmpl
```

### 3. Run

```bash
ansible-playbook deploy-confd.yaml -l app_servers
```

## Design Decisions

- **Dedicated system user**: confd runs as a non-root user with `nologin` shell — principle of least privilege.
- **Idempotent install**: Version check before download — skips download if the target version is already installed.
- **Systemd hardening**: `ProtectSystem=full`, `ProtectHome=true`, `NoNewPrivileges=true`, `PrivateTmp=true`.
- **Watch vs interval**: Defaults to `watch=true` for near-real-time updates. Switch to interval mode for backends that don't support watch.
- **Separate resource/template deployment**: `confd_template_resources` and `confd_templates` use `copy` (not `template`) so that Go template syntax (`{{getv ...}}`) is preserved without Jinja2 conflicts.
- **confd generates target files with its own user** — if the target config file (e.g., `/etc/myapp/myapp.conf`) needs different ownership, use `uid`/`gid` in the template resource TOML, or adjust the `confd_user` to have appropriate group memberships.

## Target Directory Write Permissions

confd 以 `confd` 用户运行，生成的配置文件写入目标目录（如 `/etc/nginx`）需要同时满足两层权限：

1. **Systemd 沙箱层**：`ProtectSystem=full` 将 `/etc` 设为只读，需通过 `confd_extra_readwrite_paths` 放行
2. **文件系统层**：confd 用户需要对目标目录有写权限（rwx）

仅设置 `confd_extra_readwrite_paths` 是不够的，还需选择以下方案之一解决文件系统权限：

### 方案 A：将 confd 加入目标服务的 group

适用于目标目录已有 group 写权限的场景（如 `/etc/nginx` 属于 `www-data`）。
在 playbook 中覆盖用户创建步骤或使用 `pre_tasks`：

```yaml
- name: Add confd to www-data group
  ansible.builtin.user:
    name: confd
    groups: ["www-data"]
    append: true
```

需确保目标目录有 group 写权限（`g+w`）。

### 方案 B：通过 ACL 精确授权

不改变目录 owner/group，影响范围最小：

```yaml
- name: Grant confd write access to /etc/nginx/conf.d
  ansible.posix.acl:
    path: /etc/nginx/conf.d
    entity: confd
    etype: user
    permissions: rwx
    state: present

- name: Set default ACL for new files
  ansible.posix.acl:
    path: /etc/nginx/conf.d
    entity: confd
    etype: user
    permissions: rw
    default: true
    state: present
```

### 方案 C：让 confd 输出到自己的目录

完全不碰目标服务的目录权限，隔离最干净：

```
# confd 输出到 /etc/confd/output/nginx.conf
# nginx 配置中 include /etc/confd/output/nginx.conf;
```

此方案无需设置 `confd_extra_readwrite_paths`，因为 `/etc/confd/` 已属于 confd 用户。

## File Layout on Target

```
/usr/share/confd/confd          # binary
/usr/local/bin/confd            # symlink
/etc/confd/
├── confd.toml                  # main config
├── conf.d/                     # template resources (TOML)
│   └── myapp.toml
└── templates/                  # Go templates
    └── myapp.conf.tmpl
```

## License

MIT
