#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE_FIXTURE="$ROOT_DIR/demos/fixtures/role_demo"
COLLECTION_FIXTURE="$ROOT_DIR/demos/fixtures/collection_demo"
OUTPUT_DIR="$ROOT_DIR/demos/output"
COLLECTION_RUNBOOK_DIR="$OUTPUT_DIR/collection_runbooks"
COLLECTION_RUNBOOK_CSV_DIR="$OUTPUT_DIR/collection_runbooks_csv"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$COLLECTION_RUNBOOK_DIR" "$COLLECTION_RUNBOOK_CSV_DIR"

echo "[1/8] Running role markdown demo"
PYTHONPATH="$ROOT_DIR/src" python -m prism.cli role \
  "$ROLE_FIXTURE" \
  -o "$OUTPUT_DIR/role_demo_README.md"

echo "[2/8] Running role detailed catalog demo"
PYTHONPATH="$ROOT_DIR/src" python -m prism.cli role \
  "$ROLE_FIXTURE" \
  --detailed-catalog \
  -o "$OUTPUT_DIR/role_demo_detailed.md"

echo "[3/8] Running role runbook markdown demo"
PYTHONPATH="$ROOT_DIR/src" python -m prism.cli role \
  "$ROLE_FIXTURE" \
  --detailed-catalog \
  --runbook-output "$OUTPUT_DIR/role_demo_RUNBOOK.md" \
  -o "$OUTPUT_DIR/role_demo_with_runbook.md"

echo "[4/8] Running role runbook CSV demo"
PYTHONPATH="$ROOT_DIR/src" python -m prism.cli role \
  "$ROLE_FIXTURE" \
  --detailed-catalog \
  --runbook-csv-output "$OUTPUT_DIR/role_demo_RUNBOOK.csv" \
  -o "$OUTPUT_DIR/role_demo_with_runbook_csv.md"

echo "[5/8] Running role JSON demo"
PYTHONPATH="$ROOT_DIR/src" python -m prism.cli role \
  "$ROLE_FIXTURE" \
  -f json \
  -o "$OUTPUT_DIR/role_demo.json"

echo "[6/8] Running collection markdown demo"
PYTHONPATH="$ROOT_DIR/src" python -m prism.cli collection \
  "$COLLECTION_FIXTURE" \
  -f md \
  -o "$OUTPUT_DIR/collection_demo.md"

echo "[7/8] Running collection detailed catalog and runbook demo"
PYTHONPATH="$ROOT_DIR/src" python -m prism.cli collection \
  "$COLLECTION_FIXTURE" \
  --detailed-catalog \
  --runbook-output "$COLLECTION_RUNBOOK_DIR" \
  --runbook-csv-output "$COLLECTION_RUNBOOK_CSV_DIR" \
  -f md \
  -o "$OUTPUT_DIR/collection_demo_detailed.md"

echo "[8/8] Running collection JSON demo"
PYTHONPATH="$ROOT_DIR/src" python -m prism.cli collection \
  "$COLLECTION_FIXTURE" \
  -f json \
  -o "$OUTPUT_DIR/collection_demo.json"

echo "Done. Demo artifacts are in: $OUTPUT_DIR"
