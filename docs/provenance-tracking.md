---
layout: default
title: Provenance Tracking
---

Prism records where variable insights came from and how confident they are.

This is a core Prism differentiator because it makes static-analysis output
auditable instead of opaque.

## Why It Deserves Focus

Most automation scanners show conclusions without making the evidence model easy
to inspect. Prism keeps trust high by showing what was found, where it came
from, and how confident the scanner is in that conclusion.

## What Provenance Gives You

- a reviewable trail back to source files and line numbers when available
- a clear separation between explicit facts and inferred conclusions
- a safe way to expose uncertainty instead of guessing at runtime behavior
- better decisions about what can become CI policy versus what still needs runtime validation

## Confidence Model

- `explicit`: declared directly in parseable source and suitable for contract-grade use
- `inferred`: derived from static context and should be reviewed with surrounding logic
- `dynamic_unknown`: runtime-dependent and intentionally unresolved

## Why Teams Care

Authors:

- can see where interface assumptions are coming from
- can clean up unclear defaults, metadata, and task structure faster

Consumers:

- can trust documented inputs without reverse-engineering every task file
- can distinguish solid contract details from best-effort inference

DevOps and platform teams:

- can decide which findings are safe to enforce in CI
- can track uncertainty and drift as operational risk signals

## Practical Example

If Prism reports a variable as `explicit`, that usually means it was found in a
direct source such as `defaults/main.yml`. If it reports `inferred`, the value
may have been derived from static task or template context. If it reports
`dynamic_unknown`, runtime-only behavior prevented a reliable conclusion.

That distinction matters when generated docs are treated as an automation
contract.

## Where It Connects

- [comment-driven-documentation.md](./comment-driven-documentation.md): source-adjacent human context
- [getting-started.md](./getting-started.md): first scan and expectation setting
- [devops-guide.md](./devops-guide.md): policy enforcement and analytics workflows
- [dev_docs/provenance-tracking.md](./dev_docs/provenance-tracking.md): technical reference

## Bottom Line

Provenance tracking is one of the reasons Prism can present static analysis as a
trusted operational asset instead of an opaque summary.
