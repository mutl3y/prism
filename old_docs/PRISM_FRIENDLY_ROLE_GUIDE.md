# Prism-Friendly Role Guide

Use this guide when authoring roles you want Prism to document with high confidence.

## Defaults and Variables

- Prefer defining role inputs in `defaults/main.yml` with concrete defaults.
- Keep variable names stable and descriptive; avoid overloading one variable for unrelated behavior.
- Use `vars/main.yml` for fixed internal values, not user-facing inputs.
- If a value is required, document it in the role README variable section and avoid hiding it behind dynamic includes.

## Tasks and Includes

- Prefer static `include_tasks` and `import_tasks` paths whenever possible.
- Keep include targets file-based (`file:` or `_raw_params`) and relative to the role task tree.
- If dynamic include paths are required, constrain them with explicit `when` allow-lists so readers and tooling can follow known branches.
- Treat unconstrained dynamic include paths as a hazard: they hide execution paths, reduce documentation confidence, and make review/debugging harder.
- Use explicit task names for every task and handler.

Example: constrained dynamic include (preferred)

```yaml
- name: Include sub-operation
  ansible.builtin.include_tasks: "{{ sub_operation }}.yml"
  when: sub_operation in ["sub_operation1", "sub_operation2"]
```

Example: unconstrained dynamic include (hazard)

```yaml
- name: Include runtime-selected task file
  ansible.builtin.include_tasks: "{{ arbitrary_task_file }}"
```

## Templates and Jinja

- Keep `default(...)` expressions readable and compact.
- Avoid unnecessary nested inline expressions when simpler variable precomputation works.
- Prefer deterministic template variable references over runtime-generated key names.

## Metadata and Dependencies

- Keep `meta/main.yml` current (description, platforms, min ansible version).
- Declare collection and role dependencies in requirements files where applicable.
- Keep Molecule scenarios under `molecule/<scenario>/molecule.yml` for automatic discovery.

## Style-Guide Compatibility

- If you use `--style-readme`, keep section headings consistent across updates.
- For custom section labels, add mappings in `.prism.yml` (`readme.include_sections`).
- For stable team output, keep a dedicated style-source README and treat it as source-controlled input.

## Quick Checklist

- [ ] Inputs live in `defaults/main.yml`.
- [ ] Task and handler names are explicit.
- [ ] Include/import paths are mostly static.
- [ ] README variable section reflects actual role inputs.
- [ ] `meta/main.yml` and requirements are current.
