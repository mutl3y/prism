# Scout Scan Patterns

Use this during Phase 0 before broad reading. Treat these as starter probes, not proof.
Every promoted observation must be verified against live source and include the exact file/line.

## Probe Order

1. Read `digest.yaml` skip patterns and current open findings.
2. Run deterministic probes for your assigned categories.
3. Use `import-graph.json` and your role-scoped graph slice to pick close-neighbor files.
4. Verify each candidate in source before writing it as an observation.
5. Group related candidates with a shared `fix_group_key` so Phase 5 can batch safely.

## Typing And Contract Probes

- `rg -n "\bAny\b|Callable\[\.\.\.|Callable\[.*Any|cast\(Any|typing\.cast\(Any" src tests`
- `rg -n "dict\([^)]*TypedDict|cast\([^)]*,\s*dict\(" src tests`
- `rg -n "phase_output: Any|result: Any|dict\[str, Any\]|tuple\[.*Any" src`
- Check public/plugin-facing functions for missing return annotations before flagging local helpers.

## Control-Flow And Error-Channel Probes

- `rg -n "except\s+Exception\s*:\s*pass|except\s+Exception|return\s+(None|\{\}|\[\])|\bor\s+\{\}|\bor\s+\[\]" src`
- `rg -n "strict\s*=|strict:" src` and verify strict failures do not collapse to defaults.
- When a strictness flag is threaded across layers, trace it from ingress into
  the final helper branch and verify the advertised non-strict fallback path
  actually exists in both runtime code and the nearest tests:
  `rg -n "strict_phase_failures|strict_mode|_fallback_or_raise|
  malformed_plugin_shape" src tests`
- For fallback findings, classify whether the fallback is documented behavior, diagnostic fallback, or silent behavior change.
- For subprocess callsites, check tool-native option injection as well as shell injection: `rg -n "subprocess|\['git'|git clone|--depth|--branch" src tests` and verify attacker-controlled argv data cannot start with `-` unless a `--` delimiter or explicit validation closes the path.
- For path-resolution flows, compare post-`resolve()` containment checks across neighboring seams instead of reviewing existence checks in isolation.

## Ownership And Boundary Probes

- `rg -n "from prism\.scanner_plugins|import prism\.scanner_plugins|DEFAULT_PLUGIN_REGISTRY|DIContainer\(" src tests`
- `rg -n "__all__|from .* import _|import .*\._" src`
- For public API/CLI modules, list the exported symbol and whether it is a supported public contract or internal assembly detail.
- For repo-scoped user inputs, verify the resolved target stays under the intended root after path joining: `rg -n "repo_role_path|repo_style_readme_path|resolve\(|relative_to\(|path_safety" src/prism/repo_services.py src/prism/api.py src/prism/cli.py`

## Graph And Composition Probes

- From the graph slice, enumerate composition candidates, registry origins, resolver consumers, and facade edges before source reads.
- Verify each split-authority candidate with two locations: origin line and downstream consumer line.
- For type-only import candidates, state whether moving to `TYPE_CHECKING` would preserve runtime behavior.
- When one path-resolution seam already enforces a root-boundary guard, inspect adjacent seams that resolve sibling inputs and verify they enforce the same containment rule instead of assuming the safeguard is shared.

## Test Gap Probes

- For each authoritative module touched by a finding class, check for direct tests, DI override tests, and boundary guard tests.
- Do not flag a generic test gap only because coverage is absent; tie it to a concrete behavior or contract that lacks direct proof.

## Observation Quality Rules

- `confidence: high` requires live-source evidence and a concrete failure mode.
- `confidence: medium` is valid when the code smell is confirmed but impact needs grading.
- `confidence: low` belongs in raw observations only when it helps synthesis; do not promote it directly.
- A high-severity observation needs either runtime risk, public contract risk, data-loss risk, or architecture-boundary risk.
