# mdownloader/tests/test_concurrency.py
import os
import subprocess
import sys
import pytest

@pytest.mark.xfail(reason="Wiki parser exits with code 1 in test-mode (see Epic 10)")
def test_run_all_with_workers():
    """Ensure --workers flag does not crash in test-mode."""
    sample_url = "https://en.wikipedia.org/wiki/21_(Adele_album)"
    env = os.environ.copy()
    env.setdefault("YOUTUBE_API_KEY", "DUMMY_FOR_TESTS")

    cmd = [
        sys.executable, "-m", "mdownloader.core.run_all",
        "--url", sample_url,
        "--workers", "2",
        "--test-mode", "--summary", "--no-cleanup",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)

    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
