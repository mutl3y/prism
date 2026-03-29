---
layout: default
title: User Guide
---

Use this page as the task catalog for day-to-day usage.

For runnable end-to-end examples, see [demos.md](./demos.md).

## Role Contract Mindset

Treat generated output as the role's interface contract.

- consumers use it to understand accepted inputs and expected behavior
- authors use it to spot unclear variable/task design early
- teams use JSON output to validate contract quality in CI

## Workflow 1: Generate Role Docs

```bash
prism role <role_path> -o README.md
```

You should see: a role README with variables and task summary sections.

## Workflow 2: Generate Collection Docs

```bash
prism collection <collection_path> -f md -o COLLECTION_DOCS.md
```

You should see: role scan summary plus plugin catalog coverage.

## Workflow 3: Produce Machine-Readable Payload

```bash
prism role <role_path> -f json -o role_scan.json
```

Use this output for automation and quality reporting.

Contract validation pattern:

```bash
prism role <role_path> -f json -o role_scan.json
```

Then evaluate key fields in CI (for example: unresolved variables, include-path
warnings, or runbook annotation coverage).

## Workflow 4: Expand Detail Level

```bash
prism role <role_path> --detailed-catalog -o README.md
```

Use this mode when reviewers need task-level detail.

## Workflow 5: Generate Runbook Artifacts

```bash
prism role <role_path> \
  --runbook-output RUNBOOK.md \
  --runbook-csv-output RUNBOOK.csv \
  -o README.md
```

Use markdown for human review and CSV for automation.

## Lane Notes

Average user lane:

- start with workflow 1 and 2
- use workflow 4 only when you need deeper reviewer detail

DevOps lane:

- run workflow 3 and 5 in pipelines
- combine with strict policy controls from DevOps Guide

## Marker Style Rules

Write marker payloads as plain text or compact `key=value` hints.

For a dedicated marker reference, including targeted task annotations and
provenance positioning, see [comment-driven-documentation.md](./comment-driven-documentation.md).

Preferred examples:

- `# prism~runbook: owner=platform impact=high`
- `# prism~note: verify health checks before rollout`
- `# prism~warning: rollback=manual timeout=300s`

Targeted task example:

```yaml
# prism~task: Deploy and restart application node | note: source=approved-change

- name: Deploy and restart application node
  ansible.builtin.service:
    name: my-app
    state: restarted
```

Next-task binding example:

```yaml
# prism~task: warning: verify permissions manually

- name: Deploy and restart application node
  ansible.builtin.service:
    name: my-app
    state: restarted
```

`prism~task` can either target a task by name or bind implicitly to the next
task, including a commented-out task block.

Multiline runbook example:

```yaml
# prism~runbook: owner=platform impact=high window=offhours
# precheck verify health endpoint is green
# drain node from traffic
#
# deploy artifact and restart service
#
# postcheck verify error budget remains stable

- name: Deploy and restart application node
  ansible.builtin.service:
    name: my-app
    state: restarted
```

Keep multiline instructions as continuation comment lines immediately below the
marker line.

Avoid YAML-like marker payloads (`key: value`).

## Migration Guide: Legacy Support Removal

This is the primary migration reference for users moving from retired
`ansible_role_doc` legacy names to canonical Prism names.

### Legacy Names Removed and Canonical Replacements

| Legacy name/path | Canonical replacement | Notes |
| --- | --- | --- |
| `.ansible_role_doc.yml` | `.prism.yml` | Role section configuration filename |
| `ANSIBLE_ROLE_DOC_STYLE_SOURCE` | `PRISM_STYLE_SOURCE` | Style guide source environment variable |
| `$XDG_DATA_HOME/ansible_role_doc/STYLE_GUIDE_SOURCE.md` | `$XDG_DATA_HOME/prism/STYLE_GUIDE_SOURCE.md` | XDG user style guide location |
| `/var/lib/ansible_role_doc/STYLE_GUIDE_SOURCE.md` | `/var/lib/prism/STYLE_GUIDE_SOURCE.md` | System style guide location |

### Expected Retirement Errors and Meanings

| Error code | Meaning | What to do |
| --- | --- | --- |
| `LEGACY_SECTION_CONFIG_UNSUPPORTED` | The legacy role config file `.ansible_role_doc.yml` is no longer accepted. | Rename/migrate the file to `.prism.yml`. |
| `LEGACY_RUNTIME_PATH_UNAVAILABLE` | A retired runtime compatibility path was requested (for example, the legacy style-source env var). | Remove legacy runtime settings and use canonical Prism behavior. |

### Migration Checklist

1. Rename role config files from `.ansible_role_doc.yml` to `.prism.yml`.
2. Replace `ANSIBLE_ROLE_DOC_STYLE_SOURCE` with `PRISM_STYLE_SOURCE` in shell profiles, CI, and container/runtime env files.
3. Update style guide file locations from `ansible_role_doc` directories to `prism` directories for both XDG and system paths.
4. Search your role/tooling repos for legacy names and update references:

```bash
rg -n "\.ansible_role_doc\.yml|ANSIBLE_ROLE_DOC_STYLE_SOURCE|ansible_role_doc/STYLE_GUIDE_SOURCE\.md"
```

1. Run a post-migration scan and confirm it completes without legacy-retirement errors:

```bash
prism role <role_path> -o README.md
```

1. If an error appears, match its code to the table above and apply the listed corrective action.

## Troubleshooting

| Problem | Likely Cause | Action |
| --- | --- | --- |
| variable marked required unexpectedly | no static default discovered | define in `defaults/main.yml` |
| include path appears unresolved | dynamic include path | constrain with explicit allow-list conditions |
| runbook is sparse | markers missing or not attached to tasks | add `prism~runbook/warning/note` comments above named tasks |
