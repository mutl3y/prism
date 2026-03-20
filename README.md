# Prism

> **Refract complexity into clarity.**

An Ansible role isn't a single file; it's a complex system of interconnected parts. Its defaults, variables, tasks, and metadata combine to create powerful automation, but this interconnectedness can make it opaque and difficult for others (and even your future self) to understand at a glance. Manually documenting this is tedious, error-prone, and rarely kept up-to-date.

**Prism** treats your Ansible automation like a beam of light.

It passes your entire role or collection through its analytical engine, refracting the tangled, monolithic code into a **full spectrum** of its constituent parts. It doesn't just list files; it intelligently parses them to reveal the relationships and logic hidden within.

The result is a single, beautiful, and maintainable README that is always in sync with your code.

### The Spectrum of Documentation

*   **A Clear Palette of Variables:** Defaults, group variables, and role variables are separated and presented with their types, comments, and context, so you never have to guess a variable's purpose or precedence.
*   **The Bright Lines of Tasks:** Every task is rendered clearly, showing its name, module, and parameters, turning a wall of YAML into a readable sequence of actions.
*   **The Deep Hues of Metadata:** Platform support, Galaxy info, and role dependencies are brought to the forefront, defining the role's precise operational boundaries.
*   **A Coherent Structure:** By analyzing every component, Prism builds a document that is not just a concatenation of files, but a holistic and accurate representation of your entire automation.

Stop wrestling with convoluted code and out-of-date documentation. **Let Prism illuminate your automation.**

---

## Test Fixture: mock_role

mock_role
=========

Enhanced mock Ansible role for production-like documentation tests.

This fixture includes setup/deploy/validate/rollback task paths,
realistic defaults and vars, and richer metadata used by scanner heuristics.


Galaxy Info
-----------


- **Role name**: mock_role
- **Description**: Enhanced mock Ansible role for production-like documentation tests.

This fixture includes setup/deploy/validate/rollback task paths,
realistic defaults and vars, and richer metadata used by scanner heuristics.
- **License**: MIT
- **Min Ansible Version**: 2.14
- **Tags**: mock, fixture, nginx, validation
Requirements
------------

- example.role_dependency (version: 1.0.0)
- example.collection_dependency (version: main)
- community.general

Role purpose and capabilities
-----------------------------

Enhanced mock Ansible role for production-like documentation tests.

This fixture includes setup/deploy/validate/rollback task paths,
realistic defaults and vars, and richer metadata used by scanner heuristics.

Capabilities:
- Deploy configuration or content files
- Install and manage packages
- Uses nested task includes for modular orchestration
- Triggers role handlers based on task changes

Role notes
----------

Warnings:
- this package is unhealthy

Additionals:
- ensure rollback playbooks are reviewed before production use

Inputs / variables summary
--------------------------

| Name | Type | Default | Source |
| --- | --- | --- | --- |
| `mock_role_api` | dict | `{endpoint: '{{ required_endpoint | default(''https://api.example.internal/v1'') }}',   timeout_seconds: 30, retries: 2}` | defaults/main.yml |
| `mock_role_config_path` | str | `/etc/mock-role/app.conf` | defaults/main.yml |
| `mock_role_env` | dict | `{APP_MODE: production, APP_LOG_LEVEL: info}` | defaults/main.yml |
| `mock_role_feature_flags` | dict | `{healthcheck: true, metrics: true, legacy_mode: false}` | defaults/main.yml |
| `mock_role_install_enabled` | bool | `true` | defaults/main.yml |
| `mock_role_packages` | list | `[nginx, curl]` | defaults/main.yml |
| `mock_role_rollback_enabled` | bool | `false` | defaults/main.yml |
| `mock_role_service_name` | str | `mock-role` | defaults/main.yml |
| `mock_role_state` | str | `present` | defaults/main.yml |
| `mock_role_template_group` | str | `root` | defaults/main.yml |
| `mock_role_template_mode` | str | `'0644'` | defaults/main.yml |
| `mock_role_template_owner` | str | `root` | defaults/main.yml |
| `mock_role_validate_config` | bool | `true` | defaults/main.yml |
| `role_install_enabled` | str | `'{{ mock_role_install_enabled }}'` | defaults/main.yml |
| `role_package_name` | str | `'{{ mock_role_packages | first | default(''nginx'') }}'` | defaults/main.yml |
| `role_service_name` | str | `'{{ mock_role_service_name }}'` | defaults/main.yml |
| `variable1` | str | `'{{ default(''Default value 1'', omit) }}'` | defaults/main.yml |
| `variable2` | str | `Default value 2` | defaults/main.yml |
| `nested_enabled` | computed | `—` | tasks (set_fact) |
| `deep_var` | required | `<required>` | inferred usage |
| `mock_role_configure_ini` | required | `<required>` | inferred usage |
| `mock_role_debug` | required | `<required>` | inferred usage |
| `mock_role_use_undeclared_collection` | required | `<required>` | inferred usage |
| `nested_var` | required | `<required>` | inferred usage |
| `required_api_token` | required | `<required>` | inferred usage |
| `required_endpoint` | required | `<required>` | inferred usage |
| `required_input_var` | required | `<required>` | inferred usage |


Variable provenance and confidence notes:

Unresolved variables:
- `deep_var`: Referenced in role but no static definition found.
- `mock_role_configure_ini`: Referenced in role but no static definition found.
- `mock_role_debug`: Referenced in role but no static definition found.
- `mock_role_use_undeclared_collection`: Referenced in role but no static definition found.
- `nested_var`: Referenced in role but no static definition found.
- `required_api_token`: Referenced in role but no static definition found.
- `required_endpoint`: Referenced in role but no static definition found.
- `required_input_var`: Referenced in role but no static definition found.

Ambiguous variables:
- `nested_enabled`: Computed by set_fact at runtime.

Task/module usage summary
-------------------------

- **Task files scanned**: 6
- **Tasks scanned**: 20
- **Recursive includes**: 5
- **Unique modules**: 12
- **Handlers referenced**: 1

Inferred example usage
----------------------

```yaml
- hosts: all
  roles:
    - role: mock_role
      vars:
        mock_role_api: {endpoint: '{{ required_endpoint | default(''https://api.example.internal/v1'') }}',   timeout_seconds: 30, retries: 2}
        mock_role_config_path: /etc/mock-role/app.conf
        mock_role_env: {APP_MODE: production, APP_LOG_LEVEL: info}
```

Role Variables
--------------

The following variables are available:
- `mock_role_install_enabled`: True
- `mock_role_state`: present
- `mock_role_service_name`: mock-role
- `mock_role_packages`: ['nginx', 'curl']
- `mock_role_config_path`: /etc/mock-role/app.conf
- `mock_role_validate_config`: True
- `mock_role_rollback_enabled`: False
- `mock_role_env`: {'APP_MODE': 'production', 'APP_LOG_LEVEL': 'info'}
- `mock_role_api`: {'endpoint': "{{ required_endpoint | default('https://api.example.internal/v1') }}", 'timeout_seconds': 30, 'retries': 2}
- `mock_role_feature_flags`: {'healthcheck': True, 'metrics': True, 'legacy_mode': False}
- `mock_role_template_owner`: root
- `mock_role_template_group`: root
- `mock_role_template_mode`: 0644
- `variable1`: {{ default('Default value 1', omit) }}
- `variable2`: Default value 2
- `role_install_enabled`: {{ mock_role_install_enabled }}
- `role_package_name`: {{ mock_role_packages | first | default('nginx') }}
- `role_service_name`: {{ mock_role_service_name }}

Role contents summary
---------------------

The scanner collected these role subdirectories (counts):

- **handlers**: 1 files
- **tasks**: 6 files
- **templates**: 1 files
- **files**: 1 files
- **tests**: 3 files
- **defaults**: 1 files
- **vars**: 1 files
- **molecule_scenarios**: 1 files
- **task_catalog**: 20 files
- **handler_catalog**: 2 files
- **collection_compliance_notes**: 0 files

### Handlers

- handlers/main.yml


### Tasks

- tasks/deploy.yml
- tasks/main.yml
- tasks/nested/deeper.yml
- tasks/nested/setup.yml
- tasks/rollback.yml
- tasks/validate.yml


### Templates

- templates/app.conf.j2


### Files

- files/mock-role.env


### Tests

- tests/group_vars/all.yml
- tests/inventory
- tests/test.yml


### Defaults

- defaults/main.yml


### Vars

- vars/main.yml


### Molecule_scenarios

- {'name': 'default', 'driver': 'default', 'verifier': 'ansible', 'platforms': ['instance'], 'path': 'molecule/default/molecule.yml'}


### Detailed_catalog

- True
### Task_catalog


| File | Task | Module | Parameters | Runbook |
| --- | --- | --- | --- | --- |
| `main.yml` | [Gather runtime context](#task-main-yml-gather-runtime-context-1) | debug | msg='{{ lookup(''env'',''HOME'') | default(''/home/unknown'') }}' | [Details](#task-main-yml-gather-runtime-context-1) |
| `main.yml` | [Install package with privilege](#task-main-yml-install-package-with-privilege-2) | ansible.builtin.package | state='{{ mock_role_state }}' | - |
| `main.yml` | [Include setup phase](#task-main-yml-include-setup-phase-3) | import_tasks |  | - |
| `nested/setup.yml` | [Nested task default](#task-nested-setup-yml-nested-task-default-4) | debug | msg='{{ nested_var | default(''Nested default value'') }}' | - |
| `nested/setup.yml` | [Mark nested state](#task-nested-setup-yml-mark-nested-state-5) | ansible.builtin.set_fact | nested_enabled='{{ nested_enabled | default(true) }}' | - |
| `nested/setup.yml` | [Include deeper task file](#task-nested-setup-yml-include-deeper-task-file-6) | import_tasks | deeper.yml | - |
| `nested/deeper.yml` | [Deep nested task default](#task-nested-deeper-yml-deep-nested-task-default-7) | debug | msg='{{ deep_var | default(''Deep default value'') }}' | - |
| `nested/deeper.yml` | [Render deep template](#task-nested-deeper-yml-render-deep-template-8) | ansible.builtin.template |  | - |
| `main.yml` | [Include deploy phase](#task-main-yml-include-deploy-phase-9) | include_tasks |  | - |
| `deploy.yml` | [Deploy application template](#task-deploy-yml-deploy-application-template-10) | ansible.builtin.template | owner='{{ mock_role_template_owner }}', group='{{ mock_role_template_group }}', ... | [Details](#task-deploy-yml-deploy-application-template-10) |
| `deploy.yml` | [Install environment file](#task-deploy-yml-install-environment-file-11) | ansible.builtin.copy | owner=root, group=root, mode='0644' | - |
| `deploy.yml` | [Configure application ini settings with community.general](#task-deploy-yml-configure-application-ini-settings-with-community-general-12) | community.general.ini_file | path='{{ mock_role_config_path }}', section=settings, option=debug_enabled, ... | - |
| `deploy.yml` | [Example undeclared external collection usage](#task-deploy-yml-example-undeclared-external-collection-usage-13) | ansible.posix.synchronize | mode=push | - |
| `main.yml` | [Include validate phase](#task-main-yml-include-validate-phase-14) | include_tasks |  | - |
| `validate.yml` | [Validate rendered configuration exists](#task-validate-yml-validate-rendered-configuration-exists-15) | ansible.builtin.stat | path='{{ mock_role_config_path }}' | - |
| `validate.yml` | [Assert config file was deployed](#task-validate-yml-assert-config-file-was-deployed-16) | ansible.builtin.assert | that=[config_stat.stat.exists, config_stat.stat.size > 0], fail_msg=Config was n... | - |
| `main.yml` | [Include rollback phase](#task-main-yml-include-rollback-phase-17) | include_tasks |  | - |
| `rollback.yml` | [Rollback to previous package state](#task-rollback-yml-rollback-to-previous-package-state-18) | ansible.builtin.package | state=absent | - |
| `rollback.yml` | [Remove rendered configuration](#task-rollback-yml-remove-rendered-configuration-19) | ansible.builtin.file | path='{{ mock_role_config_path }}', state=absent | - |
| `main.yml` | [Validate required input variable](#task-main-yml-validate-required-input-variable-20) | debug | msg=Using required input {{ required_input_var }} | - |


#### Task details and runbooks

<a id="task-main-yml-gather-runtime-context-1"></a>
**`main.yml` • Gather runtime context**

- Parameters: `msg='{{ lookup(''env'',''HOME'') | default(''/home/unknown'') }}'`

<details>
<summary>Runbook</summary>

check `journalctl -u systemd-resolved` if home lookup fails; set HOME manually in the environment block

</details>

<a id="task-deploy-yml-deploy-application-template-10"></a>
**`deploy.yml` • Deploy application template**

- Parameters: `owner='{{ mock_role_template_owner }}', group='{{ mock_role_template_group }}', mode='{{ mock_role_template_mode }}'`

<details>
<summary>Runbook</summary>

if template render fails, manually copy /etc/app.conf.example to {{ mock_role_config_path }} and adjust owner/group

</details>
- Warning: notifies Restart mock service — ensure handler is present


### Handler_catalog

| File | Name | Module |
| --- | --- | --- |
| `main.yml` | Restart mock service | ansible.builtin.service |
| `main.yml` | Reload mock service | ansible.builtin.service |


Auto-detected role features
---------------------------

- **task_files_scanned**: 6
- **tasks_scanned**: 20
- **recursive_task_includes**: 5
- **unique_modules**: ansible.builtin.assert, ansible.builtin.copy, ansible.builtin.file, ansible.builtin.package, ansible.builtin.set_fact, ansible.builtin.stat, ansible.builtin.template, ansible.posix.synchronize, community.general.ini_file, debug, import_tasks, include_tasks
- **external_collections**: community.general
- **handlers_notified**: Restart mock service
- **privileged_tasks**: 1
- **conditional_tasks**: 5
- **tagged_tasks**: 4

Comparison against local baseline role
-------------------------------------

No comparison baseline provided.

Detected usages of the default() filter
---------------------------------------

The scanner found undocumented variables using `default()` in role files:

- defaults/main.yml:17 — `required_endpoint | default(https://api.example.internal/v1)`
  args: `https://api.example.internal/v1`
- tasks/deploy.yml:30 — `mock_role_debug | default(false)`
  args: `false`
- tasks/deploy.yml:34 — `when: mock_role_configure_ini | default(false)`
  args: `(false`
- tasks/deploy.yml:41 — `when: mock_role_use_undeclared_collection | default(false)`
  args: `(false`
- tasks/nested/deeper.yml:5 — `deep_var | default(Deep default value)`
  args: `Deep default value`
- tasks/nested/setup.yml:5 — `nested_var | default(Nested default value)`
  args: `Nested default value`


