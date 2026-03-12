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
    python_code = (
        "from ansible_role_doc.cli import main;"
        "import sys;"
        "sys.exit(main(['{role}','-o','{out}']))"
    ).format(role=str(target), out=str(out))

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)

    assert res.returncode == 0
    assert out.exists()
    content = out.read_text(encoding='utf-8')
    assert "Default value 1" in content
    assert ("Default value 3" in content) or ("default(" in content)