---
layout: default
title: DevOps Guide
---

Run Prism as a repeatable, policy-aware pipeline.

This guide focuses on two operational goals:

- translate task context into usable human procedures during incidents
- expose portfolio-level quality signals for governance decisions

Provenance matters here because policy should be built on findings that are auditable, confidence-aware, and explicit about uncertainty.

## Lane Split

Quick lane (single repository):

- use steps 1, 3, and 5 for immediate quality gains
- adopt strict policy flags after baseline cleanup

Platform lane (multi-team standard):

- implement all steps with `.prism.yml` policy defaults
- publish markdown, JSON, and runbook CSV artifacts every run
- track policy counters release-over-release

## Step 1: Run A Baseline Scan Job

```bash
pip install -e .
prism role path/to/role --detailed-catalog -o README.generated.md
```

You should see: deterministic README output in CI artifacts.

## Step 2: Enable Policy Enforcement

Enable strict checks once teams are remediated:

```bash
prism role path/to/role \
  --fail-on-unconstrained-dynamic-includes \
  --fail-on-yaml-like-task-annotations \
  -o README.generated.md
```

You should see: pipeline failure on policy violations instead of silent drift.

Equivalent config in `.prism.yml`:

```yaml
scan:
  fail_on_unconstrained_dynamic_includes: true
  fail_on_yaml_like_task_annotations: true
```

## Step 3: Emit Machine-Readable Outputs

```bash
prism role path/to/role -f json -o role_scan.json
prism role path/to/role --runbook-csv-output RUNBOOK.csv -o README.generated.md
```

Use JSON for analytics and CSV for runbook automation.

Why this matters:

- JSON supports trend and compliance reporting in `prism-learn`
- CSV/markdown runbooks reduce manual interpretation during on-call events

## Step 4: Integrate Feedback Inputs

Feedback-driven settings are supported via local file or API endpoint.

```bash
prism role path/to/role \
  --feedback-from-learn /path/to/feedback.json \
  -o README.generated.md
```

```bash
prism role path/to/role \
  --feedback-from-learn "https://learn.example.com/api/feedback?role=my_role" \
  -o README.generated.md
```

You should see: selected settings adjusted according to validated recommendations.

## Step 5: Standardize Operational Policy

- fail fast on annotation-quality policy after remediation
- publish markdown + JSON artifacts in every pipeline run
- track unresolved and ambiguous variable counters across releases

## Policy-As-Code Loop

Use Prism outputs as enforcement inputs, not only reporting artifacts.

Example checks teams commonly automate:

- fail build when unconstrained dynamic include findings exceed threshold
- fail build when YAML-like annotation payloads are detected in strict mode
- alert when runbook annotation coverage drops below internal target
- ticket when dependency declarations violate approved collection policy

These checks are implemented in CI policy scripts using scanner flags and JSON
output fields.

Leadership checks to operationalize:

- percent of roles with runbook annotations
- count of policy failures per team/repository
- critical-role coverage for runbook and standards compliance

## Reference

- CLI target details: [Developer CLI Targets](./dev_docs/cli-targets.md)
- provenance model: [Provenance Tracking](./provenance-tracking.md)
- authoring patterns: [Prism-Friendly Role Authoring](./prism-friendly-role-authoring.md)
