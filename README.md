ansible-role-doc
=================

[![CI](https://github.com/mutl3y/ansible_role_doc/actions/workflows/default.yml/badge.svg?branch=main)](https://github.com/mutl3y/ansible_role_doc/actions/workflows/default.yml)
[![Branch](https://img.shields.io/github/actions/workflow/status/mutl3y/ansible_role_doc/default.yml?branch=main&label=main)](https://github.com/mutl3y/ansible_role_doc/tree/main)
[![Coverage](https://raw.githubusercontent.com/mutl3y/ansible_role_doc/badges/.github/badges/coverage.svg)](COVERAGE_WORKOFF_PLAN.md)
[![Python](https://img.shields.io/badge/python-3.14-blue)](pyproject.toml)
[![License](https://img.shields.io/github/license/mutl3y/ansible_role_doc)](LICENSE)

Generate README documentation for Ansible roles from local paths or repository sources.

Release history is tracked in `CHANGELOG.md`.

Summary
-------

`ansible-role-doc` scans role structure, tasks, handlers, metadata, and variables, then renders a consistent README from templates.

- Supports local role paths and `--repo-url` inputs.
- Repo scans now opportunistically use sparse/partial clone for sub-path targets and fall back to shallow clone when sparse checkout is unavailable.
- Can reuse an existing README as a style guide with section/order preservation.
- Can generate headings-only style skeletons with `--create-style-guide`.
- Variable sourcing defaults to `defaults-only` (or use `--variable-sources defaults+vars`).

Scan scope (current)
--------------------

Current scanning is static and file-based. The tool currently focuses on these sources/signals:

- Role structure and conventional paths (`tasks/`, `handlers/`, `templates/`, `defaults/`, `vars/`, `meta/`, tests).
- Variables from defaults-focused discovery (and optional vars discovery via `--variable-sources defaults+vars`).
- Static task includes and selected `include_vars`/`set_fact` patterns where they can be resolved deterministically.
- Jinja2 AST-assisted detection for `default(...)` usage and undeclared template variable references, with regex fallback for malformed or unsupported expressions.
- README-input discovery for documented variables in role README variable/input sections (including markdown tables and list formats).
- Style-guide-driven rendering when `--style-readme` or `--repo-style-readme-path` is provided.

Known limitations
-----------------

- Variable discovery is intentionally conservative and can miss values defined outside scanned defaults/vars patterns (for example dynamic `include_vars`, complex `set_fact`, role parameters, or precedence-driven overrides).
- Template analysis is moving toward Jinja2 AST parsing, but it still cannot fully resolve values that come from runtime includes, dynamic file loads, or variables computed only at execution time.
- Static analysis still merges role sources such as `defaults/` and `vars/`, but some values must remain documented as unknown or runtime-derived when provenance cannot be resolved statically.
- Complex computed defaults may not reduce cleanly to a literal value; in those cases generated docs may show the expression itself or treat it as a non-literal default.
- Generated docs can be incomplete when variable provenance is ambiguous or conditional defaults are difficult to resolve statically.
- Edge cases still include role dependencies, variable precedence interactions, templated filenames, and dynamic include paths.

Priority improvements planned
-----------------------------

- Expand Jinja2 AST coverage beyond the current default-filter and undeclared-variable paths (for example macros, custom filters/tests, and more complex control flow).
- Expand variable/source coverage for `defaults/`, `vars/`, `meta/`, and simple `set_fact`/`include_vars` detection with provenance markers.
- Add broader integration fixtures using realistic sample roles to validate real-world coverage and avoid regressions.
- Extend CLI ergonomics with additional discovery/report controls (remaining focus: exclusions).

Usage:

- Install: pip install -e .
- Run: ansible-role-doc path/to/role -o output.md
- Compare against local baseline (optional review/testing mode, not default generation): ansible-role-doc path/to/role --compare-role-path path/to/baseline -o debug_readmes/REVIEW_README_COMPARE.md
- Reuse an existing README as a style guide: `ansible-role-doc path/to/role --style-readme path/to/README.md -o debug_readmes/REVIEW_README_STYLED.md`
- Live repo test: `python -m ansible_role_doc.cli --repo-url https://github.com/mutl3y/ansible_port_listener -o debug_readmes/REVIEW_README_PORT_LISTENER.md -v`
- Use a README inside a cloned repo as a guide: `python -m ansible_role_doc.cli --repo-url https://github.com/mutl3y/ansible_port_listener --repo-style-readme-path README.md -o debug_readmes/REVIEW_README_PORT_LISTENER_STYLED.md -v`
- Generate a style-guide skeleton (section order/headings only): `ansible-role-doc path/to/role --create-style-guide -o debug_readmes/REVIEW_README_SKELETON.md`

Library API:

- `ansible-role-doc` can also be used as a scanner library by external orchestration code.
- This repo should remain the scanner/render engine; high-volume learning-loop orchestration can live in a separate app that imports the public API wrapper.
- Prefer `ansible_role_doc.api.scan_role(...)` and `ansible_role_doc.api.scan_repo(...)` instead of importing internal helpers directly.

Example:

```python
from ansible_role_doc.api import scan_role

payload = scan_role(
    "/path/to/role",
    exclude_path_patterns=["tests/**", "molecule/**"],
)

print(payload["role_name"])
print(payload["metadata"]["scanner_counters"])
```

The wrapper returns the same machine-readable scan payload used by JSON output mode, but as a Python dictionary and without writing files.

Repo example:

```python
from ansible_role_doc.api import scan_repo

payload = scan_repo(
	"https://github.com/example/role.git",
	repo_role_path="roles/demo",
	repo_style_readme_path="README.md",
)
```

For a minimal orchestration-side persistence example, see [src/learning_app_scaffold/README.md](src/learning_app_scaffold/README.md).

Local containerized learning-loop setup (Podman + PostgreSQL, with `pg_dump` checkpoints) is documented in [docs/podman-postgres-local.md](docs/podman-postgres-local.md).

CLI capabilities (today):

- Verbose logging: `-v` / `--verbose`
- Output formats: `--format md|html|json`
- Preview without writes: `--dry-run` (prints rendered output to stdout)
- Scanner detail output: `--concise-readme`, `--scanner-report-output`
- Local baseline comparison is opt-in only via `--compare-role-path`.
- Unmapped style-guide sections are kept by default; use `--no-keep-unknown-style-sections` to suppress them.

When a style guide README is used, comparison artifacts are saved beside the generated output:

- source guide copy: `style_<source>/SOURCE_STYLE_GUIDE.md`
- generated demo copy: `style_<source>/DEMO_GENERATED.md`
- generated keep-unknown demo copy: `style_<source>/DEMO_GENERATED_KEEP_UNKNOWN.md`
- captured/source-of-truth config sidecar: `style_<source>/ROLE_README_CONFIG.yml`

`ROLE_README_CONFIG.yml` behavior:

- If the role already has `.ansible_role_doc.yml`, that config is copied beside demo artifacts.
- If no role config exists, the sidecar is synthesized from unknown style headings in the source guide.
- Captured content includes `readme.capture_metadata` fields:
	- `schema_version`
	- `captured_at_utc`
	- `style_source_path`
	- `truncated`
- Guardrails apply to synthesized captures:
	- obvious secret-like tokens are redacted (for example password/token/api-key assignments and bearer tokens)
	- per-section and total capture size limits are enforced
	- entries are deduplicated and sorted for deterministic output
	- unchanged sidecars are not rewritten

Current style-guide behavior:

- Guide section order and heading style are preserved where possible.
- `--create-style-guide` generates section headings/order only (no generated section bodies) for iterative style-guide evolution.
- README config section selection is independent from heading renaming. Use `--adopt-style-headings` or `readme.adopt_style_headings: true` to render config-provided section labels such as `Capabilities` instead of canonical headings such as `Role purpose and capabilities`.
- README config can control how each section body is handled via `readme.section_content_modes` with per-section modes:
	- `generate`: use scanner-generated section content only
	- `replace`: use style-guide/source section body text only
	- `merge`: combine source section text and generated output
- `readme.section_content_modes` keys are resolved first against section labels used in `readme.include_sections`, then against aliases/canonical section ids.
- Merge mode is idempotent for repeated ingest/re-render passes: generated merge payloads are replaced in-place using hidden markers instead of appended repeatedly.
- Unknown style sections preserve source body text when present, with a fallback placeholder only when the source section body is empty.
- Skeleton style source precedence is: explicit `--style-readme` path, then `$ANSIBLE_ROLE_DOC_STYLE_SOURCE`, then `./STYLE_GUIDE_SOURCE.md`, then `$XDG_DATA_HOME/ansible-role-doc/STYLE_GUIDE_SOURCE.md` (or `~/.local/share/ansible-role-doc/STYLE_GUIDE_SOURCE.md`), then `/var/lib/ansible-role-doc/STYLE_GUIDE_SOURCE.md`, then bundled package `templates/STYLE_GUIDE_SOURCE.md`.
- Common guide sections such as role variables, examples, local testing, FAQ/pitfalls, contributing, sponsors, and license/author are mapped to generated content.
- License and author values are always taken from scanned role metadata (`meta/main.yml`) when available, even when style-guide body text differs.
- Variable sections now adapt to the source README style, including YAML-block and nested-bullet variable formats.
- Variable sections now adapt to source README styles including YAML blocks, nested bullets, and markdown tables.
- Pattern policy config merge order is: bundled package defaults, then `/var/lib/ansible-role-doc/.ansible_role_doc_patterns.yml`, then `$XDG_DATA_HOME/ansible-role-doc/.ansible_role_doc_patterns.yml` (or `~/.local/share/ansible-role-doc/.ansible_role_doc_patterns.yml`), then optional `./.ansible_role_doc_patterns.yml`, then optional `$ANSIBLE_ROLE_DOC_PATTERNS_PATH`, then explicit override path if supplied.

README config example:

```yaml
readme:
	adopt_style_headings: true
	include_sections:
		- Capabilities
		- Inputs / variables summary
		- Requirements
	section_content_modes:
		Requirements: merge
		Inputs / variables summary: generate
```

Testing note:

- Running `tox` (default `py` env) runs tests with coverage and writes `debug_readmes/coverage.xml`.
- Latest local snapshot (2026-03-15): `176 passed` with total coverage `82.56%`.
- Generate review outputs on demand with `tox -e readmes` (or `tox -e py,readmes`), which writes:
	- `debug_readmes/REVIEW_README.md`
	- `debug_readmes/REVIEW_README.html`
	- `debug_readmes/REVIEW_README.json`
	- `debug_readmes/REVIEW_README_CONCISE.md` and `debug_readmes/SCAN_REPORT.md`
	- `debug_readmes/REVIEW_README_STYLE_GUIDE_SKELETON.md`
	- `debug_readmes/REVIEW_README_INROLE_CONFIG.md`
- `debug_readmes/` is ignored by git.
- Coverage gaps and the staged workoff plan are tracked in `COVERAGE_WORKOFF_PLAN.md`.

CI note:

- Ruff annotations are published by reviewdog only on pull request events.
- Annotations are reported as a PR check (`github-pr-check`) with warning-level findings.
- Coverage badge updates are written to the dedicated `badges` branch via GitHub API calls from CI (avoids protected-branch direct pushes to `main`).

Learning batch note:

- Repository batch scans can be run with `scripts/learning_repo_batch.py` and persisted via the scaffold Postgres store.
- Freshness skipping is enabled by default (`--skip-if-fresh-days 7`); use `--force-rescan` to scan all provided URLs.
- Latest wide sample batch run label: `sample12-20260315-193723` with `12/12` successful repo scans.

Review note:

- `debug_readmes/STYLE_GUIDE_REVIEW_SUMMARY.md` indexes the current generated comparison set.
- `debug_readmes/STYLE_MISSED_SECTIONS_REPORT.md` lists unmapped style-guide headings from the latest sample repo pass.
- Current sample-repo matrix validates end-to-end generation across the configured six style sources.

Roadmap:

- See `TODO.md` for planned enhancements and remaining gaps (richer mock role realism, iterative learning-loop persistence/metrics, and further style-fidelity reductions).
- Current roadmap also tracks follow-up phases for mutable Linux-host data locations (for example XDG user data and system-level paths).
- See `STYLE_GUIDE_SOURCES.md` for candidate README source repositories to use as style guides during review.

<- hosts: reviewdog test -->

<- hosts: reviewdog verify -->

<- hosts: reviewdog retry -->
