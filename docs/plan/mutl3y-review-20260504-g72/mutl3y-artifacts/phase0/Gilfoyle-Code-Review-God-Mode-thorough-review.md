# Gilfoyle Thorough Review

Plan ID: `mutl3y-review-20260504-g72`
Cycle: `g72`
Target: `src/prism`
Reviewer: `Gilfoyle Code Review God Mode`
Date: `2026-05-04`

## Verdict
No Critical or High findings were identified in this unconstrained review of `src/prism`.

Total findings retained: 4.
Severity mix: 4 Medium, 0 Low.

## Findings

### 1. Medium: malformed policy-config shape fails open and silently disables enforcement toggles

Why this is a problem:

`scanner_config.policy` treats a non-mapping `.prism.yml` root as `{}` instead of a contract failure. That means shape corruption quietly falls back to defaults for enforcement toggles such as `fail_on_unconstrained_dynamic_includes`, `fail_on_yaml_like_task_annotations`, and underscore-reference suppression. Invalid YAML already raises a stable public error, so silently accepting the wrong top-level shape is an inconsistent and weaker boundary.

Evidence:

- `src/prism/scanner_config/policy.py:16-51` returns `{}` for non-dict roots after only a warning.
- `src/prism/scanner_config/policy.py:140-253` then converts missing values into default behavior for all public policy loaders.
- `src/prism/tests/test_t1_02_coverage_lift_batch4.py:85-108` proves invalid YAML raises, but `test_load_policy_config_non_dict_returns_empty` explicitly locks in the fail-open behavior for list roots.
- `src/prism/tests/test_scanner_config.py:127-153` covers only valid boolean loading and does not surface any user-visible error or structured warning for malformed root shape.

Impact:

A user can believe strict scan-policy enforcement is enabled while a malformed config root silently restores permissive defaults. That is a behavioral regression vector, not a cosmetic config quirk.

Recommendation:

Reject non-mapping policy roots with a stable public config error, or at minimum surface a structured warning into scan metadata so callers cannot mistake fail-open behavior for accepted policy.

Missing test coverage:

Add end-to-end assertions that malformed-but-parseable policy config shape is surfaced to callers, not merely logged.

### 2. Medium: kernel phase runner destroys structured failure identity at the boundary

Why this is a problem:

The kernel runner catches arbitrary plugin exceptions, logs only the exception string, and rewrites every failure to `KERNEL_PLUGIN_PHASE_FAILED` with `message=str(exc)`. `PrismRuntimeError` carries stable `code`, `category`, and `detail`, but that structure is discarded before the response leaves the kernel boundary.

Evidence:

- `src/prism/scanner_kernel/kernel_plugin_runner.py:139-153` catches `Exception`, logs without `exc_info=True`, and stores only a stringified message.
- `src/prism/scanner_core/protocols_runtime.py:20-25` defines `KernelPhaseFailure` without room for original exception metadata.
- `src/prism/errors.py:89-96` shows `PrismRuntimeError` already has stable structured fields worth preserving.
- `src/prism/tests/test_kernel_plugin_runner.py:116-178` and `src/prism/tests/test_kernel_plugin_runner.py:330-366` verify skip/fail-fast semantics, but there is no regression test asserting that `PrismRuntimeError` metadata survives the phase boundary.

Impact:

Downstream callers lose the difference between a contract error, a platform-not-supported error, and a generic runtime explosion. That weakens observability, makes automated handling harder, and turns incident triage into guesswork.

Recommendation:

Preserve structured error identity in the kernel envelope: original exception type, and for `PrismRuntimeError`, its `code`, `category`, and `detail`. Log phase failures with traceback context.

Missing test coverage:

Add a focused test where a plugin phase raises `PrismRuntimeError` and assert the response preserves structured metadata instead of collapsing everything to one generic code.

### 3. Medium: scan-cache policy fingerprint collapses object identity to class name, while registry compatibility still permits unmarked plugins

Why this is a problem:

The non-collection cache marker fingerprints any non-primitive prepared-policy object as `module.qualname` only. That assumes class identity is sufficient to represent behavior. It is not a safe assumption when registry compatibility still allows required-slot plugins that omit `PLUGIN_IS_STATELESS = True` and therefore may carry instance-specific behavior.

Evidence:

- `src/prism/api_layer/non_collection.py:410-488` reduces non-primitive bundle members to `type(value).__module__ + type(value).__qualname__` before cache-key construction.
- `src/prism/scanner_plugins/registry.py:56-88` defines stateless-required slots but still accepts missing stateless markers with a warning for backward compatibility.
- `src/prism/tests/test_t2_04_stateless_marker.py:40-48` explicitly locks in that backward-compat acceptance for required slots.
- `src/prism/tests/test_api_cli_entrypoints.py:1538-1779` covers only missing/malformed bundle markers and runtime wiring identity, not same-class/different-state bundle collisions.

Impact:

Two prepared bundles backed by the same plugin class but different instance state can hash to the same cache key and return stale results. The built-ins are mostly disciplined, but the public plugin boundary still tolerates weaker third-party declarations.

Recommendation:

Either hard-enforce stateless markers for all cache-relevant plugin slots, or include a stronger plugin fingerprint in the cache key contract than bare class name.

Missing test coverage:

Add a cache-key regression test with two prepared-policy instances of the same class but different observable behavior and assert distinct cache keys.

### 4. Medium: README style alias refresh still mutates process-global state without concurrency protection

Why this is a problem:

`scanner_readme.style_config` maintains a process-global alias table and refreshes it via in-place `.clear()` plus `.update()`. The module comment already admits this is not thread-safe. That would be survivable if the package were clearly single-threaded everywhere, but the repository already contains thread-safety expectations for other runtime surfaces.

Evidence:

- `src/prism/scanner_readme/style_config.py:13-18` defines process-global alias state.
- `src/prism/scanner_readme/style_config.py:38-53` mutates the shared dict in place and documents the lack of thread safety.
- `src/prism/tests/test_t1_02_coverage_lift.py:138-169` verifies only sequential scoped override and refresh behavior.
- `src/prism/tests/test_g02_thread_safety.py:1-58` demonstrates the project already treats concurrent safety as a real requirement for DI and eventing, but there is no analogous coverage here.

Impact:

Concurrent scans or embedded service usage can observe cross-request alias leakage or partially refreshed alias tables during style parsing/rendering.

Recommendation:

Move policy-derived aliases to request-scoped immutable snapshots, or guard refresh with atomic replacement under a lock. The current in-place mutation path is a concurrency seam waiting to become somebody else’s outage.

Missing test coverage:

Add a concurrency test for simultaneous refresh/read behavior, mirroring the existing thread-safety discipline used for DI and event bus paths.

## Top Recommendation
Tighten boundary contracts instead of softening them: fail closed on malformed policy shape, preserve structured runtime errors at the kernel boundary, and stop relying on weak global or cache identities for behavior-sensitive state.
