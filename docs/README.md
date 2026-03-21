---
layout: default
title: Prism Documentation
---

Prism documentation in a dual-lane format: fast onboarding for average users and operational depth for DevOps professionals.

## What Prism Solves

Prism is not only a README generator. It is a workflow for codifying automation
knowledge from source and keeping it usable during delivery and incidents.

Key outcomes:

- lower adoption friction by mapping existing documentation conventions
- runbook-ready task guidance generated from source-adjacent markers
- portfolio visibility through machine-readable outputs and `prism-learn`

## Why Provenance Is Core

Prism does not ask readers to trust a black box. Provenance tracking makes
scanner output explainable by tying findings back to source and confidence.

- it shows what is explicit versus inferred
- it keeps static-analysis uncertainty visible instead of hidden
- it makes generated docs safer to use as automation contracts

## Strategic Model

Prism treats automation as a governed knowledge asset.

- **Automation contract**: generated docs define role/collection interface expectations
- **Knowledge capital**: JSON/markdown outputs compound in value as coverage grows
- **Policy loop**: scanner flags plus machine-readable outputs enable CI enforcement

## Start Here (10 Minutes)

Step 1: set up a local environment and install Prism.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Step 2: generate your first role README.

```bash
prism role path/to/role -o README.md
```

You should see: a generated README at the output path.

## Dual-Lane Paths

For average users:

- [Demos](./demos.md)
- [Getting Started](./getting-started.md)
- [User Guide](./user-guide.md)

For DevOps professionals:

- [DevOps Guide](./devops-guide.md)
- [Feedback Integration](./feedback-integration.md)

Shared quality references:

- [Provenance Tracking](./provenance-tracking.md)
- [Prism-Friendly Role Authoring](./prism-friendly-role-authoring.md)
- [Comment-Driven Documentation](./comment-driven-documentation.md)
- [Changelog](./changelog.md)

## Full Navigation

- [Demos](./demos.md): runnable CLI and API examples with expected outputs
- [Getting Started](./getting-started.md): fastest path for average users
- [User Guide](./user-guide.md): complete common tasks step by step
- [Provenance Tracking](./provenance-tracking.md): why Prism output is auditable and trustworthy
- [Comment-Driven Documentation](./comment-driven-documentation.md): marker-driven notes, runbooks, and task annotations
- [DevOps Guide](./devops-guide.md): build CI and policy workflows

## Developer Docs

Contributor and architecture content is in [dev_docs](./dev_docs/README.md).
