# Provenance Tracking

Prism records where variable insights came from and how confident they are.

This is a core Prism differentiator because it makes static-analysis output
auditable instead of opaque.

This page is the technical companion to the top-level product guide at
[provenance-tracking.md](../provenance-tracking.md).

## Provenance Fields

- source file path
- source line number when available
- source type (`defaults`, `vars`, `meta`, `include_vars`, `set_fact`, `readme`)
- confidence level (`explicit`, `inferred`, `dynamic_unknown`)

## Why This Matters

- helps reviewers distinguish facts from inference
- supports confidence-aware documentation consumption
- improves triage for unresolved variable findings

## Why It Is A Product Differentiator

- turns generated docs into reviewable contracts instead of black-box summaries
- preserves trust by exposing uncertain or runtime-dependent conclusions
- helps teams decide what can be enforced in CI and what still needs runtime validation

## Example Interpretation

- `explicit`: value was declared directly in source and can be treated as contract-grade
- `inferred`: value was derived from static context and should be reviewed with surrounding logic
- `dynamic_unknown`: value depends on runtime behavior and should not be treated as fully resolved

## Related Guides

- [provenance-tracking.md](../provenance-tracking.md)
- [comment-driven-documentation.md](../comment-driven-documentation.md)
- [static-analysis-scope.md](./static-analysis-scope.md)
