# Review Categories

Read only the sections relevant to the current sweep or focus axis.

## Duplication

- Duplicate or near-duplicate functions across modules
- Repeated compiled regexes or constant sets
- Multiple independent implementations of the same algorithm

Signature question: would a diff between two functions be nearly zero for non-trivial logic?

## Misplaced Ownership

- "Generic" modules importing platform-specific symbols
- Default policies or plugins that are secretly platform-bound
- Docstrings claiming platform-agnostic ownership while imports say otherwise

Signature question: if Ansible became Kubernetes, would this module have to change?

## Weak Typing

- `object`, unparameterized containers, unnecessary `Any`
- `= None` without `| None`
- Long anonymous `Callable[...]` aliases instead of `Protocol`
- Long bare tuple aliases instead of `NamedTuple`
- Mutable module-level sets that should be `frozenset`
- Public or plugin-facing functions lacking parameter or return annotations

## Silent Fallbacks

- Missing plugin/policy silently replaced by defaults
- `except Exception: pass`
- `getattr(..., None)` chains masking required state

Rule: undocumented behavior-changing fallback is always a finding.

## Missing Guards

- Methods assuming state was initialized elsewhere
- Likely `None` dereference paths
- Mutable default arguments

## Abstraction Leakage

- Cross-module imports of `_`-prefixed functions
- `_`-prefixed symbols exported via `__all__`
- Lower-level modules importing higher-level orchestrators
- Re-export chains obscuring ownership

## Test Coverage Gaps

- Newly authoritative modules missing direct tests
- No DI override coverage
- Only end-to-end tests where isolated unit tests are expected

## Facade Leakage

Internal runtime assembly symbols exposed through public API/CLI module re-exports.

- `api.py` or `cli.py` re-exporting composition factories, registry singletons, or assembly helpers
- Tests patching internal seams through the public facade (freezes the leak as test dependency)
- `api_layer` or `cli_app` imports binding directly to plugin-registry internals or bundle resolver internals

Signature question: if a caller imports `api.py` and sees `DEFAULT_PLUGIN_REGISTRY` or `build_run_scan_options_canonical`, is that a supported public contract or an implementation detail?

## Composition Root Pollution

More than one owned composition site constructing the DI container or preparing the policy bundle.

- `DIContainer` constructed outside the single declared ingress
- `ensure_prepared_policy_bundle` called from within a defaults/policy module rather than from the core ingress
- Runtime assembly state created in a layer that should only resolve defaults

Signature question: if you grepped for `DIContainer()` across the codebase, would more than one non-test file appear?

## Registry Authority Split

Multiple code paths each resolving the plugin registry from a different source within a single request scope.

- `execution_request_builder` injects a registry into `DIContainer` but also computes a separate `runtime_registry` from scan options
- `DIContainer` stores the registry as a private attribute that resolver paths outside the class cannot access
- `defaults._resolve_registry()`, `loader._resolve_plugin_registry()`, and kernel routing each read from a different authority

Signature question: if you injected a custom registry into a scan request, would you be able to prove that bundle prep, loader fallback, and runtime routing all used exactly that registry?

## Shell Layer Plugin Boundary Violation

CLI, API, or shell-layer facades importing directly from plugin-internal submodules instead of going through a stable seam.

- `cli.py` importing from `scanner_plugins.audit.*` directly inside a command handler
- `scanner_reporting` importing from `scanner_plugins.parsers.*` for rendering helpers
- Any shell module importing plugin-internal modules not covered by an architecture guardrail test

Signature question: if you renamed or moved a plugin-internal module, would a CLI command or reporting facade break?

## Error Channel Violations

Silent failure masking in I/O and extraction layers that prevent distinguishing between "not found" and "found but invalid".

- `except (TypeError, OSError, yaml.YAMLError): return None` patterns that convert load failures silently
- `or {}` / `or []` patterns in YAML loading that mask file-not-found vs empty-file
- `strict=True` flags that are ignored on shape validation failure (returning `{}` instead of raising)
- Broad `except Exception` not narrowed to the actual expected error set

Signature question: if a YAML file contained `null` instead of a dict, would the caller receive `None`, `{}`, or an error? Are all three distinguishable?

## Import Cycle Pressure

Runtime imports that should be `TYPE_CHECKING`-only, creating bidirectional module dependency edges that stress the strongly-connected component graph.

- A module imported for its concrete class also imports the caller's class in a factory or DI method, creating a back-edge (e.g. `DIContainer` ↔ `feature_detector`)
- Modules that only use a type in a function signature or annotation importing it at runtime instead of under `TYPE_CHECKING`
- Chains where `scanner_core → scanner_extract → scanner_io → scanner_plugins → scanner_core` close a loop through multiple intermediate hops

Signature question: if you moved the type annotation to a string forward-reference or `TYPE_CHECKING` import, would the runtime import disappear without breaking the module?

## Compatibility Shim Staleness

Thin re-export shims that were introduced as temporary compatibility bridges but never retired, hardening an obsolete import path into permanent policy.

- A module that contains only re-exports of symbols from a different package with no added logic
- A shim whose original migration plan has been marked closed in plan artifacts or AGENTS.md
- A shim whose re-exported symbols are available directly from the canonical module with no API difference

Signature question: if the shim file were deleted, would any caller break — and if so, why have those callers not been migrated?

## Policy Coercion Fail-Open

Config and policy parsing paths that silently return a default when a value fails validation, coercion, or type-check rather than raising or emitting a diagnostic.

- `if coerced is None: return default` without a warning log when coercion is unexpected
- Shape validation returning `{}` or `default_prefix` on type mismatch without indicating the failure to the caller
- Parse errors in override/config files silently collapsing to empty dict rather than propagating a load failure
- Strict-mode parameters that accept a `strict` flag but do not honour it when shape is wrong

Signature question: if a config file had a typo that caused a required field to coerce to `None`, would the caller get the wrong default silently or an observable error?

## Orchestration Seam Integrity

Orchestration functions that accept more than three collaborators typed as `Callable[..., Any]`, making the seam structurally unverifiable regardless of runtime correctness.

- A single function signature with ≥3 `Callable[..., Any]` parameters
- `getattr(obj, method_name)(...)` patterns used to call plugin entry points without a protocol
- Orchestration functions whose collaborator set is only validated by runtime duck-typing rather than declared protocol compliance
- `phase_output: Any` or `result: Any` in kernel/orchestrator return positions

This is distinct from Weak Typing, which covers individual `Any` annotations. The signature question here is qualitative: if an orchestrator accepts nine untyped callables, no amount of individual annotation cleanup is sufficient — the seam itself needs named protocols.

Signature question: can you write a type-correct stub for each collaborator this orchestration function accepts, and will mypy enforce it at the call site?

## Test Fixture Global State Coupling

Tests that depend on module-level singletons or global registries as implicit fixtures rather than constructing isolated test doubles, freezing global composition state as a test dependency.

- Tests that import `DEFAULT_PLUGIN_REGISTRY` directly and use it without overriding or isolating it
- Test suites that assert idempotent bootstrap behavior instead of asserting that a startup seam exists and has been called
- Tests that patch internal seams through the public API facade (which both normalizes the facade leak and couples the test to internal module paths)
- Tests missing DI override coverage — i.e., no test injects an alternative registry or policy plugin to verify the injection path is actually used

Signature question: if you ran two test modules in a single process, could one test's import of `scanner_plugins` affect the registry state seen by the other?

## Module-Level Singleton Pollution

Module-level variables holding concrete class instances used as global composition authorities, making test isolation, hot-reload, and multi-platform scenarios structurally difficult.

- Module-scope singleton instances of concrete plugin classes (`_TASK_LINE_PARSING_FALLBACK = AnsibleDefaultTaskLineParsingPolicyPlugin()`)
- A globally constructed registry object (`DEFAULT_PLUGIN_REGISTRY`) stored at module scope and imported across the codebase
- Module-level constants that are actually mutable objects (dicts, lists, plugin instances) rather than immutable data
- Fallback singletons constructed at import time that embed platform assumptions

Signature question: if two concurrent scan requests needed different platform defaults, would module-level singletons make that structurally impossible?
