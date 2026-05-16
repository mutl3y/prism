# Micro-Swarm

Use a micro-swarm only for ambiguous findings or tightly entangled decisions.

## When To Use

- module move with unclear import fallout
- ownership refactor with test/API uncertainty
- one finding spans imports, tests, and runtime behavior

## When Not To Use

- broad discovery
- routine category fixes
- bookkeeping
- work where one foreman decision is the only blocker

## Default Shape

Use 2-3 named investigators with distinct questions:

- `Probe-Imports`: import graph and layering fallout
- `Probe-Tests`: direct test imports and test breakage risk
- `Probe-Ownership`: correct home for the symbol or module

Each investigator writes a file-backed artifact and returns only a short summary plus artifact path.

The foreman synthesizes. Investigators do not run a free-form group chat.
