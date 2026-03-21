role_demo
=========

Minimal role fixture for Prism demos


Galaxy Info
-----------


- **Role name**: role_demo
- **Description**: Minimal role fixture for Prism demos
- **License**: MIT
- **Min Ansible Version**: 2.14

Requirements
------------

No additional requirements.

Role purpose and capabilities
-----------------------------

Minimal role fixture for Prism demos

Capabilities:
- Deploy configuration or content files
- Manage users and groups
- Uses nested task includes for modular orchestration
- Triggers role handlers based on task changes

Role notes
----------

Warnings:
- rollback=manual timeout=60s

Notes:
- This fixture exists only to exercise Prism scanners.

Inputs / variables summary
--------------------------

| Name | Type | Default | Source |
| --- | --- | --- | --- |
| `demo_allowed_networks` | list | `[10.0.0.0/24, 192.168.10.0/24]` | defaults/main.yml |
| `demo_feature_flags` | list | `[docs, reporting]` | defaults/main.yml |
| `demo_service_enabled` | bool | `true` | defaults/main.yml |
| `demo_service_log_level` | str | `info` | defaults/main.yml |
| `demo_service_name` | str | `prism-demo` | defaults/main.yml |
| `demo_service_port` | int | `8080` | defaults/main.yml |


Task/module usage summary
-------------------------

- **Task files scanned**: 3
- **Tasks scanned**: 7
- **Recursive includes**: 2
- **Unique modules**: 6
- **Handlers referenced**: 1

Inferred example usage
----------------------

```yaml
- hosts: all
  roles:
    - role: role_demo
      vars:
        demo_allowed_networks: [10.0.0.0/24, 192.168.10.0/24]
        demo_feature_flags: [docs, reporting]
        demo_service_enabled: true
```

Role Variables
--------------

The following variables are available:
- `demo_service_name`: prism-demo
- `demo_service_enabled`: True
- `demo_service_port`: 8080
- `demo_service_log_level`: info
- `demo_feature_flags`: ['docs', 'reporting']
- `demo_allowed_networks`: ['10.0.0.0/24', '192.168.10.0/24']

Role contents summary
---------------------

The scanner collected these role subdirectories (counts):

- **handlers**: 1 files
- **tasks**: 3 files
- **templates**: 1 files
- **files**: 0 files
- **tests**: 0 files
- **defaults**: 1 files
- **vars**: 0 files
- **molecule_scenarios**: 0 files
- **unconstrained_dynamic_task_includes**: 0 files
- **unconstrained_dynamic_role_includes**: 0 files
- **collection_compliance_notes**: 0 files
- **yaml_parse_failures**: 0 files

### Handlers

- handlers/main.yml


### Tasks

- tasks/deploy.yml
- tasks/main.yml
- tasks/prepare.yml


### Templates

- templates/demo-service.conf.j2


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

- **task_files_scanned**: 3
- **tasks_scanned**: 7
- **recursive_task_includes**: 2
- **unique_modules**: ansible.builtin.copy, ansible.builtin.debug, ansible.builtin.group, ansible.builtin.template, ansible.builtin.user, import_tasks
- **external_collections**: none
- **handlers_notified**: Restart demo service
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
