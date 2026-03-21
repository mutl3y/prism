---
layout: default
title: Feedback Integration
---

Use external recommendation payloads from prism-learn to tune scan behavior.

This closes the loop between local scans and organization-wide guidance.

## Input Modes

- local file: `--feedback-from-learn /path/to/feedback.json`
- API endpoint: `--feedback-from-learn https://learn.example.com/api/feedback?role=my_role`

## Lane Notes

Average user lane:

- use local-file feedback during experimentation
- keep recommendation sets small and explicit

DevOps lane:

- use API-backed feedback in CI
- validate endpoint availability before policy-gated runs
- use recurring feedback snapshots to standardize quality across teams

## Role Example

```bash
prism role path/to/role --feedback-from-learn /path/to/feedback.json -o README.md
```

## Collection Example

```bash
prism collection path/to/collection --feedback-from-learn /path/to/feedback.json -f md -o COLLECTION_DOCS.md
```

## Repo Example

```bash
prism repo --repo-url https://github.com/org/repo --feedback-from-learn /path/to/feedback.json -o README.md
```

## Behavior and Errors

- reachable + valid payload: recommendations may override relevant scan settings
- missing file, unreachable URL, malformed payload: scan exits with a clear error

## Governance Outcome

With consistent feedback ingestion, teams can move from one-off fixes to managed
quality programs backed by measurable trends.

## Minimal Schema Example

```json
{
  "version": "1.0",
  "generated_at": "2026-03-19T18:00:00Z",
  "recommendations": [
    {
      "type": "check_collection_compliance",
      "display": true,
      "reason": "Collection declaration gaps exceed baseline"
    }
  ],
  "summary": "Collection compliance checks should be enabled."
}
```
