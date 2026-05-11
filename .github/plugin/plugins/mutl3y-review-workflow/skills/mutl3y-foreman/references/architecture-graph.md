# Architecture Graph

This skill uses a deterministic architecture graph to reduce split-brain discovery across isolated scouts.

## Purpose

`digest.yaml` and `import-graph.json` are still useful, but they do not capture enough structural truth for cross-cutting questions like:

- who constructs DI state
- which resolver path is the authority
- which facade re-exports internal helpers
- which tests pin a seam
- which modules depend on singletons or registry globals

The architecture graph fills that gap without forcing every scout to read the whole codebase.

## Artifact Set

- `docs/plan/.mutl3y-lessons/architecture-graph.json`: canonical repo-level graph
- `docs/plan/<PLAN_ID>/mutl3y-artifacts/phase0/graph-slices/<AGENT_NAME>.json`: role-scoped slice for one scout
- `docs/plan/<PLAN_ID>/mutl3y-artifacts/phase3/graph-slices/<AGENT_NAME>.json`: finding-scoped slice for one investigator

## Freshness Rule

Refresh `architecture-graph.json` when either is true:

- relevant source mtimes are newer than the cached graph
- the foreman is starting a new thorough review or a deep review after architecture-heavy changes

Do not rebuild it between every subagent launch if the inputs are unchanged.

## Keep It Deterministic

The graph is a structural cache, not a prose memory store.

Allowed node kinds:

- `module`
- `class`
- `function`
- `facade`
- `composition_root`
- `registry`
- `plugin`
- `test`
- `singleton`

Allowed edge kinds:

- `imports`
- `re_exports`
- `constructs`
- `calls`
- `resolves_from`
- `owned_by`
- `covered_by_test`
- `touches_singleton`
- `declared_seam`

Keep node payloads compact:

- stable id
- kind
- file path
- symbol name when applicable
- small metadata bag for machine-derivable facts only

Do not put free-form conclusions or unverified findings into the graph.

## Scout Usage

Scouts should read only a role-specific slice, not the full graph.

Examples:

- `Scout-Typing`: seam boundaries, protocol-return sites, `Any`-heavy orchestration nodes
- `Scout-Ownership`: module ownership edges, facade re-exports, platform-specific imports
- `Scout-ControlFlow`: fallback-heavy nodes, exception edges, strict/non-strict control seams
- `Scout-Graph`: import pressure, cycle candidates, singleton usage, registry-resolution paths

## Synthesizer Usage

`Synthesizer-Architecture` may read:

- all scout artifacts
- the full `architecture-graph.json`
- live source for verification

The synthesizer is the only normal Phase 0 reader of the whole graph.

## Verification Rule

The graph is a navigation aid. It is never sufficient close evidence by itself.

Before promoting or closing a finding:

- verify the claim against live source
- cite the exact code line
- cite the test or gap that makes the seam meaningful

## Suggested Build Command

If you need a deterministic seed implementation, use:

```bash
python scripts/build_architecture_graph.py --repo-root <REPO_ROOT> --output docs/plan/.mutl3y-lessons/architecture-graph.json
```
