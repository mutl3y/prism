# Pure Execution Architecture

**Status:** Current architecture reference

---

## Overview

Prism uses a pure execution architecture for the scanner runtime: orchestration
is separated from platform behavior, and plugin-owned policy determines how the
scan pipeline behaves.

## Ownership Boundaries

| Layer | Owns | Must not own |
| --- | --- | --- |
| `scanner_core` | execution lifecycle, typed request/context assembly, orchestration | platform-specific branches and plugin policy |
| `scanner_kernel` | preflight, routing, strict/non-strict runtime behavior | parsing or traversal implementation |
| `scanner_plugins.*` | platform and policy behavior, parsing, traversal, feature-specific rules | shared payload contracts |
| `api.py` / `cli.py` | public entry surfaces and top-level flow wiring | runtime policy ownership |

## Runtime Rules

- request shaping happens before runtime execution begins
- `scanner_core` operates on typed request/context data instead of embedding platform heuristics
- `scanner_kernel` decides routing and fallback behavior
- platform-specific behavior lives in plugin-owned modules

## Plugin Selection

Resolution order is deterministic:

1. explicit scan option override
2. `policy_context` selection
3. platform match
4. registry default

## Strict And Non-Strict Handling

Strict mode fails fast when policy or runtime routing cannot be satisfied.
Non-strict mode can continue with warnings where the kernel has an approved
fallback path.

This keeps uncertainty visible instead of hiding it behind silent runtime
guessing.

## Policy Context Governance

Policy context provides request-bound policy and selector data.

- marker-prefix configuration is projected at ingress rather than discovered deep in the hot path
- invalid or conflicting policy context is surfaced explicitly
- plugins can extend behavior without changing shared scanner payload contracts

## Current Implications

- `scanner_core` remains generic and orchestration-focused
- `scanner_kernel` remains the routing and fallback authority
- `scanner_plugins.ansible` is the canonical Ansible implementation
- Kubernetes and Terraform expansion remain architecture-ready but are not implemented in the live package

## Normative References

- Architecture reference: `docs/dev_docs/architecture.md`
- Capability ownership: `docs/dev_docs/package-capabilities.md`
- Closure record: `docs/plan/architecture-extensibility-review-20260421/plan.yaml`
- Current product definition: `docs/PRD.yaml`
- CI guardrail: `.github/workflows/prism.yml`
