# CI Starter Workflows

Use these starter examples to run `prism` in CI.

## GitHub Actions

A starter workflow is available at:

- `.github/workflows/prism.yml`

It installs the package in editable mode, runs a sample role scan, and uploads the generated README as an artifact.

## GitLab CI

Add this job to `.gitlab-ci.yml`:

```yaml
stages:
  - docs

prism:
  stage: docs
  image: python:3.11
  script:
    - python -m pip install --upgrade pip
    - pip install -e .
    - prism src/prism/tests/roles/enhanced_mock_role -o README.generated.md
  artifacts:
    paths:
      - README.generated.md
```

## Notes

- Use `--collection-root -f md` to generate collection-level docs with per-role markdown files.
- Use `-f pdf` only when the `weasyprint` dependency is installed in your CI environment.
