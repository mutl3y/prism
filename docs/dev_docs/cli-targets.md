# CLI Targets

Primary Prism CLI targets and when to use each one.

## Target Model

`prism` is organized around explicit subcommand targets:

- `role`
- `collection`
- `repo`
- `completion`

## Target Matrix

| Target | Primary Input | Primary Output | Best Use |
| --- | --- | --- | --- |
| `role` | local role directory | role README, optional runbook artifacts | authoring and review |
| `collection` | local collection root | collection docs + plugin inventory | portfolio documentation |
| `repo` | remote Git source + role path | generated docs from repository source | remote validation and intake |
| `completion` | shell type | completion script | local CLI ergonomics |

## Target: role

Use when scanning a local role directory.

Example:

```bash
prism role path/to/role -o README.md
```

Common advanced options:

- `--detailed-catalog`
- `--runbook-output RUNBOOK.md`
- `--runbook-csv-output RUNBOOK.csv`
- `--fail-on-unconstrained-dynamic-includes`
- `--fail-on-yaml-like-task-annotations`

## Target: collection

Use when scanning a local collection root with `galaxy.yml` and `roles/`.

Example:

```bash
prism collection path/to/collection -f md -o COLLECTION_DOCS.md
```

Common advanced options:

- `--detailed-catalog`
- `--runbook-output <directory>`
- `--runbook-csv-output <directory>`
- `--feedback-from-learn <file-or-url>`

## Target: repo

Use when scanning a role path from a repository source.

Example:

```bash
prism repo --repo-url https://github.com/org/repo --repo-role-path . -o README.md
```

Common advanced options:

- `--repo-ref <branch-or-tag>`
- `--repo-timeout <seconds>`
- `--repo-style-readme-path <path>`
- `--feedback-from-learn <file-or-url>`

## Target: completion

Use when generating shell completion from the live parser.

Example:

```bash
prism completion bash
```

## Output Strategy by Target

- role: author-facing README + optional runbook artifacts
- collection: portfolio-level documentation + plugin inventory
- repo: remote source validation and review docs
- completion: shell UX support for local workflows
