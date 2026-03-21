# Architecture

Prism is a static-analysis documentation engine for Ansible roles and collections.

It is best understood as a contract-and-governance pipeline, not only a renderer.

## Pipeline Overview

1. discover role/collection structure
2. parse YAML and Jinja signals
3. compute variable insights and scanner counters
4. render docs and machine-readable payloads

## Primary Components

- scanner core for role analysis
- collection plugin catalog extraction
- CLI orchestration (`role`, `collection`, `repo`)
- output rendering (`md`, `json`, `html`, `pdf`)

## Contract And Governance Layers

- contract layer: generated markdown/json defines automation interface behavior
- confidence layer: provenance and uncertainty flags mark non-deterministic areas
- governance layer: CI policies consume scanner flags and JSON fields
- learning loop: `prism-learn` aggregates fleet-wide trends and recommendations

## Design Principle

Prefer deterministic, reviewable output over speculative runtime inference.
