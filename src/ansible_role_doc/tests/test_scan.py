"""Unit tests for the ansible_role_doc scanner CLI.

These tests exercise the package CLI by importing the local package and
invoking the entrypoint in a subprocess to simulate real usage.
"""

from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).parent


def test_scan_detects_defaults(tmp_path):
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "output.md"
    # Run the CLI by importing the package module to avoid path assumptions
    # Import package via sys.path so installed package isn't required.
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from ansible_role_doc.cli import main;"
        "sys.exit(main(['{role}','-o','{out}']))"
    ).format(src_dir=str(HERE.parent.parent), role=str(target), out=str(out))

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)

    assert res.returncode == 0
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Default value 1" in content
    assert ("Default value 3" in content) or ("default(" in content)
