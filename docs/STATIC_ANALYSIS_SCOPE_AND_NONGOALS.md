# Static Analysis Scope and Non-Goals

This document defines what Prism currently analyzes, and what it intentionally does not guarantee.

## In Scope

- Conventional role structure and files (`tasks`, `handlers`, `defaults`, `vars`, `meta`, `templates`).
- Static task include/import paths that can be resolved from source files.
- Role include/import references that are statically identifiable.
- Variable and template signals that can be inferred from parseable YAML/Jinja source.
- README/style-guide aware rendering and section-mapping behavior.
- Collection-root role iteration and collection-level summary payloads.

## Out of Scope (Current)

- Full runtime variable resolution across all Ansible precedence layers.
- Dynamic include paths or runtime-generated filenames that require execution context.
- Exact runtime values for variables computed only during task execution.
- Guaranteed semantic equivalence with playbook execution in all environments.
- Mutation or remediation of role code; Prism reports and renders, it does not fix automation logic.

## Non-Goals

- Replacing `ansible-playbook` as an execution or validation engine.
- Guaranteeing that generated documentation is sufficient as an operational runbook without role-owner review.
- Acting as a policy enforcement engine for every organization-specific rule.

## Design Principle

Prism prioritizes deterministic, reviewable output over speculative inference. When source evidence is ambiguous, it prefers uncertainty notes and conservative reporting.

## Practical Implications

- Use generated docs as high-quality static documentation, not as proof of runtime correctness.
- Pair Prism output with role tests (for example Molecule and CI) for execution assurance.
- Treat uncertain findings as prompts for role author cleanup (clear defaults, static includes, explicit metadata).
