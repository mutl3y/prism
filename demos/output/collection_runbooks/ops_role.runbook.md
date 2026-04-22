# RUNBOOK: ops_role
---


## Contents

- [Role Notes](#role-notes)
_No tasks found._

---

## Role Notes
<a id="role-notes"></a>

- **Note:** This role demonstrates a second collection role for aggregate docs.


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
