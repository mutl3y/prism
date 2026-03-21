---
layout: default
title: Static Analysis Scope
---

Defines what Prism currently guarantees and what remains out of scope.

## In Scope

- conventional role structure scanning
- static include/import path resolution
- variable and template signal extraction from parseable source
- style-aware rendering and section mapping
- collection summaries and plugin inventory payloads

## Out of Scope

- full runtime variable precedence evaluation
- unconstrained runtime include-path resolution
- exact runtime values for computed task-time expressions
- replacing `ansible-playbook` execution validation

## Practical Use

Treat generated docs as high-quality static documentation and pair with test execution for runtime assurance.

## Contract Reliability Model

When used as an automation contract, confidence should be interpreted as:

- explicit: directly declared in parseable source
- inferred: derived from static context with bounded confidence
- dynamic-unknown: runtime-dependent and intentionally marked uncertain

This model preserves trust by exposing uncertainty instead of speculating on
runtime-only behavior.
