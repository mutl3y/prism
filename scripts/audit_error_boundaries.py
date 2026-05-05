"""T3-04: Error boundary audit script.

Scans scanner_core/scanner_io/scanner_extract/scanner_analysis modules for
raw ``raise (ValueError|RuntimeError|TypeError|KeyError)(...)`` statements
and reports any that are not present in the baseline allowlist. New raw
raises at module boundaries should either be wrapped in
:class:`prism.errors.PrismRuntimeError` or explicitly added to the allowlist
with justification.

Usage::

    python scripts/audit_error_boundaries.py            # report mode
    python scripts/audit_error_boundaries.py --check    # exit 1 on regressions
    python scripts/audit_error_boundaries.py --update   # rewrite baseline
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOTS = (
    "src/prism/scanner_core",
    "src/prism/scanner_io",
    "src/prism/scanner_extract",
    "src/prism/scanner_analysis",
)
BASELINE_PATH = REPO_ROOT / "docs/dev_docs/error-boundary-audit-baseline.json"

RAW_RAISE_RE = re.compile(
    r"^\s*raise\s+(ValueError|RuntimeError|TypeError|KeyError)\s*\("
)


def _collect_raises() -> list[tuple[str, int, str]]:
    """Return list of (relative_path, line_number, kind) raw raises."""
    findings: list[tuple[str, int, str]] = []
    for root in SCAN_ROOTS:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            continue
        for py_file in sorted(root_path.rglob("*.py")):
            rel = py_file.relative_to(REPO_ROOT).as_posix()
            try:
                content = py_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for lineno, line in enumerate(content.splitlines(), start=1):
                match = RAW_RAISE_RE.match(line)
                if match:
                    findings.append((rel, lineno, match.group(1)))
    return findings


def _load_baseline() -> set[tuple[str, str]]:
    if not BASELINE_PATH.exists():
        return set()
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {(entry["file"], entry["kind"]) for entry in data.get("allowlist", [])}


def _write_baseline(findings: list[tuple[str, int, str]]) -> None:
    payload = {
        "description": (
            "Allowlist of raw exception raises at module boundaries. "
            "Each entry is identified by (file, kind). Update via "
            "scripts/audit_error_boundaries.py --update after wrapping a raise "
            "in PrismRuntimeError or adding a new justified raise."
        ),
        "allowlist": [
            {"file": path, "kind": kind}
            for path, kind in sorted({(p, k) for p, _, k in findings})
        ],
    }
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 on regression")
    parser.add_argument("--update", action="store_true", help="rewrite baseline")
    args = parser.parse_args(argv)

    findings = _collect_raises()
    if args.update:
        _write_baseline(findings)
        print(f"Wrote baseline with {len(findings)} entries to {BASELINE_PATH}")
        return 0

    baseline = _load_baseline()
    current = {(path, kind) for path, _, kind in findings}
    new_raises = sorted(current - baseline)

    if args.check:
        if new_raises:
            print("New raw exception raises detected (regression):")
            for path, kind in new_raises:
                print(f"  {path}: raise {kind}")
            print("Wrap in PrismRuntimeError or run --update.")
            return 1
        return 0

    print(f"Total raw raises: {len(findings)}")
    print(f"Allowlisted (file, kind) pairs: {len(baseline)}")
    if new_raises:
        print("New (non-allowlisted) raises:")
        for path, kind in new_raises:
            print(f"  {path}: raise {kind}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
