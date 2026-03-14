# Contributing

Thank you for considering contributing to ansible_role_doc!

This file contains short, practical guidelines to make contributions smooth and
helpful for everyone. If you're unsure about anything, open an issue or a draft
pull request and we'll help.

## Where to start

- Look for existing issues before opening a new one. If you find a bug, please
  include the steps to reproduce, observed behavior, and expected behavior.
- For new features, open an issue first to discuss scope and design.

## Code of conduct

Be respectful and inclusive in all interactions. If you need to report
unacceptable behavior, open a private issue or contact the maintainers.

## Development setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   ```

2. Install development dependencies:

   ```bash
   pip install -r requirements-dev.txt
   pip install -e .[dev]
   ```

3. Run tests locally:

   ```bash
   pytest -q
   # or using Makefile.pod targets
   make test
   ```

4. Run tox for full checks and a mock output preview:

  ```bash
  tox
  ```

  This also generates `debug_readmes/REVIEW_README.md` from the mock role so
  you can quickly review rendered output. The folder is gitignored.

## Linting and formatting

- We use `ruff`, `black`, and `pylint` alongside `pre-commit` hooks.
- In pull requests, Ruff findings are published by reviewdog as a PR check (`github-pr-check`) at warning level.
- Before submitting a PR, run:

  ```bash
  ruff check .
  black .
  pylint src/ansible_role_doc tests || true
  pre-commit run --all-files || true
  ```

## Branch & commit conventions

- Create a descriptive branch from `main`, e.g. `fix/readme-typo` or
  `feat/add-formatter`.
- Keep commits focused and atomic. Use conventional-style messages like
  `fix:`, `feat:`, `chore:`, `docs:`.

## Pull request checklist

- [ ] Branch from `main` with a descriptive name
- [ ] Write tests for new features / bug fixes
- [ ] Run linters and formatters; fix reported issues
- [ ] Update documentation or templates if relevant
- [ ] Add a clear title and description explaining the why and what

## Writing good issues / PR descriptions

- Provide a clear summary of the problem or feature request.
- Include steps to reproduce, expected vs. actual behavior, and minimal
  examples if possible.
- For PRs, explain design decisions and link related issues.

## Maintainers

Maintainers will review contributions and may request changes. Small PRs are
typically merged quickly; larger proposals may be discussed first.

Thanks again for contributing — your help makes this project better!
