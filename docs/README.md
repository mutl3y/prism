---
layout: default
title: Prism Documentation
---

Prism documentation for users, operators, and maintainers.

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

## Common Paths

For users generating documentation:

- [Demos](./demos.md)
- [Getting Started](./getting-started.md)
- [User Guide](./user-guide.md)

For operators and CI owners:

- [DevOps Guide](./devops-guide.md)
- [Policy Inputs and Audit Rules](./feedback-integration.md)

Shared quality references:

- [Provenance Tracking](./provenance-tracking.md)
- [Prism-Friendly Role Authoring](./prism-friendly-role-authoring.md)
- [Comment-Driven Documentation](./comment-driven-documentation.md)
- [Release Notes](./changelog.md)

## Full Navigation

- [Demos](./demos.md): runnable CLI and API examples with expected outputs
- [Getting Started](./getting-started.md): fastest path for average users
- [User Guide](./user-guide.md): complete common tasks step by step
- [Provenance Tracking](./provenance-tracking.md): why Prism output is auditable and trustworthy
- [Comment-Driven Documentation](./comment-driven-documentation.md): marker-driven notes, runbooks, and task annotations
- [DevOps Guide](./devops-guide.md): build CI and policy workflows
- [Release Notes](./changelog.md): short user-facing milestone history

## Developer Docs

Contributor and architecture content is in [dev_docs](./dev_docs/README.md).
For the current package ownership and capability map, start with [Package Capabilities](./dev_docs/package-capabilities.md).
