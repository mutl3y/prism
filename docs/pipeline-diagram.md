# ansible-role-doc Pipeline Diagram

CLI usage and flags reference.

## Quick reference — `ansible-role-doc --help`

```
usage: ansible-role-doc [-h] [--repo-url REPO_URL] [--repo-ref REPO_REF]
                        [--repo-role-path REPO_ROLE_PATH]
                        [--repo-timeout REPO_TIMEOUT]
                        [--compare-role-path COMPARE_ROLE_PATH]
                        [--style-readme STYLE_README] [--create-style-guide]
                        [--repo-style-readme-path REPO_STYLE_README_PATH]
                        [--vars-seed VARS_SEED] [--concise-readme]
                        [--scanner-report-output SCANNER_REPORT_OUTPUT]
                        [--include-scanner-report-link | --no-include-scanner-report-link]
                        [--variable-sources {defaults+vars,defaults-only}]
                        [--readme-config README_CONFIG]
                        [-o OUTPUT] [-t TEMPLATE] [-f {md,html}] [-v]
                        [role_path]
```

| Flag | Purpose |
|------|---------|
| `role_path` | Local role directory to scan |
| `--repo-url` | Clone and scan a remote Git repo instead |
| `--repo-ref` | Branch/tag/ref to clone |
| `--repo-role-path` | Sub-path inside cloned repo |
| `--repo-timeout` | Clone timeout in seconds (default 60) |
| `--repo-style-readme-path` | README inside cloned repo to use as style guide |
| `--compare-role-path` | Local baseline role for comparison report |
| `--style-readme` | Local README to use as style guide (section order + headings) |
| `--create-style-guide` | Render headings-only skeleton; auto-resolves style source |
| `--vars-seed` | Extra vars files/dirs to prime required-variable detection |
| `--concise-readme` | Strip scanner-heavy sections; write them to a sidecar |
| `--scanner-report-output` | Custom path for the sidecar report |
| `--no-include-scanner-report-link` | Hide scanner-report link from concise README |
| `--variable-sources` | `defaults-only` (default) or `defaults+vars` |
| `--readme-config` | YAML file controlling section visibility |
| `-o` | Output README path |
| `-t` | Custom Jinja2 template path |
| `-f` | Output format: `md` (default) or `html` |
| `-v` | Verbose output |
