supervisor
==========

Ansible role which helps to install and configure Supervisor.

The configuration of the role is done in such way that it should not be
necessary to change the role for any kind of configuration. All can be
done either by changing role parameters or by declaring completely new
configuration as a variable. That makes this role absolutely
universal. See the examples below for more details.

Please report any issues or send PR.


Examples
--------

```yaml
---

- name: Example of how to install Supervisor with default configuration
  hosts: all
  roles:
    - supervisor

- name: Example of how to add new programs
  hosts: all
  vars:
    supervisor_config__custom:
      program:my_prog1:
        command: /usr/bin/php /var/www/sites/my_prog1/app/console MyProg1 -q
        autostart: yes
        autorestart: yes
        startsecs: 1
        numprocs: 2
        priority: 1
        process_name: "%(process_num)s"
        user: www-data
        stderr_logfile: /tmp/my_prog1.err
        stdout_logfile: /tmp/my_prog1.out
      program:my_prog2:
        command: /usr/bin/php /var/www/sites/my_prog2/app/console MyProg2 -q
        autostart: yes
        autorestart: yes
        startsecs: 1
        numprocs: 6
        priority: 1
        process_name: "%(process_num)s"
        user: www-data
        stderr_logfile: /tmp/my_prog2.err
        stdout_logfile: /tmp/my_prog2.out
  roles:
    - supervisor

- name: Example of how to change and add more parameters
  hosts: all
  vars:
    # Change chmod of the socker file from 700 to 777
    supervisor_config_unix_http_server_chmod: "0777"
    # Add mode parameters into the supervisord section
    supervisor_config_supervisord__custom:
      user: chrism
      umask: "022"
  roles:
    - supervisor
```


Role variables
--------------

```yaml
# Package to install (explicit version can be specified here)
supervisor_pkg: supervisor

# Whether to install EPEL YUM repo
supervisor_epel_install: "{{ yumrepo_epel_install | default(true) }}"

# EPEL YUM repo URL
supervisor_epel_yumrepo_url: "{{ yumrepo_epel_url | default('https://dl.fedoraproject.org/pub/epel/$releasever/$basearch/') }}"

# EPEL YUM repo GPG key
supervisor_epel_yumrepo_gpgkey: "{{ yumrepo_epel_gpgkey | default('https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-$releasever') }}"

# Additional EPEL YUM repo params
supervisor_epel_yumrepo_params: "{{ yumrepo_epel_params | default({}) }}"

# Service name
supervisor_service: "{{
  'supervisord'
    if ansible_os_family == 'RedHat'
    else
  'supervisor' }}"

# Path to the config file
supervisor_config_file: "{{
  '/etc/supervisord.conf'
    if ansible_os_family == 'RedHat'
    else
  '/etc/supervisor/supervisord.conf' }}"


# Default values of the options of the unix_http_server section
supervisor_config_unix_http_server_file: "{{
  '/var/run/supervisor/supervisor.sock'
    if ansible_os_family == 'RedHat'
    else
  '/var/run/supervisor.sock' }}"
supervisor_config_unix_http_server_chmod: "0700"

# Default options of the unix_http_server section
supervisor_config_unix_http_server__default:
  file: "{{ supervisor_config_unix_http_server_file }}"
  chmod: "{{ supervisor_config_unix_http_server_chmod }}"

# Custom options of the unix_http_server section
supervisor_config_unix_http_server__custom: {}

# Final options of the unix_http_server section
supervisor_config_unix_http_server: "{{
    supervisor_config_unix_http_server__default.update(
    supervisor_config_unix_http_server__custom) }}{{
    supervisor_config_unix_http_server__default }}"


# Default values of the options of the supervisord section
supervisor_config_supervisord_logfile: /var/log/supervisor/supervisord.log
supervisor_config_supervisord_pidfile: /var/run/supervisord.pid
supervisor_config_supervisord_childlogdir: "{{
  '/tmp'
    if ansible_os_family == 'RedHat'
    else
  '/var/log/supervisor' }}"
supervisor_config_supervisord_logfile_maxbytes: 50MB
supervisor_config_supervisord_logfile_backups: 10
supervisor_config_supervisord_loglevel: info
supervisor_config_supervisord_nodaemon: no
supervisor_config_supervisord_minfds: 1024
supervisor_config_supervisord_minprocs: 200


# Default options of the supervisord section
supervisor_config_supervisord__default:
  logfile: "{{ supervisor_config_supervisord_logfile }}"
  pidfile: "{{ supervisor_config_supervisord_pidfile }}"
  childlogdir: "{{ supervisor_config_supervisord_childlogdir }}"
  logfile_maxbytes: "{{ supervisor_config_supervisord_logfile_maxbytes }}"
  logfile_backups: "{{ supervisor_config_supervisord_logfile_backups }}"
  loglevel: "{{ supervisor_config_supervisord_loglevel }}"
  nodaemon: "{{ supervisor_config_supervisord_nodaemon }}"
  minfds: "{{ supervisor_config_supervisord_minfds }}"
  minprocs: "{{ supervisor_config_supervisord_minprocs }}"

# Custom options of the supervisord section
supervisor_config_supervisord__custom: {}

# Final options of the supervisord section
supervisor_config_supervisord: "{{
    supervisor_config_supervisord__default.update(
    supervisor_config_supervisord__custom) }}{{
    supervisor_config_supervisord__default }}"


# Default values of the options of the rpcinterface:supervisor section
supervisor_config_rpcinterface_supervisor_supervisor_rpcinterface_factory: supervisor.rpcinterface:make_main_rpcinterface

# Default options of the rpcinterface:supervisor section
supervisor_config_rpcinterface_supervisor__default:
  supervisor.rpcinterface_factory: "{{ supervisor_config_rpcinterface_supervisor_supervisor_rpcinterface_factory }}"

# Custom options of the rpcinterface:supervisor section
supervisor_config_rpcinterface_supervisor__custom: {}

# Final options of the rpcinterface:supervisor section
supervisor_config_rpcinterface_supervisor: "{{
    supervisor_config_rpcinterface_supervisor__default.update(
    supervisor_config_rpcinterface_supervisor__custom) }}{{
    supervisor_config_rpcinterface_supervisor__default }}"


# Default values of the options of the supervisorctl section
supervisor_config_supervisorctl_serverurl: "{{
  'unix:///var/run/supervisor/supervisor.sock'
    if ansible_os_family == 'RedHat'
    else
  'unix:///var/run/supervisor.sock' }}"

# Default options of the supervisorctl section
supervisor_config_supervisorctl__default:
  serverurl: "{{ supervisor_config_supervisorctl_serverurl }}"

# Custom options of the supervisorctl section
supervisor_config_supervisorctl__custom: {}

# Final options of the supervisorctl section
supervisor_config_supervisorctl: "{{
    supervisor_config_supervisorctl__default.update(
    supervisor_config_supervisorctl__custom) }}{{
    supervisor_config_supervisorctl__default }}"


# Default values of the options of the include section
supervisor_config_include_files: "{{
  '/etc/supervisord.d/*.ini'
    if ansible_os_family == 'RedHat'
    else
  '/etc/supervisor/conf.d/*.conf' }}"

# Default options of the include section
supervisor_config_include__default:
  files: "{{ supervisor_config_include_files }}"

# Custom options of the include section
supervisor_config_include__custom: {}

# Final options of the include section
supervisor_config_include: "{{
    supervisor_config_include__default.update(
    supervisor_config_include__custom) }}{{
    supervisor_config_include__default }}"


# Default configuration
supervisor_config__default:
  unix_http_server: "{{ supervisor_config_unix_http_server }}"
  supervisord: "{{ supervisor_config_supervisord }}"
  rpcinterface:supervisor: "{{ supervisor_config_rpcinterface_supervisor }}"
  supervisorctl: "{{ supervisor_config_supervisorctl }}"
  include: "{{ supervisor_config_include }}"

# Custom configuration
supervisor_config__custom: {}

# Final configuration
supervisor_config: "{{
  supervisor_config__default.update(
  supervisor_config__custom) }}{{
  supervisor_config__default }}"
```


Dependencies
------------

- [`config_encoder_filters`](https://github.com/jtyr/ansible-config_encoder_filters)


License
-------

MIT


Author
------

Jiri Tyr
