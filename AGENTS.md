# AGENTS.md

Ansible "lab": scratch playbooks/roles for experimenting with provisioning
(bootstrap, nginx, etcd, alertmanager, supervisor, confd, nvim). Not a
production role collection.

## Critical gotchas
- **Roles are tagged `never` by default.** In `playbook.yaml` every role has
  `tags: [..., never]`, so `ansible-playbook playbook.yaml` runs only
  un-tagged/`always` tasks. To actually run a role, pass `--tags <name>`
  (e.g. `--tags bootstrap`). `tags-test.yaml` demonstrates this behavior.
- **Short module names are intentional, not a bug.** `.ansible-lint` has
  `fqcn-builtins` in `skip_list`, so bare `debug:` / `copy:` are expected.
  Do not "fix" them to `ansible.builtin.*`.
- **`become` prompts for a password.** `ansible.cfg` sets `become_ask_pass=True`
  and `host_key_checking=False`. Privilege escalation will prompt during runs.
- **Vault password file is disabled.** `vault_password_file` is commented out in
  `ansible.cfg`; encrypted vars need `--vault-password-file`/prompt.

## Running
- Default inventory is `inventory/vagrant.ini` (`[defaults]` in `ansible.cfg`).
  Switch with `-i inventory/<name>.ini` (`local`, `macos`, `stage1`, `joytest`).
- `make vagrant ARGS="..."` ≡ `ansible-playbook -i ./inventory/vagrant.ini <ARGS> ./playbook.yml`.
- `make test` only echoes `ARGS` — it is NOT a real test runner.
- `roles_path=./roles` is set; roles (incl. namespaced `nmusatti.source_python`)
  resolve from there.
- Custom modules in `library/` (e.g. `custom_module`, `get_nofile`) are
  auto-loaded — no need to set a `library` path.

## Conventions
- Extensions are mixed (`.yaml` and `.yml`); keep whatever an existing file uses.
- Most playbooks end with a `vim:` modeline (`ft=yaml.ansible`); preserve it.
- Role READMEs (e.g. `roles/alertmanager/README.md`) document design decisions
  and security hardening — read before changing those roles.
- `roles/<name>/tests/test.yml` is the per-role smoke test with its own
  inventory; it targets `localhost`.
