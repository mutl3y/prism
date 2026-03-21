# Prism-Friendly Role Authoring

Write roles so scanner output stays stable, complete, and review-friendly.

## Lane Notes

Average user lane:

- prioritize clear defaults and explicit task names
- use constrained includes only when needed

DevOps lane:

- standardize this checklist in role templates
- enforce annotation and include-path quality in CI

## Defaults and Variables

- define user-facing role inputs in `defaults/main.yml`
- keep names stable and descriptive
- use `vars/main.yml` for fixed internal values
- document required variables clearly

## Tasks and Includes

- prefer static `include_tasks` and `import_tasks` paths
- use explicit task and handler names
- constrain dynamic include paths with allow-listed `when` conditions

Preferred pattern:

```yaml
- name: Include sub-operation
  ansible.builtin.include_tasks: "{{ sub_operation }}.yml"
  when: sub_operation in ["sub_operation1", "sub_operation2"]
```

Avoid unconstrained dynamic includes:

```yaml
- name: Include runtime-selected task file
  ansible.builtin.include_tasks: "{{ arbitrary_task_file }}"
```

## Templates and Jinja

- keep `default(...)` expressions readable
- avoid deeply nested inline expressions when simpler preprocessing is possible
- prefer deterministic variable references

## Metadata and Dependencies

- keep `meta/main.yml` accurate and current
- declare role and collection dependencies explicitly
- keep molecule scenarios in `molecule/<scenario>/molecule.yml`

## Checklist

- [ ] Inputs are defined in defaults
- [ ] task names are explicit
- [ ] includes are static or constrained
- [ ] metadata and requirements are current
