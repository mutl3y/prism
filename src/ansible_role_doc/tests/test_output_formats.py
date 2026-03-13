from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).parent


def test_outputs_md_and_html(tmp_path):
    role_src = HERE / "mock_role"
    target = tmp_path / "mock_role"
    shutil.copytree(role_src, target)

    out_md = tmp_path / "output.md"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from ansible_role_doc.cli import main;"
        "sys.exit(main(['{role}','-o','{out}','-v']))"
    ).format(src_dir=str(HERE.parent.parent), role=str(target), out=str(out_md))

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    assert res.returncode == 0
    assert out_md.exists()
    content = out_md.read_text(encoding="utf-8")
    # metadata from mock_role should be present
    assert "Galaxy Info" in content
    assert "license" in content.lower()

    # now HTML output
    out_html = tmp_path / "output.html"
    python_code = (
        "import sys;"
        "sys.path.insert(0, '{src_dir}');"
        "from ansible_role_doc.cli import main;"
        "sys.exit(main(['{role}','-o','{out}','-f','html']))"
    ).format(src_dir=str(HERE.parent.parent), role=str(target), out=str(out_html))

    cmd = [sys.executable, "-c", python_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    assert res.returncode == 0
    assert out_html.exists()
    html = out_html.read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert "mock_role" in html
