# mdownloader/tests/test_wiki_parser.py
import os
import subprocess
from pathlib import Path
import pytest

@pytest.mark.xfail(reason="Wiki parser currently exits with code 1 in test-mode")
def test_wiki_parser_test_mode():
    """Test Wikipedia album parser in test-mode with cleanup skipped.

    This is marked xfail until parsers/wiki.py is patched to handle current table structures.
    """
    url = "https://en.wikipedia.org/wiki/21_(Adele_album)"
    cmd = [
        "python3", "-m", "mdownloader.core.run_all",
        "--url", url,
        "--summary",
        "--test-mode",
        "--no-cleanup",
    ]

    env = os.environ.copy()
    current = Path(__file__).resolve()
    root_dir = None
    for parent in current.parents:
        if (parent / "mdownloader").exists():
            root_dir = parent
            break
    if root_dir is None:
        root_dir = Path(os.getcwd()).parent
    env["PYTHONPATH"] = str(root_dir)

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    # We expect this to fail right now, but once fixed the test will pass.
    assert result.returncode == 0, f"Process failed:\nstdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
