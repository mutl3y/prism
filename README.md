Prism
=================

[![CI](https://github.com/mutl3y/prism/actions/workflows/prism.yml/badge.svg?branch=main)](https://github.com/mutl3y/prism/actions/workflows/prism.yml)
[![Branch](https://img.shields.io/github/actions/workflow/status/mutl3y/prism/prism.yml?branch=main&label=main)](https://github.com/mutl3y/prism/tree/main)
[![Coverage](https://raw.githubusercontent.com/mutl3y/prism/badges/.github/badges/coverage.svg)](docs/COVERAGE_WORKOFF_PLAN.md)
[![Python](https://img.shields.io/badge/python-3.14-blue)](pyproject.toml)
[![License](https://img.shields.io/github/license/mutl3y/prism)](LICENSE)

Generate README documentation for Ansible roles from local paths or repository sources.

Release history is tracked in `docs/CHANGELOG.md`.

Summary
-------

`Prism` scans role structure, tasks, handlers, metadata, and variables, then renders a consistent README from templates.

- Supports local role paths and `--repo-url` inputs.
- Supports local collection roots via `--collection-root` with collection-level markdown or JSON output.
- Repo scans now opportunistically use sparse/partial clone for sub-path targets and fall back to shallow clone when sparse checkout is unavailable.
- Can reuse an existing README as a style guide with section/order preservation.
- Can generate headings-only style skeletons with `--create-style-guide`.
- Can append detailed task and handler tables with `--detailed-catalog`.
- Can render PDF output with `--format pdf` when the optional `weasyprint` dependency is installed.
- Variable sourcing defaults to `defaults-only` (or use `--variable-sources defaults+vars`).
- Parses and documents Molecule scenarios found in `molecule/*/molecule.yml`.
- Supports per-role config files (`.prism.yml`) and explicit `--readme-config` / `--policy-config` flags for repeatable configuration.
- Supports custom Jinja2 output templates via `--template` to adapt rendered output without forking the project.

Scan scope (current)
--------------------

Current scanning is static and file-based. The tool currently focuses on these sources/signals:

- Role structure and conventional paths (`tasks/`, `handlers/`, `templates/`, `defaults/`, `vars/`, `meta/`, tests).
- Variables from defaults-focused discovery (and optional vars discovery via `--variable-sources defaults+vars`).
- Static task includes and selected `include_vars`/`set_fact` patterns where they can be resolved deterministically.
- Jinja2 AST-assisted detection for `default(...)` usage and undeclared template variable references, with regex fallback for malformed or unsupported expressions.
- README-input discovery for documented variables in role README variable/input sections (including markdown tables and list formats).
- Style-guide-driven rendering when `--style-readme` or `--repo-style-readme-path` is provided.
- Molecule scenario discovery from `molecule/*/molecule.yml` (driver, verifier, platforms).
- Collection root scanning: iterates `roles/` inside a collection directory, renders per-role docs, and produces a collection-level summary via `--collection-root`.

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
- Expand task/handler parsing to recognise `include_role` and `import_role` directives and trace cross-role dependencies (currently only `include_tasks`/`import_tasks` file paths are followed).

Usage:

- Install core scanner only: pip install -e .
- Install dev tooling: pip install -e .[dev]
- Run: prism path/to/role -o output.md
- Scan a local collection root into collection markdown plus per-role docs: `prism path/to/collection --collection-root --format md -o COLLECTION_README.md`
- Emit a machine-readable collection payload: `prism path/to/collection --collection-root --format json -o collection.json`
- Compare against local baseline (optional review/testing mode, not default generation): prism path/to/role --compare-role-path path/to/baseline -o debug_readmes/REVIEW_README_COMPARE.md
- Reuse an existing README as a style guide: `prism path/to/role --style-readme path/to/README.md -o debug_readmes/REVIEW_README_STYLED.md`
- Include detailed task and handler tables: `prism path/to/role --detailed-catalog -o debug_readmes/REVIEW_README_CATALOG.md`
- Generate PDF output (requires `weasyprint`): `prism path/to/role --format pdf -o debug_readmes/REVIEW_README.pdf`
- Live repo test: `python -m prism.cli --repo-url https://github.com/mutl3y/ansible_port_listener -o debug_readmes/REVIEW_README_PORT_LISTENER.md -v`
- Use a README inside a cloned repo as a guide: `python -m prism.cli --repo-url https://github.com/mutl3y/ansible_port_listener --repo-style-readme-path README.md -o debug_readmes/REVIEW_README_PORT_LISTENER_STYLED.md -v`
- Generate a style-guide skeleton (section order/headings only): `prism path/to/role --create-style-guide -o debug_readmes/REVIEW_README_SKELETON.md`
- Use a per-role config file: place `.prism.yml` in the role root (auto-discovered) or pass `--readme-config path/to/config.yml`
- Use a custom output template: `prism path/to/role --template path/to/README.md.j2 -o output.md`
- Apply a custom pattern policy: `prism path/to/role --policy-config path/to/patterns.yml -o output.md`

Codespaces live demo:

- This repository includes a `.devcontainer/devcontainer.json` configuration for GitHub Codespaces.
- On first create, Codespaces installs dev dependencies with `pip install -e .[dev]`.
- On start, Codespaces runs `bash scripts/codespaces_live_demo.sh --quick` to generate demo artifacts in `debug_readmes/codespaces_demo/`.
- Main demo output: `debug_readmes/codespaces_demo/README.md`
- Optional local preview server:
	- `bash scripts/codespaces_live_demo.sh --serve --port 8000`
	- Then open forwarded port `8000` in Codespaces.

Library API:

- `prism` can also be used as a scanner library by external orchestration code.
- This repo should remain the scanner/render engine; high-volume learning-loop orchestration can live in a separate app that imports the public API wrapper.
- Prefer `prism.api.scan_role(...)`, `prism.api.scan_repo(...)`, and `prism.api.scan_collection(...)` instead of importing internal helpers directly.

Example:

```python
from prism.api import scan_role

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
from prism.api import scan_repo

payload = scan_repo(
	"https://github.com/example/role.git",
	repo_role_path="roles/demo",
	repo_style_readme_path="README.md",
)
```

Collection example:

```python
from prism.api import scan_collection

payload = scan_collection(
	"/path/to/collection",
	include_rendered_readme=True,
)

print(payload["summary"])
print(payload["roles"][0]["role"])
```

Prism-learn add-on
------------------

Learning-loop orchestration, metrics storage, and Postgres-backed batch workflows now live in the optional companion project: [prism-learn](https://github.com/mutl3y/prism-learn).

Use `prism` for core role scanning and README generation.
Use `prism-learn` when you need:

- long-running learning/batch scans
- persistence and reporting over scan history
- local containerized Postgres + worker workflows

`prism-learn` depends on `prism-ansible`, so `prism` remains the scanner/render engine and library API.

CLI capabilities (today):

- Verbose logging: `-v` / `--verbose`
- Output formats: `--format md|html|json|pdf`
- Preview without writes: `--dry-run` (prints rendered output to stdout)
- Scanner detail output: `--concise-readme`, `--scanner-report-output`
- Collection-root scanning: `--collection-root` for local collection markdown or JSON output
- Detailed task/handler tables: `--detailed-catalog`
- Local baseline comparison is opt-in only via `--compare-role-path`.
- Unmapped style-guide sections are kept by default; use `--no-keep-unknown-style-sections` to suppress them.
- PDF output requires the optional `weasyprint` dependency.
- Per-role configuration: auto-discovers `.prism.yml` in the role root; override with `--readme-config`
- Pattern policy overrides: `--policy-config` for custom token/alias/sensitivity rules
- Custom Jinja2 output template: `--template` (falls back to bundled `templates/README.md.j2`)
- Molecule scenario documentation: detected automatically from `molecule/*/molecule.yml`

When a style guide README is used, comparison artifacts are saved beside the generated output:

- source guide copy: `style_<source>/SOURCE_STYLE_GUIDE.md`
- generated demo copy: `style_<source>/DEMO_GENERATED.md`
- generated keep-unknown demo copy: `style_<source>/DEMO_GENERATED_KEEP_UNKNOWN.md`
- captured/source-of-truth config sidecar: `style_<source>/ROLE_README_CONFIG.yml`

`ROLE_README_CONFIG.yml` behavior:

- If the role already has `.prism.yml`, that config is copied beside demo artifacts.
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
- README config section selection is independent from heading rendering mode. Use `--adopt-heading-mode {canonical,style,popular}` or `readme.adopt_heading_mode`.
  - `canonical`: render canonical section titles (default)
  - `style`: render include_sections labels such as `Capabilities`
  - `popular`: render bundled popular display titles from `data/section_display_titles.yml`
- README config can control how each section body is handled via `readme.section_content_modes` with per-section modes:
	- `generate`: use scanner-generated section content only
	- `replace`: use style-guide/source section body text only
	- `merge`: combine source section text and generated output
- `readme.section_content_modes` keys are resolved first against section labels used in `readme.include_sections`, then against aliases/canonical section ids.
- Merge mode is idempotent for repeated ingest/re-render passes: generated merge payloads are replaced in-place using hidden markers instead of appended repeatedly.
- Unknown style sections preserve source body text when present, with a fallback placeholder only when the source section body is empty.
- Skeleton style source precedence is: explicit `--style-readme` path, then `$PRISM_STYLE_SOURCE`, then `./STYLE_GUIDE_SOURCE.md`, then `$XDG_DATA_HOME/prism/STYLE_GUIDE_SOURCE.md` (or `~/.local/share/prism/STYLE_GUIDE_SOURCE.md`), then `/var/lib/prism/STYLE_GUIDE_SOURCE.md`, then bundled package `templates/STYLE_GUIDE_SOURCE.md`.
- Common guide sections such as role variables, examples, local testing, FAQ/pitfalls, contributing, sponsors, and license/author are mapped to generated content.
- License and author values are always taken from scanned role metadata (`meta/main.yml`) when available, even when style-guide body text differs.
- Variable sections now adapt to the source README style, including YAML-block and nested-bullet variable formats.
- Variable sections now adapt to source README styles including YAML blocks, nested bullets, and markdown tables.
- Pattern policy config merge order is: bundled package defaults, then `/var/lib/prism/.prism_patterns.yml`, then `$XDG_DATA_HOME/prism/.prism_patterns.yml` (or `~/.local/share/prism/.prism_patterns.yml`), then optional `./.prism_patterns.yml`, then optional `$PRISM_PATTERNS_PATH`, then explicit override path if supplied.

README config example:

```yaml
readme:
	adopt_heading_mode: style
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
- Latest local snapshot (2026-03-17): `244 passed` with total coverage `85.0%`.
- Generate review outputs on demand with `tox -e readmes` (or `tox -e py,readmes`), which writes:
	- `debug_readmes/REVIEW_README.md`
	- `debug_readmes/REVIEW_README.html`
	- `debug_readmes/REVIEW_README.json`
	- `debug_readmes/REVIEW_README_CONCISE.md` and `debug_readmes/SCAN_REPORT.md`
	- `debug_readmes/REVIEW_README_STYLE_GUIDE_SKELETON.md`
	- `debug_readmes/REVIEW_README_INROLE_CONFIG.md`
- `debug_readmes/` is ignored by git.
- Coverage gaps and the staged workoff plan are tracked in `docs/COVERAGE_WORKOFF_PLAN.md`.

CI note:

- Ruff annotations are published by reviewdog only on pull request events.
- Annotations are reported as a PR check (`github-pr-check`) with warning-level findings.
- Coverage badge updates are written to the dedicated `badges` branch via GitHub API calls from CI (avoids protected-branch direct pushes to `main`).
- Starter docs-generation templates are included in `docs/ci-starter-workflows.md` and `.github/workflows/prism.yml`.

Review note:

- `debug_readmes/STYLE_GUIDE_REVIEW_SUMMARY.md` indexes the current generated comparison set.
- `debug_readmes/STYLE_MISSED_SECTIONS_REPORT.md` lists unmapped style-guide headings from the latest sample repo pass.
- Current sample-repo matrix validates end-to-end generation across the configured six style sources.

Roadmap:

- See `docs/TODO.md` for planned enhancements and remaining gaps (richer mock role realism and further style-fidelity reductions).
- Current roadmap also tracks follow-up phases for mutable Linux-host data locations (for example XDG user data and system-level paths).
- See `docs/STYLE_GUIDE_SOURCES.md` for candidate README source repositories to use as style guides during review.

<- hosts: reviewdog test -->

<- hosts: reviewdog verify -->

<- hosts: reviewdog retry -->
