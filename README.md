ansible-role-doc
=================

[![CI](https://github.com/mutl3y/ansible_role_doc/actions/workflows/default.yml/badge.svg?branch=main)](https://github.com/mutl3y/ansible_role_doc/actions/workflows/default.yml)
[![Branch](https://img.shields.io/github/actions/workflow/status/mutl3y/ansible_role_doc/default.yml?branch=main&label=main)](https://github.com/mutl3y/ansible_role_doc/tree/main)
[![Coverage](https://img.shields.io/badge/coverage-86.6%25-brightgreen)](COVERAGE_WORKOFF_PLAN.md)
[![Python](https://img.shields.io/badge/python-3.14-blue)](pyproject.toml)
[![License](https://img.shields.io/github/license/mutl3y/ansible_role_doc)](LICENSE)

Scan an Ansible role for Jinja2 `default()` usages and generate README documentation.

Usage:

- Install: pip install -e .
- Run: ansible-role-doc path/to/role -o output.md
- Compare against local baseline: ansible-role-doc path/to/role --compare-role-path path/to/baseline -o debug_readmes/REVIEW_README_COMPARE.md
- Reuse an existing README as a style guide: `ansible-role-doc path/to/role --style-readme path/to/README.md -o debug_readmes/REVIEW_README_STYLED.md`
- Live repo test: `python -m ansible_role_doc.cli --repo-url https://github.com/mutl3y/ansible_port_listener -o debug_readmes/REVIEW_README_PORT_LISTENER.md -v`
- Use a README inside a cloned repo as a guide: `python -m ansible_role_doc.cli --repo-url https://github.com/mutl3y/ansible_port_listener --repo-style-readme-path README.md -o debug_readmes/REVIEW_README_PORT_LISTENER_STYLED.md -v`

When a style guide README is used, comparison artifacts are saved beside the generated output:

- source guide copy: `style_<source>/SOURCE_STYLE_GUIDE.md`
- generated demo copy: `style_<source>/DEMO_GENERATED.md`

Current style-guide behavior:

- Guide section order and heading style are preserved where possible.
- Common guide sections such as role variables, examples, local testing, FAQ/pitfalls, contributing, sponsors, and license/author are mapped to generated content.
- Variable sections now adapt to the source README style, including YAML-block and nested-bullet variable formats.

Testing note:

- Running `tox` now also runs coverage and writes `debug_readmes/coverage.xml` alongside `debug_readmes/REVIEW_README.md` for quick mock-role output review.
- `debug_readmes/` is ignored by git.
- Coverage gaps and the staged workoff plan are tracked in `COVERAGE_WORKOFF_PLAN.md`.

Review note:

- `debug_readmes/STYLE_GUIDE_REVIEW_SUMMARY.md` indexes the current generated comparison set.
- Mock-role comparison demos currently exist for Docker and SSH hardening guide styles.

Roadmap:

- See `TODO.md` for planned enhancements (richer mock role realism, local-role comparison, and GitHub source intake for README generation).
- See `STYLE_GUIDE_SOURCES.md` for candidate README source repositories to use as style guides during review.

<- hosts: reviewdog test -->

<- hosts: reviewdog verify -->

<- hosts: reviewdog retry -->
