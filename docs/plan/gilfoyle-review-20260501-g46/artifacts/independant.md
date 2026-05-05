I’m doing a fresh code-first sweep now with no reliance on the old ledgers: broad pattern discovery first, then live reads on the highest-risk slices, then I’ll give you a real verdict with findings first.

Search complete: Find architecture risks

Searched for files matching `**/src/prism/**/*`, 308 matches

Searched for regex `subprocess|Popen|run\(|check_output|check_call|os\.system|shell=True|exec\(|eval\(` (`**/src/prism/**/*.py`), 29 results

Searched for regex `resolve\(|Path\(|realpath|abspath|normpath|expanduser|joinpath|relative_to\(|parents\[|cwd|chdir|os\.path` (`**/src/prism/**/*.py`), 200 results

Searched for regex `global |@lru_cache|cache\(|singleton|registry|REGISTRY|_registry|DEFAULT_|setdefault\(|append\(|clear\(|mutable|Lock\(|RLock\(` (`**/src/prism/**/*.py`), 200 results

Searched for regex `from .* import \*|__all__|bootstrap|initialize|wire|container|provider|inject|resolve_plugin|register|entry_points|import_module|pkgutil|__init__` (`**/src/prism/**/*.py`), 200 results

Read [](file:///raid5/source/test/prism/src/prism/api_layer/non_collection.py#1-1), lines 1 to 340

Read [](file:///raid5/source/test/prism/src/prism/api_layer/plugin_facade.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/bootstrap.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/registry.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_core/events.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_core/di.py)

Read [](file:///raid5/source/test/prism/src/prism/repo_services.py#1-1), lines 1 to 140

Read [](file:///raid5/source/test/prism/src/prism/path_safety.py)

Search complete: Find contract debt

Searched for files matching `**/src/prism/**/*.py`, 228 matches

Searched for regex `\bAny\b|Callable\s*\[\s*\.\.\.\s*,\s*Any\s*\]|dict\s*\[\s*str\s*,\s*Any\s*\]|TypedDict|cast\(|Protocol|Mapping\[\s*str\s*,\s*Any\s*\]|MutableMapping\[\s*str\s*,\s*Any\s*\]` (`**/src/prism/**/*.py`), 200 results

Searched for regex `json\.|from_json|to_json|asdict|model_dump|model_validate|parse_obj|__dict__|isinstance\(|hasattr\(|getattr\(|setattr\(` (`**/src/prism/**/*.py`), 200 results

Searched for regex `Callable\s*\[\s*\.\.\.\s*,\s*Any\s*\]` (`**/src/prism/**/*.py`), 3 results

Searched for regex `cast\(` (`**/src/prism/**/*.py`), 19 results

Searched for regex `dict\s*\[\s*str\s*,\s*Any\s*\]|Mapping\[\s*str\s*,\s*Any\s*\]|MutableMapping\[\s*str\s*,\s*Any\s*\]` (`**/src/prism/**/*.py`), 200 results

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/defaults.py#520-520), lines 520 to 585

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/ansible/kernel.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_kernel/kernel_plugin_runner.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_kernel/plugin_name_resolver.py)

Search complete: Find fail-open risks

Searched codebase for "broad exception silent fallback returning empty container or None malformed input non-strict validation YAML parsing plugin orchestration file loading repo intake src/prism", 21 results

Searched for files matching `prism` · `src/prism/**/*`, 200 matches

Searched for regex `except\s*:|except\s+Exception|except\s+BaseException|return\s+\[\]|return\s+\{|return\s+set\(|return\s+None|yaml|safe_load|load\(|plugin|fallback|default|try:` (`prism` · `src/prism/**`), 200 results

Read [](file:///raid5/source/test/prism/src/prism/scanner_io/loader.py#1-1), lines 1 to 260

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/parsers/yaml/parsing_policy.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_extract/discovery.py#1-1), lines 1 to 260

Read [](file:///raid5/source/test/prism/src/prism/scanner_kernel/repo_context.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/defaults.py#1-1), lines 1 to 420

Read [](file:///raid5/source/test/prism/src/prism/scanner_kernel/kernel_plugin_runner.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/defaults.py#420-420), lines 420 to 520

Read [](file:///raid5/source/test/prism/src/prism/api_layer/common.py)

Read [](file:///raid5/source/test/prism/src/prism/api_layer/collection.py#140-140), lines 140 to 240

Read [](file:///raid5/source/test/prism/src/prism/scanner_io/collection_payload.py#60-60), lines 60 to 220

Read [](file:///raid5/source/test/prism/src/prism/scanner_extract/task_file_traversal.py#90-90), lines 90 to 190

Read [](file:///raid5/source/test/prism/src/prism/scanner_reporting/collection_dependencies.py#80-80), lines 80 to 160

I’ve got fresh repo-wide candidates from code search; now I’m reading the new suspect slices directly to separate real architectural defects from the usual static-analysis fan fiction.

Read [](file:///raid5/source/test/prism/src/prism/scanner_io/collection_payload.py#200-200), lines 200 to 249

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/defaults.py#520-520), lines 520 to 570

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/ansible/kernel.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_kernel/plugin_name_resolver.py)

Read [](file:///raid5/source/test/prism/src/prism/api_layer/common.py)

I’ve validated several fresh code-level seams myself; I’m adding one independent whole-tree review pass now so the final verdict isn’t just my own charmingly perfect paranoia talking.

Independent architecture review

Searched for regex `except Exception|fallback|default to|default=.*ansible|os\.environ|global |singleton|lru_cache|cache|Any\]|-> Any|cast\(|getattr\(.*default|warn|warning` (`prism` · `src/prism/**`), 200 results

Read [](file:///raid5/source/test/agent_and_skills/.github/instructions/python.instructions.md)

Search complete: Map runtime seams

Searched for files matching `prism` · `src/prism/**/*.py`, 200 matches

Searched for regex `entrypoint|main\(|if __name__ == ['\"]__main__['\"]|scan|plugin|registry|container|inject|global|state|__all__|from \.|public|api` (`prism` · `src/prism/**/*.py`), 200 results

Searched codebase for "main runtime entrypoints public API facade DI container plugin registry composition where scan execution starts plugins resolved global state prism", 17 results

Searched for regex `_registry|registry =|default_plugin_registry|get_default_plugin_registry|global |threading.Lock|lru_cache|cache|singleton|repo_scan_facade|__all__|run_scan\(|scan_role\(|main\(|app\(` (`prism` · `src/prism/**/*.py`), 200 results

Read [](file:///raid5/source/test/prism/src/prism/api.py#1-1), lines 1 to 220

Read [](file:///raid5/source/test/prism/src/prism/cli.py#1-1), lines 1 to 260

Read [](file:///raid5/source/test/prism/src/prism/__init__.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/interfaces.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/defaults.py#1-1), lines 1 to 320

Read [](file:///raid5/source/test/prism/src/prism/scanner_kernel/plugin_name_resolver.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/__init__.py)

Read [](file:///raid5/source/test/prism/src/prism/repo_services.py)

Searched for regex `strict_mode\s*=\s*False|strict_mode=False|resolve_.*strict_mode|_resolve_plugin_with_precedence\(|resolve_comment_driven_documentation_plugin\(` (`prism` · `src/prism/**`), 26 results

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/bootstrap.py)

Read [](file:///raid5/source/test/prism/src/prism/api_layer/collection.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/discovery.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/bundle_resolver.py)

Searched for regex `^[_A-Z]*DEFAULT_|global |_DEFAULT_REGISTRY|plugin_registry =|threading\.Lock\(|os\.environ|get_default_plugin_registry\(|initialize_default_registry\(|discover_entry_point_plugins\(` (`prism` · `src/prism/**`), 144 results

Read [](file:///raid5/source/test/prism/src/prism/api_layer/plugin_facade.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_kernel/repo_context.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_core/scan_request.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_core/scanner_context.py)

Read [](file:///raid5/source/test/prism/src/prism/api.py#1-1), lines 1 to 260

Read [](file:///raid5/source/test/prism/src/prism/scanner_data/contracts_request.py#1-1), lines 1 to 260

Read [](file:///raid5/source/test/prism/src/prism/scanner_core/events.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_data/__init__.py#1-1), lines 1 to 260

Read [](file:///raid5/source/test/prism/src/prism/errors.py)

Searched for regex `scan_degraded|strict_phase_failures|FailurePolicy\(|failure_policy|best-effort|continuing in best-effort mode` (`prism` · `src/prism/**`), 86 results

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/registry.py#220-220), lines 220 to 464

Read [](file:///raid5/source/test/prism/src/prism/scanner_core/feature_detector.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_core/variable_discovery.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_readme/style_config.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_kernel/orchestrator.py#220-220), lines 220 to 340

Read [](file:///raid5/source/test/prism/src/prism/scanner_core/execution_request_builder.py#300-300), lines 300 to 532

Searched for regex `def run_scan\(|DEFAULT_PLUGIN_REGISTRY =|discover_entry_point_plugins\(|def _construct_registry_plugin\(|def _validate_plugin_shape\(|def refresh_policy_derived_state\(|_DEFAULT_LISTENERS|class RoleScanResult|class RepoScanResult|class ScanPipelinePlugin|class FeatureDetectionPlugin|class VariableDiscoveryPlugin` (`prism` · `src/prism/**`), 60 results

Searched for regex `except Exception as exc|continuing in best-effort mode|scan_degraded|falling back to default` (`prism` · `src/prism/**`), 35 results

Searched for regex `RuntimeError\)|raise RuntimeError|PrismRuntimeError\(|recoverable_scan_errors|collection_role_runtime_recoverable_errors` (`prism` · `src/prism/**`), 157 results

Read [](file:///raid5/source/test/prism/src/prism/scanner_io/collection_payload.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_kernel/kernel_plugin_runner.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_readme/__init__.py)

The independent pass surfaced two additional architectural smells worth validating directly: import-time plugin bootstrap and leftover process-global state. I’m checking those in source before I hand you the final autopsy.

Read [](file:///raid5/source/test/prism/src/prism/scanner_readme/style_config.py)

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/__init__.py#180-180), lines 180 to 203

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/discovery.py)

I’ve confirmed the import-time bootstrap problem in source. One last read on the public facade and declared result types, then I’ll give you the full code-first verdict without leaning on any plan propaganda.

Read [](file:///raid5/source/test/prism/src/prism/api.py#1-1), lines 1 to 180

Read [](file:///raid5/source/test/prism/src/prism/scanner_plugins/interfaces.py#1-1), lines 1 to 130

Read [](file:///raid5/source/test/prism/src/prism/scanner_data/__init__.py#1-1), lines 1 to 120

I’ve got the substance; I’m just tightening the line anchors for the final write-up so you get a defensible review instead of vague sneering.

Searched for regex `DEFAULT_PLUGIN_REGISTRY = initialize_default_registry\(|discover_entry_point_plugins\(|refresh_policy_derived_state\(|_DEFAULT_LISTENERS: list\[EventListener\] = \[\]|effective_listeners = \(` (`**/src/prism/scanner_plugins/__init__.py|src/prism/scanner_plugins/bootstrap.py|src/prism/scanner_readme/style_config.py|src/prism/scanner_core/events.py|src/prism/scanner_core/di.py`), no results

Searched for regex `def run_scan\(|class RoleScanResult|class RepoScanResult|def orchestrate_scan_payload\(|def process_scan_pipeline\(` (`**/src/prism/api.py|src/prism/scanner_data/__init__.py|src/prism/scanner_plugins/interfaces.py`), no results

Searched for regex `return \{\}|return \[\]|non-strict mode: returning empty dict|non-strict mode: skipping file|scan_degraded=True` (`**/src/prism/scanner_extract/discovery.py|src/prism/scanner_core/scanner_context.py`), no results

**Findings**
- High — Import-time plugin bootstrap is still a hidden composition root, and it can execute third-party plugin registration during import. The package creates the default registry as a side effect in prism/src/prism/scanner_plugins/__init__.py, and entry-point discovery loads and runs external registration callables in prism/src/prism/scanner_plugins/discovery.py. That is tolerable for a toy CLI; it is not a clean product boundary for an embeddable tool or service.
- High — Repo-scoped scans do not actually stay repo-scoped. In prism/src/prism/repo_services.py and prism/src/prism/repo_services.py, resolved paths are accepted after existence checks without proving they stay under the checkout root, even though a containment helper already exists in prism/src/prism/path_safety.py. That is a direct trust-boundary failure, not a stylistic quibble.
- High — Repository cloning still allows Git option injection through attacker-controlled leading-dash input. The command is assembled in prism/src/prism/repo_services.py and the unvalidated repo URL is appended in prism/src/prism/repo_services.py without a delimiter to stop Git option parsing. No shell is involved, which is nice, but Git still parses argv like an adult.
- High — Ansible include_vars resolution can escape the role root and then load host-side YAML as trusted variable input. The offending path resolution is in prism/src/prism/scanner_plugins/ansible/default_policies.py and prism/src/prism/scanner_plugins/ansible/default_policies.py. For a scanner that claims structured ownership boundaries, that is an ugly miss.
- High — The most important product seams are still convention-based dict pipes rather than stable contracts. The public non-collection seam still exposes a dict payload in prism/src/prism/api.py and prism/src/prism/scanner_data/__init__.py, while plugin and kernel interfaces remain dict-in, dict-out and Any-heavy in prism/src/prism/scanner_plugins/interfaces.py, prism/src/prism/scanner_core/protocols_runtime.py, prism/src/prism/scanner_kernel/kernel_plugin_runner.py, and prism/src/prism/scanner_io/output_orchestrator.py. Architecturally, that means the code is still more disciplined than the contracts it advertises.
- Medium — Non-strict execution still converts malformed input and some runtime failures into success-shaped output with warnings or degraded metadata. You can see that in prism/src/prism/scanner_extract/discovery.py, prism/src/prism/scanner_extract/discovery.py, and prism/src/prism/scanner_core/scanner_context.py. That is explicit behavior, not accidental, but it still creates a product risk because downstream consumers must notice metadata instead of trusting the returned payload.
- Medium — Residual process-global mutable state still exists in places that should be request-scoped. The style alias refresh path openly mutates module-global state in prism/src/prism/scanner_readme/style_config.py, and default event listeners are still process-global in prism/src/prism/scanner_core/events.py and inherited into new containers in prism/src/prism/scanner_core/di.py. That is manageable in a single-process CLI; it is exactly the sort of thing that becomes embarrassing when real concurrency arrives.

**Assumptions**
- This pass was code-only. I did not rely on plan artifacts, closure ledgers, or prior findings to form the verdict.
- I did not rerun the full pytest, ruff, black, and typecheck bundle in this review pass, though current editor diagnostics for the source tree were clean.

**Verdict**
Architecturally, it is going the right way. There is real structure here now: the DI seam is explicit in prism/src/prism/scanner_core/di.py, plugin construction is at least being validated in prism/src/prism/scanner_plugins/registry.py, and the code no longer reads like a pile of accidental imports with delusions of grandeur.

But it is not Pied Piper product-ready yet. Not because the codebase is hopeless, but because the remaining defects are exactly the ones that separate a promising internal tool from a trustworthy product: hidden composition at import time, broken trust boundaries around file paths, weak public contracts, and best-effort fallbacks that still look like success. In other words, the architecture has matured faster than the guarantees.

My blunt answer is this: it is no longer amateur hour, but it still is not something I would call product-grade with a straight face.

What would change that verdict:
1. Eliminate the current High trust-boundary issues in repo intake and include_vars handling.
2. Stop doing default plugin bootstrap as an import side effect.
3. Harden the public and kernel/plugin seams into concrete contracts instead of dict-shaped politeness.
4. Re-run a fresh scout cycle and an independent full review and get zero Critical or High results from both.
