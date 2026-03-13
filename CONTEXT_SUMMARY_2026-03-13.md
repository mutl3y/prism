# Context Summary — 2026-03-13

This file captures the current project state so work can be resumed later without reconstructing context from chat history.

## Current project state

The project now supports:

- scanning local Ansible roles
- scanning roles from GitHub repositories via `--repo-url`
- SSH-based GitHub cloning with non-interactive behavior and timeout protection
- recursive task include discovery for `include_tasks` / `import_tasks`
- richer inferred README sections (purpose, capabilities, variable summary, task summary, example usage)
- local baseline comparison via `--compare-role-path`
- README style-guide support from:
  - a local README (`--style-readme`)
  - a README inside a cloned repo (`--repo-style-readme-path`)
- style-aware rendering for role variables, including:
  - YAML-block variable sections
  - nested-bullet variable sections with default/description bullets
- saved style comparison artifacts in source-specific folders under `debug_readmes/`
- CI-generated coverage badge updates on push (`.github/badges/coverage.svg`)
- centralized debug artifact cleanup via `make clean-demo-readmes` (also used by `tox`)

## Key files changed over the session

- `src/ansible_role_doc/cli.py`
- `src/ansible_role_doc/scanner.py`
- `src/ansible_role_doc/templates/README.md.j2`
- `src/ansible_role_doc/tests/test_cli_repo.py`
- `src/ansible_role_doc/tests/test_render_readme.py`
- `README.md`
- `.github/workflows/default.yml`
- `.github/badges/coverage.svg`
- `Makefile.pod`
- `tox.ini`
- `TODO.md`
- `STYLE_GUIDE_SOURCES.md`

## Current debug/review layout

Current review artifacts are in `debug_readmes/`.

Important files:

- `debug_readmes/REVIEW_README.md` — mock-role baseline output
- `debug_readmes/REVIEW_README_MOCK_STYLED_FROM_DOCKER.md` — mock role rendered using Docker guide style
- `debug_readmes/REVIEW_README_MOCK_STYLED_FROM_DEVSEC.md` — mock role rendered using SSH hardening guide style
- `debug_readmes/REVIEW_README_GEERLINGGUY_DOCKER_STYLED.md` — live Docker repo styled output
- `debug_readmes/REVIEW_README_DEVSEC_SSH_HARDENING_STYLED.md` — live SSH hardening repo styled output
- `debug_readmes/STYLE_GUIDE_REVIEW_SUMMARY.md` — comparison index

Style folders:

- `debug_readmes/style_ansible_role_docker/`
  - `SOURCE_STYLE_GUIDE.md`
  - `DEMO_GENERATED.md`
- `debug_readmes/style_ansible_ssh_hardening/`
  - `SOURCE_STYLE_GUIDE.md`
  - `DEMO_GENERATED.md`

## Current style-guide behavior

Implemented:

- preserves guide section order when headings are recognized
- preserves heading style (`#` vs setext)
- maps common sections including:
  - requirements / dependencies
  - role variables
  - example playbook / usage
  - local testing
  - FAQ / pitfalls
  - contributing
  - sponsors
  - license / author information
- uses repo name fallback for cloned repos if role metadata is weak
- saves guide/demo comparison artifacts under source-named folders

Known limitation:

- generated output still does not fully reproduce the prose density or hand-written narrative style of source READMEs
- style fidelity is structural and format-aware, not full prose mimicry

## Current validation state

Recent focused validations succeeded:

- `pytest -q src/ansible_role_doc/tests/test_cli_repo.py src/ansible_role_doc/tests/test_render_readme.py`
- result: 15 passing tests during the latest style-aware rendering work

Most recent full-suite status:

- `tox` passing with 57 tests
- coverage report generated at `debug_readmes/coverage.xml`
- recent reported total coverage: 86.6% (scanner-heavy remaining gaps)

Earlier full `tox` runs were also passing before the latest documentation-only updates.

## Current roadmap status

Completed recently:

- style-guide support
- section mapping improvements
- variable style matching
- style-source folder organization for generated comparison artifacts
- mock-role demos from multiple saved style guides

Open next-step items from `TODO.md`:

1. expand mock role realism further
2. revisit variable discovery for GitHub-scanned roles where defaults/vars are sparse or indirect
3. refine style-guide fidelity further where source README structure and generated output still differ
4. later-phase learning loop work (snapshots, metrics, optional feedback loop)

## Recommended next actions

Most logical next step:

- revisit variable discovery for GitHub-scanned roles

Suggested focus areas:

- detect variables referenced in task files even when not declared in `defaults/main.yml` or `vars/main.yml`
- inspect `include_vars` usage and additional vars files
- optionally mine existing README variable sections as hints (without treating them as source of truth)

Alternative next step:

- refine style fidelity for source-specific prose patterns in the variable and example sections

Operational note for next session:

- If generated review artifacts are noisy, run `make -f Makefile.pod clean-demo-readmes` first.
- Coverage badge auto-updates in CI from `debug_readmes/coverage.xml` and commits `.github/badges/coverage.svg` on push events.

## Notes about user intent

The user wants:

- practical side-by-side review outputs
- a clear debug artifact structure
- the ability to pause and resume work later
- more accurate source-style matching, especially for variable sections
- a later revisit of sparse variable discovery for GitHub roles
