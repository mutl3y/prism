# RUNBOOK: sample_role
---


## Contents

_No tasks found._


---

_No tasks were found in this role._

To add runbook comments, annotate tasks with `# prism~...` comments:

```yaml
# prism~runbook: restart service, verify with systemctl status
- name: Restart nginx
  ansible.builtin.service:
    name: nginx
    state: restarted
```
