---
layout: default
title: Scan Performance Baseline 2026-04-04
---

Initial Wave 2.1 local baseline for Prism role scans, captured against stable test-role fixtures.

## Command Workflow

Timing baseline:

```bash
.venv/bin/python scripts/profile_role_scan.py --iterations 3 --profile-fixture comment_driven_demo_role
```

Detailed-catalog spot check:

```bash
.venv/bin/python scripts/profile_role_scan.py --iterations 3 --detailed-catalog --fixture comment_driven_demo_role --json
```

Profile hot-path inspection:

```bash
.venv/bin/python -c "import pstats; s=pstats.Stats('debug_readmes/profiles/comment_driven_demo_role-default.prof'); s.sort_stats('cumtime').print_stats(20)"
```

## Baseline Table

Scenario: `prism role <fixture> --dry-run`

| Fixture | Min (s) | Mean (s) | Max (s) |
| --- | ---: | ---: | ---: |
| `mock_role` | 0.6493 | 0.6562 | 0.6609 |
| `enhanced_mock_role` | 0.8189 | 0.8381 | 0.8577 |
| `comment_driven_demo_role` | 0.9841 | 0.9887 | 0.9933 |

Detailed-catalog spot check:

| Fixture | Min (s) | Mean (s) | Max (s) |
| --- | ---: | ---: | ---: |
| `comment_driven_demo_role` with `--detailed-catalog` | 1.0550 | 1.0592 | 1.0627 |

## Profile Artifact

- cProfile output: `debug_readmes/profiles/comment_driven_demo_role-default.prof`
- Artifact size: `352120` bytes

## First Hotspots

The initial `cProfile` pass points to YAML loading/parsing as the dominant measured hotspot on the default scan path for `comment_driven_demo_role`.

- `yaml.safe_load` / `yaml.load`: 191 calls, about `1.77s` cumulative
- YAML composer/parser internals dominate most of the cumulative top-20 stack
- End-to-end `prism.scanner.run_scan` stays near `1.71s` cumulative inside the profiled process

## Follow-Up Direction

Wave 2.2 should start by measuring where repeated YAML file loads can be reduced safely before looking at broader rendering or Jinja-path optimization.

## Post-Cache Follow-Up

After adding a stat-keyed in-process YAML load cache in `prism.scanner_extract.task_file_traversal`, the same local benchmark workflow showed a measurable improvement across the representative fixtures.

Updated command results:

| Fixture | Baseline Mean (s) | Post-Cache Mean (s) | Improvement |
| --- | ---: | ---: | ---: |
| `mock_role` | 0.6562 | 0.5776 | 11.98% |
| `enhanced_mock_role` | 0.8381 | 0.6342 | 24.33% |
| `comment_driven_demo_role` | 0.9887 | 0.6309 | 36.19% |
| `comment_driven_demo_role` with `--detailed-catalog` | 1.0592 | 0.6730 | 36.46% |

Updated absolute timings:

| Fixture | Min (s) | Mean (s) | Max (s) |
| --- | ---: | ---: | ---: |
| `mock_role` | 0.5745 | 0.5776 | 0.5806 |
| `enhanced_mock_role` | 0.6266 | 0.6342 | 0.6413 |
| `comment_driven_demo_role` | 0.6292 | 0.6309 | 0.6326 |

Updated detailed-catalog spot check:

| Fixture | Min (s) | Mean (s) | Max (s) |
| --- | ---: | ---: | ---: |
| `comment_driven_demo_role` with `--detailed-catalog` | 0.6651 | 0.6730 | 0.6786 |

Updated profile summary for `debug_readmes/profiles/comment_driven_demo_role-default.prof`:

- `yaml.safe_load` / `yaml.load`: 52 calls, about `0.745s` cumulative
- profiled process total time dropped to about `1.366s`
- end-to-end `prism.scanner.run_scan` cumulative time dropped to about `0.672s`

Wave 2.2 follow-up conclusion: the targeted YAML cache produced enough improvement to justify keeping the optimization, and YAML parsing remains measurable but no longer dominates the profiled path as heavily as the initial baseline.
