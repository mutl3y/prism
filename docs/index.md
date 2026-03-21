---
layout: default
title: Prism Documentation Home
---

## Overview

Build practical, trustworthy Ansible documentation from source code.

Prism helps teams keep existing conventions while still producing consistent
documentation and runbook artifacts. This reduces migration friction and enables
incremental quality improvement instead of all-at-once rewrites.

Prism uses static analysis, so unresolved runtime behavior is surfaced as
explicit uncertainty instead of hidden assumptions.

## Why Provenance Comes Early

Prism is most useful when readers can trust what it says. Provenance tracking
shows where facts came from and how confident the scanner is, which makes the
output auditable for authors, consumers, and platform teams.

## Why Teams Standardize On Prism

- **Automation API contract**: generated docs make role inputs and behavior reviewable
- **Knowledge capital**: each scan adds queryable documentation intelligence
- **Policy as code**: CI can enforce quality and annotation standards at source

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
prism role path/to/role -o README.md
```

## Learning Order

1. [Demos](./demos.md)
2. [Getting Started](./getting-started.md)
3. [User Guide](./user-guide.md)
4. [Provenance Tracking](./provenance-tracking.md)
5. [Comment-Driven Documentation](./comment-driven-documentation.md)
6. [Prism-Friendly Role Authoring](./prism-friendly-role-authoring.md)
7. [DevOps Guide](./devops-guide.md)
8. [Feedback Integration](./feedback-integration.md)
9. [Changelog](./changelog.md)

## Track By Role

For average users:

- run Demos first for runnable reference workflows
- start at Getting Started and complete the first role scan
- use User Guide workflows for routine docs generation
- use Provenance Tracking to understand what Prism knows versus infers
- add marker-based context with Comment-Driven Documentation patterns
- use Prism-Friendly Role Authoring when output quality is low
- keep current section naming conventions while improving structure over time

For DevOps professionals:

- implement policy-enforced CI in DevOps Guide
- add JSON and runbook CSV artifacts for automation
- add feedback-driven recommendations from prism-learn
- use generated runbook steps to reduce incident response cognitive load

## Leadership and Governance View

Use machine-readable outputs and `prism-learn` reporting to track:

- documentation health across roles and collections
- complexity hotspots and runbook coverage
- policy adherence and drift trends over time

## Why Provenance Matters

Prism does not hide uncertainty. Provenance tracking shows where role facts came
from and how confident the scanner is in each conclusion.

Start with [provenance-tracking.md](./provenance-tracking.md) if you want the
short product explanation before the engineering details.

## Developer Documentation

Engineering and project maintenance documentation lives under `dev_docs/`.

For runnable examples, start with [demos.md](./demos.md).
