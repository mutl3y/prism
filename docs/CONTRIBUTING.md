# Contributing

Thank you for considering contributing to prism!

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

4. Run tox for full checks:

  ```bash
  tox
  ```

5. Optionally generate demo README outputs:

  ```bash
  tox -e readmes
  ```

  This writes demo artifacts under `debug_readmes/` (gitignored).

## Linting and formatting

- We use `ruff`, `black`, and `pylint` alongside `pre-commit` hooks.
- In pull requests, Ruff findings are published by reviewdog as a PR check (`github-pr-check`) at warning level.
- Before submitting a PR, run:

  ```bash
  ruff check .
  black .
  pylint src/prism tests || true
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

## Release process (changelog)

- Keep release notes in `CHANGELOG.md` only.
- Add user-visible changes under `## [Unreleased]` in one of: `Added`, `Changed`, `Fixed`, `Removed`, `Deprecated`, or `Security`.
- For a release, move relevant `Unreleased` entries to a new version section:

  ```markdown
  ## [0.1.1] - YYYY-MM-DD
  ```

- Update link references at the bottom of `CHANGELOG.md` so:
  - `[Unreleased]` compares from the new tag to `HEAD`
  - `[0.1.1]` points to the new release tag URL

## Writing good issues / PR descriptions

- Provide a clear summary of the problem or feature request.
- Include steps to reproduce, expected vs. actual behavior, and minimal
  examples if possible.
- For PRs, explain design decisions and link related issues.

## Maintainers

Maintainers will review contributions and may request changes. Small PRs are
typically merged quickly; larger proposals may be discussed first.

Thanks again for contributing — your help makes this project better!
