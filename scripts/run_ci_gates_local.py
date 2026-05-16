#!/usr/bin/env python3
"""
Pre-commit Hook Wrapper for CI Gates

Allows running validation gates locally before pushing to GitHub.

Usage:
  1. Direct: python3 run_ci_gates_local.py
  2. Pre-commit: Add to .pre-commit-config.yaml
  3. Manual: python3 run_ci_gates_local.py --gates layer,types,coverage

Features:
  - Run all gates or select specific ones
  - Local dry-run before CI
  - Clear pass/fail reporting
  - Option to bypass (--skip-gates)
"""

import subprocess
import sys
import argparse
from pathlib import Path
from typing import List, Tuple

class LocalGateRunner:
    """Run CI gates locally."""
    
    def __init__(self, verbose=False, fail_fast=False):
        self.verbose = verbose
        self.fail_fast = fail_fast
        self.results = {}
    
    def run_gate(self, gate_name: str, command: List[str]) -> Tuple[bool, str]:
        """Run a single gate command."""
        if self.verbose:
            print(f"\n🔧 Running: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        return success, output
    
    def run_mypy(self) -> bool:
        """Type safety check."""
        print("📝 Type Safety (mypy)...", end=" ", flush=True)
        success, output = self.run_gate(
            "mypy",
            [".venv/bin/python", "-m", "mypy", "--strict", "src/prism/scanner_core/"]
        )
        
        if success:
            print("✅")
        else:
            print(f"❌ ({output.count('error:')} errors)")
            if self.verbose:
                print(output)
        
        self.results["mypy"] = success
        return success
    
    def run_ruff(self) -> bool:
        """Linting check."""
        print("🔍 Linting (ruff)...", end=" ", flush=True)
        success, output = self.run_gate(
            "ruff",
            [".venv/bin/python", "-m", "ruff", "check", "src/prism/"]
        )
        
        if success:
            print("✅")
        else:
            print(f"❌")
            if self.verbose:
                print(output)
        
        self.results["ruff"] = success
        return success
    
    def run_black(self) -> bool:
        """Code formatting check."""
        print("🎨 Formatting (black)...", end=" ", flush=True)
        success, output = self.run_gate(
            "black",
            [".venv/bin/python", "-m", "black", "--check", "src/prism/"]
        )
        
        if success:
            print("✅")
        else:
            print(f"❌ (Run: black src/prism/)")
            if self.verbose:
                print(output)
        
        self.results["black"] = success
        return success
    
    def run_pytest_quick(self) -> bool:
        """Quick smoke test (subset of tests)."""
        print("⚡ Tests (quick)...", end=" ", flush=True)
        
        # Run critical tests only (faster)
        success, output = self.run_gate(
            "pytest",
            [
                ".venv/bin/python", "-m", "pytest", "-x", "-q",
                "src/prism/tests/test_scanner_context.py",
                "src/prism/tests/test_di.py",
                "src/prism/tests/test_scan_request.py",
            ]
        )
        
        if success:
            print("✅")
        else:
            print(f"❌ (Run: pytest -v for details)")
            if self.verbose:
                print(output)
        
        self.results["pytest_quick"] = success
        return success
    
    def run_layer_boundary_check(self) -> bool:
        """Layer boundary enforcement."""
        print("🏗️  Layer Boundaries...", end=" ", flush=True)
        
        # Check for upward imports
        violations = []
        
        result = subprocess.run(
            ["grep", "-r", "from prism.scanner_plugins", "src/prism/scanner_core/"],
            capture_output=True,
        )
        if result.returncode == 0:
            violations.append("scanner_core imports scanner_plugins")
        
        if violations:
            print(f"❌ ({len(violations)} violations)")
            if self.verbose:
                for v in violations:
                    print(f"  - {v}")
            self.results["layer_boundaries"] = False
            return False
        else:
            print("✅")
            self.results["layer_boundaries"] = True
            return True
    
    def run_all_gates(self) -> bool:
        """Run all gates."""
        print("\n🚀 Running Local CI Gates\n" + "="*50)
        
        gates = [
            self.run_mypy,
            self.run_ruff,
            self.run_black,
            self.run_layer_boundary_check,
            self.run_pytest_quick,
        ]
        
        for gate in gates:
            try:
                if not gate():
                    if self.fail_fast:
                        break
            except Exception as e:
                print(f"⚠️  Gate error: {e}")
        
        print("\n" + "="*50)
        
        # Summary
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        
        print(f"\n📊 Summary: {passed}/{total} gates passed")
        
        if passed == total:
            print("✅ Ready to push!")
            return True
        else:
            print(f"❌ Fix {total - passed} gate(s) before pushing")
            return False
    
    def run_selected_gates(self, gate_names: List[str]) -> bool:
        """Run selected gates."""
        print(f"\n🚀 Running Selected Gates: {', '.join(gate_names)}\n" + "="*50)
        
        gate_map = {
            "mypy": self.run_mypy,
            "types": self.run_mypy,  # Alias
            "ruff": self.run_ruff,
            "lint": self.run_ruff,  # Alias
            "black": self.run_black,
            "format": self.run_black,  # Alias
            "layer": self.run_layer_boundary_check,
            "boundaries": self.run_layer_boundary_check,  # Alias
            "pytest": self.run_pytest_quick,
            "tests": self.run_pytest_quick,  # Alias
        }
        
        results = []
        for name in gate_names:
            if name in gate_map:
                try:
                    results.append(gate_map[name]())
                except Exception as e:
                    print(f"⚠️  Error running {name}: {e}")
                    results.append(False)
            else:
                print(f"⚠️  Unknown gate: {name}")
        
        print("\n" + "="*50)
        
        if all(results):
            print("✅ All selected gates passed!")
            return True
        else:
            print(f"❌ {len([r for r in results if not r])} gate(s) failed")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Run CI gates locally before pushing"
    )
    parser.add_argument(
        "--gates",
        help="Specific gates to run (comma-separated: mypy,ruff,black,layer,pytest)",
        default=None
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "--skip-gates",
        action="store_true",
        help="Skip gates (emergency only!)"
    )
    
    args = parser.parse_args()
    
    if args.skip_gates:
        print("⚠️  Skipping CI gates (use only in emergencies!)")
        sys.exit(0)
    
    # Change to prism root
    prism_root = Path(__file__).parent.parent
    import os
    os.chdir(prism_root)
    
    runner = LocalGateRunner(verbose=args.verbose, fail_fast=args.fail_fast)
    
    if args.gates:
        gate_names = [g.strip() for g in args.gates.split(",")]
        success = runner.run_selected_gates(gate_names)
    else:
        success = runner.run_all_gates()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
