# Skills

This folder contains project-level Copilot skills for repeatable workflows.

## When To Use Which Skill

- `boost-prompt`: Use when you want to turn a rough request into a precise,
  high-quality prompt before implementation. This skill is prompt-only and
  should not write code.
- `comment-code-generate-a-tutorial`: Use when you want a Python script
  refactored for beginners, with instructional comments and a tutorial-style
  `README.md`.
- `create-llms`: Use when you need to generate or regenerate root `llms.txt`
  from repository structure and documentation.
- `git-commit`: Use when you want help staging logical changes and writing a
  conventional commit message from the actual diff.
- `git-flow-branch-creator`: Use when you need a branch name and branch type
  chosen from current changes using Git Flow conventions.
- `make-repo-contribution`: Use before creating issues, branches, commits, or
  PRs so contribution workflow and templates are checked first.
- `pytest-coverage`: Use when you need to find Python lines missing test
  coverage and add tests systematically.
- `structured-autonomy-implement`: Use when you already have an implementation
  plan and want strict, step-by-step execution without scope drift.
- `structured-autonomy-plan`: Use when you want a research-backed
  implementation plan broken into testable steps and intended commits.
- `suggest-awesome-github-copilot-agents`: Use when you want recommendations
  for additional custom agents from `github/awesome-copilot`, including local
  overlap and outdated-agent detection.
- `suggest-awesome-github-copilot-instructions`: Use when you want
  recommendations for instruction files from `github/awesome-copilot`, with
  duplicate and outdated-file detection.
- `suggest-awesome-github-copilot-skills`: Use when you want recommendations
  for additional skills from `github/awesome-copilot`, including overlap and
  outdated-skill detection.

## Notes

- Some skills assume specific tools or integrations are available. If a skill
  references missing tools in your current environment, adapt the workflow
  rather than forcing unsupported calls.
- Prefer running one skill per request unless you explicitly need a staged
  multi-skill flow.

## Source

Local skills under `.github/skills/` are repository-scoped customizations.
