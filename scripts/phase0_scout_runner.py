#!/usr/bin/env python3
"""Phase 0 discovery scanner - generates scout findings for mutl3y-cluster autopilot."""

import json
import re
from pathlib import Path
from typing import Any

import yaml

# Target source
TARGET = Path("/raid5/source/test/prism/src/prism")
ARTIFACTS_DIR = Path("/raid5/source/test/prism/mutl3y-artifacts/phase-0/scouts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def find_any_annotations() -> list[dict[str, Any]]:
    """Scout-Typing: Find loose type annotations."""
    findings = []
    pattern = re.compile(r".*:\s*Any\b|Callable\[\.\.\.,\s*Any\]")
    finding_id = 1

    for py_file in sorted(TARGET.rglob("*.py")):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(content.split("\n"), 1):
                if pattern.search(line) and "import" not in line:
                    rel_path = str(py_file.relative_to(TARGET.parent.parent))
                    findings.append({
                        "id": f"Scout-Typing-{finding_id:02d}",
                        "category": "typing",
                        "fingerprint": f"typing_any_annotation_{rel_path}_{line_no}",
                        "file": rel_path,
                        "line": line_no,
                        "severity_hint": "medium",
                        "confidence": "high",
                        "detector": "grep",
                        "memory_status": "new",
                        "memory_match": "",
                        "evidence_snippet": line.strip()[:95],
                        "evidence_command": f"grep -n ': Any' {rel_path}",
                        "related_symbols": [],
                        "fix_group_key": "typing_loose_annotations",
                        "proposed_fix_class": "add_type",
                        "blocking_preconditions": [],
                        "suggested_narrow_gate": "mypy src/prism",
                    })
                    finding_id += 1
                    if finding_id > 10:
                        return findings
        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return findings


def find_ownership_issues() -> list[dict[str, Any]]:
    """Scout-Ownership: Find module ownership and layer violations."""
    findings = []
    finding_id = 1

    # Look for private imports across modules
    private_import_pattern = re.compile(r"from\s+[\w.]*_[\w.]*\s+import|import\s+[\w.]*_[\w.]*")

    for py_file in sorted(TARGET.rglob("*.py")):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(content.split("\n"), 1):
                if "from" in line and "import" in line and "_" in line:
                    if any(skip in line for skip in ["__", "typing", "# type", "import _"]):
                        continue
                    rel_path = str(py_file.relative_to(TARGET.parent.parent))
                    findings.append({
                        "id": f"Scout-Ownership-{finding_id:02d}",
                        "category": "ownership",
                        "fingerprint": f"ownership_private_import_{rel_path}_{line_no}",
                        "file": rel_path,
                        "line": line_no,
                        "severity_hint": "medium",
                        "confidence": "medium",
                        "detector": "grep",
                        "memory_status": "new",
                        "memory_match": "",
                        "evidence_snippet": line.strip()[:95],
                        "evidence_command": f"sed -n {line_no}p {rel_path}",
                        "related_symbols": [],
                        "fix_group_key": "ownership_layer_violations",
                        "proposed_fix_class": "move_module",
                        "blocking_preconditions": [],
                        "suggested_narrow_gate": "ruff check src/prism",
                    })
                    finding_id += 1
                    if finding_id > 8:
                        return findings
        except Exception:
            pass

    return findings


def find_error_handling_issues() -> list[dict[str, Any]]:
    """Scout-ControlFlow: Find error handling and control flow issues."""
    findings = []
    finding_id = 1

    broad_except_pattern = re.compile(r"except\s*(Exception|BaseException|:)")
    silent_pass_pattern = re.compile(r"except.*:\s*pass")

    for py_file in sorted(TARGET.rglob("*.py")):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(content.split("\n"), 1):
                if broad_except_pattern.search(line):
                    rel_path = str(py_file.relative_to(TARGET.parent.parent))
                    severity = "high" if silent_pass_pattern.search(line) else "medium"
                    findings.append({
                        "id": f"Scout-ControlFlow-{finding_id:02d}",
                        "category": "error_channel",
                        "fingerprint": f"controlflow_broad_except_{rel_path}_{line_no}",
                        "file": rel_path,
                        "line": line_no,
                        "severity_hint": severity,
                        "confidence": "high",
                        "detector": "grep",
                        "memory_status": "new",
                        "memory_match": "",
                        "evidence_snippet": line.strip()[:95],
                        "evidence_command": f"sed -n {line_no}p {rel_path}",
                        "related_symbols": [],
                        "fix_group_key": "error_handling_broad_except",
                        "proposed_fix_class": "tighten_except",
                        "blocking_preconditions": [],
                        "suggested_narrow_gate": "pytest -k error src/prism/tests",
                    })
                    finding_id += 1
                    if finding_id > 8:
                        return findings
        except Exception:
            pass

    return findings


def find_graph_issues() -> list[dict[str, Any]]:
    """Scout-Graph: Find dependency and import issues."""
    findings = []
    finding_id = 1

    # Look for potential circular import patterns
    import_pattern = re.compile(r"^from\s+([\w.]+)\s+import|^import\s+([\w.]+)")

    for py_file in sorted(TARGET.rglob("*.py")):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            imports = []
            for line in content.split("\n"):
                match = import_pattern.match(line)
                if match:
                    imports.append(line.strip())

            # Check for back-references (simple heuristic)
            rel_path = str(py_file.relative_to(TARGET.parent.parent))
            parent_pkg = rel_path.split("/")[2]  # Get package like scanner_core

            if len(imports) > 15:  # Potential over-importing
                findings.append({
                    "id": f"Scout-Graph-{finding_id:02d}",
                    "category": "graph",
                    "fingerprint": f"graph_high_import_count_{rel_path}",
                    "file": rel_path,
                    "line": 1,
                    "severity_hint": "low",
                    "confidence": "medium",
                    "detector": "grep",
                    "memory_status": "new",
                    "memory_match": "",
                    "evidence_snippet": f"File has {len(imports)} imports",
                    "evidence_command": f"grep -n '^from\\|^import' {rel_path} | wc -l",
                    "related_symbols": [],
                    "fix_group_key": "graph_dependency_review",
                    "proposed_fix_class": "type_only_import",
                    "blocking_preconditions": [],
                    "suggested_narrow_gate": "",
                })
                finding_id += 1
                if finding_id > 8:
                    return findings
        except Exception:
            pass

    return findings


def main() -> None:
    """Generate all scout findings and write artifacts."""
    print("[Phase 0] Generating scout findings...")

    scouts = {
        "Scout-Typing": find_any_annotations,
        "Scout-Ownership": find_ownership_issues,
        "Scout-ControlFlow": find_error_handling_issues,
        "Scout-Graph": find_graph_issues,
    }

    summaries = []

    for scout_name, scout_fn in scouts.items():
        print(f"  Running {scout_name}...")
        findings = scout_fn()

        artifact_path = ARTIFACTS_DIR / f"{scout_name}.yaml"
        artifact_path.write_text(
            yaml.safe_dump(findings, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"    → {len(findings)} findings written to {artifact_path.relative_to(TARGET.parent.parent)}")

        summary = {
            "scout": scout_name,
            "artifact_path": str(artifact_path.relative_to(TARGET.parent.parent.parent)),
            "findings_count": len(findings),
            "severity_breakdown": {
                "critical": sum(1 for f in findings if f["severity_hint"] == "critical"),
                "high": sum(1 for f in findings if f["severity_hint"] == "high"),
                "medium": sum(1 for f in findings if f["severity_hint"] == "medium"),
                "low": sum(1 for f in findings if f["severity_hint"] == "low"),
            },
            "top_fix_groups": list(set(f["fix_group_key"] for f in findings[:3])),
        }
        summaries.append(summary)

    # Write phase 0 summary
    summary_path = ARTIFACTS_DIR.parent / "phase-0-scout-summary.yaml"
    summary_path.write_text(
        yaml.safe_dump(
            {"scouts_summary": summaries, "total_findings": sum(s["findings_count"] for s in summaries)},
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    print(f"\n[Phase 0] Scout summary written to {summary_path.relative_to(TARGET.parent.parent.parent)}")
    print(f"[Phase 0] Total findings: {sum(s['findings_count'] for s in summaries)}")


if __name__ == "__main__":
    main()
