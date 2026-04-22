sample_role
=========

Role fixture packaged inside collection demo


Galaxy Info
-----------


- **Role name**: sample_role
- **Description**: Role fixture packaged inside collection demo
- **License**: MIT
- **Min Ansible Version**: 2.14

Requirements
------------

No additional requirements.

Role purpose and capabilities
-----------------------------

Role fixture packaged inside collection demo

Capabilities:
- Deploy configuration or content files
- Uses nested task includes for modular orchestration
- Triggers role handlers based on task changes

Role notes
----------

No role notes were found in comment annotations.

Inputs / variables summary
--------------------------

| Name | Type | Default | Source |
| --- | --- | --- | --- |
| `collection_demo_enabled` | bool | `true` | defaults/main.yml |
| `collection_demo_message` | str | `Hello from collection sample_role` | defaults/main.yml |
| `collection_demo_tags` | list | `[docs, collection]` | defaults/main.yml |


Task/module usage summary
-------------------------

- **Task files scanned**: 2
- **Tasks scanned**: 4
- **Recursive includes**: 1
- **Unique modules**: 4
- **Handlers referenced**: 1

Inferred example usage
----------------------

```yaml
- hosts: all
  roles:
    - role: sample_role
      vars:
        collection_demo_enabled: true
        collection_demo_message: Hello from collection sample_role
        collection_demo_tags: [docs, collection]
```

Role Variables
--------------

The following variables are available:
- `collection_demo_message`: Hello from collection sample_role
- `collection_demo_enabled`: True
- `collection_demo_tags`: ['docs', 'collection']

Role contents summary
---------------------

The scanner collected these role subdirectories (counts):

- **handlers**: 1 files
- **tasks**: 2 files
- **templates**: 1 files
- **files**: 0 files
- **tests**: 0 files
- **defaults**: 1 files
- **vars**: 0 files
- **molecule_scenarios**: 0 files
- **unconstrained_dynamic_task_includes**: 0 files
- **unconstrained_dynamic_role_includes**: 0 files
- **collection_compliance_notes**: 0 files
- **non_authoritative_test_evidence_limits**: 3 files
- **yaml_parse_failures**: 0 files

### Handlers

- handlers/main.yml


### Tasks

- tasks/configure.yml
- tasks/main.yml


### Templates

- templates/sample-role.txt.j2


### Defaults

- defaults/main.yml


### Marker_prefix

- p
- r
- i
- s
- m


### Ignore_unresolved_internal_underscore_references

- True
### Non_authoritative_test_evidence_limits

- max_file_bytes
- max_files_scanned
- max_total_bytes



Auto-detected role features
---------------------------

- **task_files_scanned**: 2
- **tasks_scanned**: 4
- **recursive_task_includes**: 1
- **unique_modules**: ansible.builtin.copy, ansible.builtin.debug, ansible.builtin.template, import_tasks
- **external_collections**: none
- **handlers_notified**: Refresh collection sample role state
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
