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
- **task_catalog**: 7 files
- **handler_catalog**: 2 files
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


### Detailed_catalog

- True
### Task_catalog


| File | Task | Module | Parameters | Runbook |
| --- | --- | --- | --- | --- |
| `main.yml` | [Prepare demo service prerequisites](#task-main-yml-prepare-demo-service-prerequisites-1) | import_tasks |  | owner=platform impact=low |
| `prepare.yml` | [Ensure demo service group exists](#task-prepare-yml-ensure-demo-service-group-exists-2) | ansible.builtin.group | state=present | owner=platform step=prepare impact=low |
| `prepare.yml` | [Ensure demo service user exists](#task-prepare-yml-ensure-demo-service-user-exists-3) | ansible.builtin.user | group='{{ demo_service_name }}', system=true | - |
| `main.yml` | [Ensure demo config file is present](#task-main-yml-ensure-demo-config-file-is-present-4) | ansible.builtin.copy | content='service={{ demo_service_name }}    enabled={{ demo_service_enabled }}  ... | - |
| `main.yml` | [Deploy rendered configuration and validate settings](#task-main-yml-deploy-rendered-configuration-and-validate-settings-5) | import_tasks |  | - |
| `deploy.yml` | [Render demo service configuration](#task-deploy-yml-render-demo-service-configuration-6) | ansible.builtin.template | mode='0644' | - |
| `deploy.yml` | [Verify configured feature flags](#task-deploy-yml-verify-configured-feature-flags-7) | ansible.builtin.debug | msg='Enabled features: {{ demo_feature_flags | join('', '') }}' | - |


#### Task details and runbooks

<a id="task-main-yml-prepare-demo-service-prerequisites-1"></a>
**`main.yml` • Prepare demo service prerequisites**


<details>
<summary>Runbook</summary>

owner=platform impact=low

</details>

<a id="task-prepare-yml-ensure-demo-service-group-exists-2"></a>
**`prepare.yml` • Ensure demo service group exists**

- Parameters: `state=present`

<details>
<summary>Runbook</summary>

owner=platform step=prepare impact=low

</details>

<a id="task-main-yml-ensure-demo-config-file-is-present-4"></a>
**`main.yml` • Ensure demo config file is present**

- Parameters: `content='service={{ demo_service_name }}    enabled={{ demo_service_enabled }}    port={{ demo_service_port }}    ', mode='0644'`

- Note: This fixture exists only to exercise Prism scanners.

<a id="task-deploy-yml-render-demo-service-configuration-6"></a>
**`deploy.yml` • Render demo service configuration**

- Parameters: `mode='0644'`

- Warning: rollback=manual timeout=60s


### Handler_catalog

| File | Name | Module |
| --- | --- | --- |
| `main.yml` | Restart demo service | ansible.builtin.debug |
| `main.yml` | Reload demo service | ansible.builtin.debug |


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
