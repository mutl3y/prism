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

## Troubleshooting

| Problem | Likely Cause | Action |
| --- | --- | --- |
| variable marked required unexpectedly | no static default discovered | define in `defaults/main.yml` |
| include path appears unresolved | dynamic include path | constrain with explicit allow-list conditions |
| runbook is sparse | markers missing or not attached to tasks | add `prism~runbook/warning/note` comments above named tasks |
