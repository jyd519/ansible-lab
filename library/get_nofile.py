#!/usr/bin/python

# https://docs.ansible.com/ansible/2.10/dev_guide/developing_modules_best_practices.html#creating-correct-and-informative-module-output

import functools
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: get_nofile.py
short_description: Check remote process' nofile limit
description:
  - Get process' nofile limits
options:
  name:
    description:
      - name of the process you want to inspect nofile limit
  json:
    description:
        - True: return limit info as dict
        - False: return limit info as lines
"""


def main():
    # Define options accepted by the module. ❶
    module_args = dict(
        name=dict(type='str', required=True),
        json=dict(type='bool', required=False, default=False),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False,
        limits=[]
    )

    name = module.params["name"]
    rc, out, err = module.run_command("pgrep " + name, use_unsafe_shell=True)
    if rc != 0:
        result['err'] = f"Process [{name}] is not running"
        result['rc'] = rc

    limits = []
    max_len = functools.reduce(lambda p, c: len(
        c) if len(c) > p else p, out.split('\n'), 0)
    for pid in out.split('\n'):
        if pid:
            rc, out, err = module.run_command(
                f"""prlimit -n -p {pid} | awk 'NR==2{{printf "%s soft: %s hard: %s", $1, $7, $8}}'""", use_unsafe_shell=True)
            if err:
                result['err'] = err.strip()
                result['rc'] = rc or 1
                break
            if module.params['json']:
                tokens = out.split(' ')
                limits.append(
                    {"pid": pid, "soft": tokens[1], "hard": tokens[2]})
            else:
                limits.append(f"{pid:{max_len}} " + out.strip())

    result['limits'] = limits

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
