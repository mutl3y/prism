ops_role
=========

Operations-oriented role fixture for collection demos


Galaxy Info
-----------


- **Role name**: ops_role
- **Description**: Operations-oriented role fixture for collection demos
- **License**: MIT
- **Min Ansible Version**: 2.14

Requirements
------------

No additional requirements.

Role purpose and capabilities
-----------------------------

Operations-oriented role fixture for collection demos

Capabilities:
- Deploy configuration or content files
- Triggers role handlers based on task changes

Role notes
----------


Notes:
- This role demonstrates a second collection role for aggregate docs.

Inputs / variables summary
--------------------------

| Name | Type | Default | Source |
| --- | --- | --- | --- |
| `ops_role_retries` | int | `3` | defaults/main.yml |
| `ops_role_state_path` | str | `/tmp/prism-ops-role.state` | defaults/main.yml |


Task/module usage summary
-------------------------

- **Task files scanned**: 1
- **Tasks scanned**: 2
- **Recursive includes**: 0
- **Unique modules**: 2
- **Handlers referenced**: 1

Inferred example usage
----------------------

```yaml
- hosts: all
  roles:
    - role: ops_role
      vars:
        ops_role_retries: 3
        ops_role_state_path: /tmp/prism-ops-role.state
```

Role Variables
--------------

The following variables are available:
- `ops_role_state_path`: /tmp/prism-ops-role.state
- `ops_role_retries`: 3

Role contents summary
---------------------

The scanner collected these role subdirectories (counts):

- **handlers**: 1 files
- **tasks**: 1 files
- **templates**: 0 files
- **files**: 0 files
- **tests**: 0 files
- **defaults**: 1 files
- **vars**: 0 files
- **molecule_scenarios**: 0 files
- **unconstrained_dynamic_task_includes**: 0 files
- **unconstrained_dynamic_role_includes**: 0 files
- **task_catalog**: 2 files
- **handler_catalog**: 1 files
- **collection_compliance_notes**: 0 files
- **non_authoritative_test_evidence_limits**: 3 files
- **yaml_parse_failures**: 0 files

### Handlers

- handlers/main.yml


### Tasks

- tasks/main.yml


### Defaults

- defaults/main.yml


### Marker_prefix

- p
- r
- i
- s
- m


### Detailed_catalog

- True
### Task_catalog


| File | Task | Module | Parameters | Runbook |
| --- | --- | --- | --- | --- |
| `main.yml` | [Persist ops state marker](#task-main-yml-persist-ops-state-marker-1) | ansible.builtin.copy | content=retries={{ ops_role_retries }}, mode='0644' | owner=ops impact=medium |
| `main.yml` | [Report ops retry configuration](#task-main-yml-report-ops-retry-configuration-2) | ansible.builtin.debug | msg=ops_role retries set to {{ ops_role_retries }} | - |


#### Task details and runbooks

<a id="task-main-yml-persist-ops-state-marker-1"></a>
**`main.yml` • Persist ops state marker**

- Parameters: `content=retries={{ ops_role_retries }}, mode='0644'`

<details>
<summary>Runbook</summary>

owner=ops impact=medium

</details>
- Note: This role demonstrates a second collection role for aggregate docs.


### Handler_catalog

| File | Name | Module |
| --- | --- | --- |
| `main.yml` | Emit ops role refresh notice | ansible.builtin.debug |

### Ignore_unresolved_internal_underscore_references

- True
### Non_authoritative_test_evidence_limits

- max_file_bytes
- max_files_scanned
- max_total_bytes



Auto-detected role features
---------------------------

- **task_files_scanned**: 1
- **tasks_scanned**: 2
- **recursive_task_includes**: 0
- **unique_modules**: ansible.builtin.copy, ansible.builtin.debug
- **external_collections**: none
- **handlers_notified**: Emit ops role refresh notice
- **privileged_tasks**: 0
- **conditional_tasks**: 0
- **tagged_tasks**: 0
- **included_role_calls**: 0
- **included_roles**: none
- **dynamic_included_role_calls**: 0
- **dynamic_included_roles**: none
- **disabled_task_annotations**: 0
- **yaml_like_task_annotations**: 0

Comparison against local baseline role
-------------------------------------

No comparison baseline provided.

Detected usages of the default() filter
---------------------------------------

No undocumented variables using `default()` were detected.
