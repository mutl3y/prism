# prism Pipeline Diagram

CLI usage and flags reference.

## Repository split (current)

- `prism` (this repository): scanner and README rendering engine, CLI, style-guide handling, output formats.
- `prism-learn` (optional add-on): learning-loop orchestration, metrics/persistence storage, Postgres + container workflows.

Companion repository:

- https://github.com/mutl3y/prism-learn

If you need long-running batch scans and scan-history analytics, use `prism-learn` on top of `prism-ansible`.

## Quick reference — `prism --help`

```
usage: prism [-h] {role,collection,repo,completion} ...
```

| Command / Flag | Purpose |
|------|---------|
| `role <role_path>` | Scan a local role and render docs |
| `collection <collection_path>` | Scan a local collection root and render collection docs/payload |
| `repo --repo-url <url>` | Clone + scan a repository role source |
| `completion bash` | Generate Bash completion script from the live parser |
| `--compare-role-path` | Optional local baseline role for review/testing comparison reports |
| `--style-readme` | Local README to use as style guide (section order + headings) |
| `--create-style-guide` | Render headings-only skeleton; auto-resolves style source |
| `--vars-context-path` | Preferred: external vars context files/dirs used as non-authoritative hints |
| `--vars-seed` | Backward-compatible alias for `--vars-context-path` |
| `--concise-readme` | Strip scanner-heavy sections; write them to a sidecar |
| `--scanner-report-output` | Custom path for the sidecar report |
| `--no-include-scanner-report-link` | Hide scanner-report link from concise README |
| `--variable-sources` | `defaults-only` (default) or `defaults+vars` |
| `--readme-config` | YAML file controlling section visibility |
| `--adopt-heading-mode` | Heading mode for README config selectors: canonical, style, or popular |
| `--keep-unknown-style-sections` | Keep unmapped style-guide sections (retaining source body when present) |
| `--repo-ref` | Repo command: branch/tag/ref to clone |
| `--repo-role-path` | Repo command: sub-path inside cloned repo |
| `--repo-timeout` | Repo command: clone timeout in seconds (default 60) |
| `--repo-style-readme-path` | Repo command: README inside cloned repo to use as style guide |
| `-o` | Output path |
| `-t` | Custom Jinja2 template path (role/repo) |
| `-f` | Output format (`role`/`repo`: `md|html|json|pdf`, `collection`: `md|json`) |
| `--dry-run` | Print rendered output without writing files |
| `-v` | Verbose output |

Note: top-level invocation without a subcommand is no longer supported; use `role`, `collection`, `repo`, or `completion`.
