---
layout: default
title: Policy Inputs and Audit Rules
---

The older `--feedback-from-learn` workflow has been retired.

The replacement policy model is explicit and file-backed:

- use native scan flags for built-in Prism strictness
- use `--audit-rules <path>` for Policy-as-Code evaluation against scan payloads
- use JSON scan outputs as inputs to external governance systems such as `prism-learn`

This keeps policy decisions reviewable in-repo instead of injecting mutable
runtime recommendations through a remote feedback channel.

## Replacement Policy

### 1. Native strict scan flags

Use built-in Prism controls when the policy is directly supported by the scan
surface.

```bash
prism role path/to/role \
  --fail-on-unconstrained-dynamic-includes \
  --fail-on-yaml-like-task-annotations \
  -o README.md
```

These flags are the first choice for hard fail-closed behavior because they are
owned directly by the scanner runtime.

### 2. Policy-as-Code audit rules

Use `--audit-rules` when the policy is evaluated from the generated scan
payload rather than from a built-in strictness flag.

```bash
prism role path/to/role \
  --audit-rules policy-rules.yml \
  --fail-on-audit-violations \
  -f json -o role_scan.json
```

The rule file must be a local YAML or JSON mapping with either a
`policy_rules` or `audit_rules` list.

Minimal example:

```yaml
policy_rules:
  - id: no-shell-without-runbook
    description: Shell tasks must have approved runbook coverage
    severity: error
  - id: runbook-coverage-min
    description: Warn when runbook coverage drops below target
    severity: warning
    params:
      threshold: 0.8
```

Current built-in rule IDs documented in the codebase are:

- `no-shell-without-runbook`
- `runbook-coverage-min`
- `dependency-compliance`

Remote HTTP/HTTPS rule loading is intentionally not supported. Policy inputs
must come from a local file path.

### 3. External governance loop

Use Prism JSON output as the stable input to downstream systems.

```bash
prism role path/to/role -f json -o role_scan.json
```

Systems such as `prism-learn` should consume the emitted JSON and produce
reporting, triage, or recommended next actions outside the Prism CLI contract.

## Migration From `--feedback-from-learn`

Map old usage to the new policy model as follows:

| Old intent | Replacement |
| --- | --- |
| Inject recommendation file into scan runtime | Convert the rule into native scan flags or a local `policy_rules` file used with `--audit-rules` |
| Pull recommendations from a remote endpoint during scan | Fetch or generate a local rules file before running Prism, then pass it with `--audit-rules` |
| Feed organizational guidance back into CI | Evaluate Prism JSON output in `prism-learn` or another governance system after the scan |

## Lane Notes

Average user lane:

- prefer native strict flags first
- use a small checked-in rules file when team policy exceeds built-in flags

DevOps lane:

- keep policy files versioned with the repo or generated deterministically in CI
- fail with `--fail-on-audit-violations` when audit rules are mandatory
- keep analytics and trend reporting in downstream systems consuming JSON output

## Role Example

```bash
prism role path/to/role \
  --audit-rules policy-rules.yml \
  --fail-on-audit-violations \
  -o README.md
```

## Collection Example

```bash
prism collection path/to/collection \
  --audit-rules policy-rules.yml \
  --fail-on-audit-violations \
  -f md -o COLLECTION_DOCS.md
```

## Repo Example

```bash
prism repo --repo-url https://github.com/org/repo -f json -o repo_scan.json
```

Then evaluate the emitted JSON in downstream governance tooling rather than
injecting remote recommendations into the repo scan command.

## Behavior and Errors

- missing audit rules file: scan exits with a clear error
- malformed YAML or JSON rules file: scan exits with a clear error
- audit violations plus `--fail-on-audit-violations`: Prism exits with audit failure status
- downstream recommendation systems should transform scan output before the next run, not during it

## Governance Outcome

With explicit policy files and stable JSON outputs, teams can move from ad hoc
recommendations to governed, reviewable enforcement inputs.
