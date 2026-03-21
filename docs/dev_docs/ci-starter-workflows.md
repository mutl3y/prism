# CI Starter Workflows

Starter usage patterns for running Prism in CI.

## GitHub Actions Pattern

- install package
- run role or collection scan
- publish generated docs as artifacts
- fail build on policy violations

## GitLab Pattern

```yaml
stages:
  - docs

prism:
  stage: docs
  image: python:3.11
  script:
    - python -m pip install --upgrade pip
    - pip install -e .
    - prism role src/prism/tests/roles/enhanced_mock_role --fail-on-yaml-like-task-annotations -o README.generated.md
  artifacts:
    paths:
      - README.generated.md
```
