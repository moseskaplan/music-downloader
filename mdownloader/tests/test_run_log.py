# mdownloader/tests/test_run_log.py
import os
import subprocess
import sys
from pathlib import Path
import pytest

@pytest.mark.xfail(reason="Wiki parser exits with code 1 in test-mode (see Epic 10)")
def test_run_all_creates_run_log(tmp_path):
    """Verify that run_all produces a run_log.txt for an album run."""
    sample_url = "https://en.wikipedia.org/wiki/21_(Adele_album)"
    env = os.environ.copy()
    env.setdefault("YOUTUBE_API_KEY", "DUMMY_FOR_TESTS")
    env["XDG_CACHE_HOME"] = str(tmp_path / ".cache")

    # Output dir where run_all should drop album log
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    cmd = [
        sys.executable, "-m", "mdownloader.core.run_all",
        "--url", sample_url,
        "--test-mode", "--summary", "--no-cleanup",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=output_dir, timeout=300)

    # Check if run_log.txt exists anywhere under output_dir
    run_logs = list(output_dir.rglob("run_log.txt"))
    assert run_logs, f"No run_log.txt found. stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
