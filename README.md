# Prism: Your Automation's Living Documentation

Project site: [mutl3y.github.io/prism](https://mutl3y.github.io/prism)
[![CI](https://github.com/mutl3y/prism/actions/workflows/prism.yml/badge.svg?branch=main)](https://github.com/mutl3y/prism/actions/workflows/prism.yml) [![Branch](https://img.shields.io/github/actions/workflow/status/mutl3y/prism/prism.yml?branch=main&label=main)](https://github.com/mutl3y/prism/tree/main) [![Coverage](https://raw.githubusercontent.com/mutl3y/prism/badges/.github/badges/coverage.svg)](docs/dev_docs/completed-plans.md) [![Python](https://img.shields.io/badge/python-3.14-blue)](pyproject.toml) [![License](https://img.shields.io/github/license/mutl3y/prism)](LICENSE)

**From code to knowledge: automatically generate accurate, operator-friendly documentation for Ansible roles, collections, and repositories.**

---

Ansible is the source of truth for your infrastructure, but its documentation is often the first source of technical debt. Manually written READMEs quickly become stale, making roles hard to reuse, difficult to onboard new team members, and risky to operate during incidents.

**Prism treats documentation as code.** It performs static analysis on Ansible content to generate accurate, operator-friendly documentation that stays aligned with source.

## ✨ Key Features

Prism goes beyond variable lists and captures operational context from the same source files your automation runs.

### Intelligently Adapts to Your Style

**Problem:** Most doc generators force a rigid template.

**Prism's solution:** Through `prism-learn` experimentation, GitHub Models were used to categorize section titles across more than 37,000 real-world roles. Prism recognizes common conventions, detects existing section headers (like `Usage`, `Example Playbook`, or `Role Variables`), and injects generated content while preserving hand-written prose.

### 🤖 From Code to Crisis: Automated Runbooks

**Problem:** When automation fails, operators need a procedure, not just code.

**Prism's solution:** Add marker comments like `# prism~runbook: ...`, `# prism~warning: ...`, and `# prism~note: ...` to tasks for human-centric guidance. Prism extracts these directives and produces a clear, ordered runbook.

Marker guidance: keep annotation payloads as plain text or compact `key=value` hints (for example `owner=platform impact=high`). Do not embed YAML structures in marker comments.

Valid compact examples:

- `# prism~runbook: owner=platform impact=high`
- `# prism~warning: rollback=manual timeout=300s`

Example snippet:

```yaml
# prism~runbook: Before proceeding, ensure no active transactions are in the message queue.
# prism~warning: Draining may take up to 5 minutes on large backlogs.
# prism~note: Use mq-status --check to verify queue health.
- name: Stop the primary application service
  ansible.builtin.service:
    name: my-app
    state: stopped
```

### 🌐 Fleet-Wide Governance with `prism-learn`

**Problem:** You cannot manage what you cannot measure.

**Prism's solution:** Prism exports structured metadata across your automation fleet. The companion project, [`prism-learn`](https://github.com/mutl3y/prism-learn), ingests that data to report on documentation quality, complexity hotspots, and dependency risk.

## 🚀 Quick Start

1. Install Prism: `pip install prism-ansible`
2. Move into your Ansible project: `cd /path/to/your/ansible-project`
3. Run Prism against a role: `prism role roles/my-webserver-role`
4. Review the generated role README.

## Command-Line Usage

- Scan a role: `prism role <path/to/role>`
- Scan a collection: `prism collection <path/to/collection>`
- Scan a repository role: `prism repo --repo-url <git-url> [--repo-role-path <path/in/repo>]`

Run `prism --help` for the full command and option list.

## ⚙️ CI/CD Integration: Keep Docs Fresh Automatically

Prism is designed to run in CI/CD so generated docs stay in sync with source.

Typical workflow:

1. Install `prism-ansible` in the pipeline job.
2. Run `prism role ...` or `prism repo --repo-url ...` during validation.
3. Commit or publish generated docs as part of your docs workflow.

## 🔧 Configuration

Create a `.prism.yml` file in the target repo or role root to tune behavior.

Example:

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
markers:
  prefix: prism
scan:
  fail_on_yaml_like_task_annotations: false
```

To enforce strict annotation payload hygiene in CI, set `scan.fail_on_yaml_like_task_annotations: true` or pass `--fail-on-yaml-like-task-annotations` on the CLI.

Marker prefix rules:

- Default prefix: `prism`
- Allowed pattern: `[A-Za-z0-9_.-]+`
- Allowed characters: letters, numbers, `_`, `.`, `-`

## Technical Documentation

Most deep technical material now lives in `docs/`:

- `docs/CHANGELOG.md`
- `docs/changelog.md`
- `docs/prism-friendly-role-authoring.md`
- `docs/dev_docs/static-analysis-scope.md`
- `docs/dev_docs/roadmap.md`
- `docs/dev_docs/style-guide-sources.md`
- `docs/dev_docs/ci-starter-workflows.md`

## 🌱 Contributing

Contributions are welcome. See `docs/dev_docs/contributing.md`.

## 📄 License

Prism is licensed under the [Apache License 2.0](LICENSE).
