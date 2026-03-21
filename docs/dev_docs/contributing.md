---
layout: default
title: Contributing
---

Use this workflow when contributing code or docs.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .[dev]
```

## Validation

```bash
pytest -q
tox -q
ruff check .
```

## Pull Request Expectations

- keep changes focused
- add or update tests when behavior changes
- include docs updates for user-visible behavior
- use clear commit prefixes (`feat:`, `fix:`, `docs:`, `chore:`)
