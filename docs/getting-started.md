---
layout: default
title: Getting Started
---

Start with one role scan, then branch to either average-user or DevOps workflows.

## Prerequisites

- Python 3.14+
- local checkout of Prism
- role or collection source to scan

## Expectation Setting

Prism is a static scanner. Runtime-only behavior is reported as uncertainty,
not guessed.

Use [provenance-tracking.md](./provenance-tracking.md) to understand how Prism
shows that uncertainty and why that makes the output more trustworthy.

## Step 1: Install Prism

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

You should see: `prism --help` returns subcommand usage.

## Step 2: Generate Your First Role README

```bash
prism role path/to/role -o README.md
```

You should see: role metadata, variable summary, and task sections in `README.md`.

## Step 3: Generate Collection Documentation

```bash
prism collection path/to/collection -f md -o COLLECTION_DOCS.md
```

You should see: role totals and plugin catalog sections in collection output.

## Step 4: Add Runbook Context To Tasks

Use a multiline marker by placing continuation comment lines directly under the
first `prism~runbook` line.

```yaml
# prism~runbook:
# precheck verify service health endpoint returns 200
# drain node from load balancer
#
# restart service and wait 30 seconds
#
# postcheck verify queue depth and error rate are normal
#
# prism~warning: rollback=manual approver=oncall
# rollback restore previous package version and re-add node to load balancer
#
- name: Roll application node safely
  ansible.builtin.service:
    name: my-app
    state: restarted
```

Re-run role scan:

```bash
prism role path/to/role \
  --detailed-catalog \
  --runbook-output RUNBOOK.md \
  --runbook-csv-output RUNBOOK.csv \
  -o README.md
```

You should see: marker notes rendered in task sections and a standalone
`RUNBOOK.md` with actionable operator steps.

For more marker patterns, including `prism~note` and `prism~task` in both
explicit-target and next-task forms, see
[comment-driven-documentation.md](./comment-driven-documentation.md).

## Dual-Lane Next Step

Average user lane:

- continue with [User Guide](./user-guide.md) common tasks
- use [Comment-Driven Documentation](./comment-driven-documentation.md) when adding operational context
- read [Provenance Tracking](./provenance-tracking.md) to understand scanner confidence
- use defaults + marker best practices from role authoring guide

DevOps lane:

- continue with [DevOps Guide](./devops-guide.md) for CI policy enforcement
- add feedback workflows from [Feedback Integration](./feedback-integration.md)

## Troubleshooting Checkpoint

- README contains role metadata, variables, and task summaries
- collection docs include plugin catalog sections
- marker comments appear in runbook/task details

Next: [User Guide](./user-guide.md) or [DevOps Guide](./devops-guide.md).
