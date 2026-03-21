---
layout: default
title: Annotation Quality Workoff
---

Status: complete

## What Was Delivered

- disabled marker detection for commented-out tasks
- `disabled_task_annotations` counters
- YAML-like payload warning detection
- `yaml_like_task_annotations` counters
- strict-fail enforcement option in config and CLI
- scanner-report rendering for annotation quality counters

## Guidance

- target zero YAML-like marker payloads
- enforce strict mode in CI after remediation
- track disabled annotation drift as a review signal
