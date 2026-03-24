test-role
=========




Galaxy Info
-----------


No Galaxy metadata found.

Requirements
------------

No additional requirements.

Role purpose and capabilities
-----------------------------

The role `test-role` automates setup and configuration tasks with Ansible best-practice structure.

Capabilities:
- Provides reusable Ansible automation tasks

Role notes
----------

No role notes were found in comment annotations.

Inputs / variables summary
--------------------------

| Name | Type | Default | Source |
| --- | --- | --- | --- |
| `test_var` | str | `test_value` | defaults/main.yml |
| `test_var_2` | int | `123` | defaults/main.yml |
| `test_var_3` | documented | `<documented in README>` | README.md (documented input) |


Variable provenance and confidence notes:

Unresolved variables:
- `test_var_3`: Documented in README; static role definition not found.


Task/module usage summary
-------------------------

- **Task files scanned**: 1
- **Tasks scanned**: 1
- **Recursive includes**: 0
- **Unique modules**: 1
- **Handlers referenced**: 0

Inferred example usage
----------------------

```yaml
- hosts: all
  roles:
    - role: test-role
      vars:
        test_var: test_value
        test_var_2: 123
        test_var_3: <documented in README>
```

Role Variables
--------------

The following variables are available:
- `test_var`: test_value
- `test_var_2`: 123

Role contents summary
---------------------

The scanner collected these role subdirectories (counts):

- **handlers**: 0 files
- **tasks**: 1 files
- **templates**: 0 files
- **files**: 0 files
- **tests**: 0 files
- **defaults**: 1 files
- **vars**: 0 files
- **molecule_scenarios**: 0 files
- **unconstrained_dynamic_task_includes**: 0 files
- **unconstrained_dynamic_role_includes**: 0 files
- **collection_compliance_notes**: 0 files
- **yaml_parse_failures**: 0 files

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



Auto-detected role features
---------------------------

- **task_files_scanned**: 1
- **tasks_scanned**: 1
- **recursive_task_includes**: 0
- **unique_modules**: debug
- **external_collections**: none
- **handlers_notified**: none
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
