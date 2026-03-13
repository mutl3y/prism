from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).parent


def test_render_readme_for_mock_role(tmp_path):
    """Render the README for the bundled `mock_role` and verify output."""
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out = tmp_path / "REVIEW_README.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from ansible_role_doc.scanner import run_scan;"
        "run_scan('{role}', output='{out}')"
    ).format(src_dir=str(HERE.parent.parent), role=str(target), out=str(out))

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    assert res.returncode == 0
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Galaxy Info" in content
    assert "Detected usages" in content or "default()" in content
