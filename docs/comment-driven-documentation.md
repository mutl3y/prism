---
layout: default
title: Comment-Driven Documentation
---

Prism can turn task-adjacent comments into structured documentation.

This is one of the fastest ways to preserve operator knowledge close to the
source that implements it.

## Why It Matters

- keeps operational context next to the task it describes
- reduces drift between code and human instructions
- captures reviewer notes, warnings, and manual fallback steps
- improves runbook quality without requiring a separate authoring system

## Supported Marker Model

Prism uses `# prism~...` markers. The supported note marker is `prism~note`.

Common marker kinds:

- `prism~note`: general reviewer or operator note
- `prism~warning`: caution or rollback concern
- `prism~runbook`: task procedure text for runbook output
- `prism~task`: attach a note, warning, or runbook entry either to a specific named task or implicitly to the next task

## Example: `prism~note`

Use `prism~note` when you want a short free-form comment to appear with task
documentation.

```yaml
# prism~note: verify firewall openings before first deploy

- name: Start application service
  ansible.builtin.service:
    name: my-app
    state: started
```

Good uses:

- reviewer reminders
- pre-check hints
- environment-specific cautions that do not justify a runbook step

## Example: `prism~task`

Use `prism~task` in either of these modes:

- explicit mode: target a task by name
- implicit mode: place the annotation directly above the next task

Explicit targeting example:

```yaml
# prism~task: Restart application service | warning: confirm service user exists before restart
# prism~task: Restart application service | note: source=change-window-only

- name: Restart application service
  ansible.builtin.service:
    name: my-app
    state: restarted
```

Implicit next-task example:

```yaml
# prism~task: note: verify health checks before continuing

- name: Deploy and restart application node
  ansible.builtin.service:
    name: my-app
    state: restarted
```

Commented-out task example:

```yaml
# prism~task: warning: disabled during freeze window
#
# - name: Restart application service
#   ansible.builtin.service:
#     name: my-app
#     state: restarted
```

These patterns are useful when:

- the annotation needs to point at a specific task by name
- the comment should bind to the next task without repeating the task name
- the next task is currently commented out and should still be tracked as disabled context
- reviewers want explicit targeting in larger task files

## Example: Multiline `prism~runbook`

Use continuation comment lines immediately below the first marker line.

```yaml
# prism~runbook:
# precheck verify health endpoint returns 200
# drain node from load balancer
#
# restart service and wait 30 seconds
#
# postcheck confirm queue depth and error rate are normal

- name: Roll application node safely
  ansible.builtin.service:
    name: my-app
    state: restarted
```

## Authoring Rules

- keep markers directly above the task they describe
- use `key=value` hints instead of YAML-like `key: value` payloads
- keep task names stable if you rely on explicit `prism~task` name targeting
- use `prism~runbook` for actions, `prism~note` for context, and `prism~warning` for risk

## Provenance Advantage

Comment-driven documentation is more valuable when readers can see where facts
and inferences came from.

Pair marker usage with [provenance-tracking.md](./provenance-tracking.md)
to understand:

- which values came from explicit source declarations
- which values were inferred from static analysis
- which values remain runtime-dependent and uncertain

## Next Step

Use this guide with [getting-started.md](./getting-started.md) for your first
role scan and [user-guide.md](./user-guide.md) for everyday workflows.
