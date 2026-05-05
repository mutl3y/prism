"""T3-04: Error boundary audit guardrail."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_error_boundaries.py"
BASELINE_PATH = REPO_ROOT / "docs/dev_docs/error-boundary-audit-baseline.json"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("_audit_t3_04", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["_audit_t3_04"] = module
    spec.loader.exec_module(module)
    return module


def test_audit_script_exists() -> None:
    assert SCRIPT_PATH.exists(), "audit script must exist for T3-04 enforcement"


def test_baseline_exists_and_is_valid_json() -> None:
    assert BASELINE_PATH.exists(), "baseline must be checked in"
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert "allowlist" in payload
    for entry in payload["allowlist"]:
        assert {"file", "kind"} <= entry.keys()
        assert entry["kind"] in {"ValueError", "RuntimeError", "TypeError", "KeyError"}


def test_no_new_raw_raises_at_module_boundaries() -> None:
    module = _load_audit_module()
    findings = module._collect_raises()
    baseline = module._load_baseline()
    current = {(path, kind) for path, _, kind in findings}
    new_raises = sorted(current - baseline)
    assert not new_raises, (
        "New raw exception raises detected at module boundaries. "
        "Wrap them in PrismRuntimeError or update the baseline via "
        f"`python scripts/audit_error_boundaries.py --update`. New: {new_raises}"
    )
