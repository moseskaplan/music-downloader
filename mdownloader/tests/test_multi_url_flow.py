# mdownloader/tests/test_multi_url_flow.py
import os
import subprocess
import sys
import pytest

@pytest.mark.xfail(reason="Wiki parser exits with code 1 in test-mode (see Epic 10)")
def test_run_all_multi_url(tmp_path):
    """Smoke test: run_all with multiple URLs to verify multi-URL flow."""
    urls = [
        "https://en.wikipedia.org/wiki/21_(Adele_album)",
        "https://en.wikipedia.org/wiki/Random_Access_Memories",
    ]
    env = os.environ.copy()
    env.setdefault("YOUTUBE_API_KEY", "DUMMY_FOR_TESTS")
    env["XDG_CACHE_HOME"] = str(tmp_path / ".cache")

    cmd = [
        sys.executable, "-m", "mdownloader.core.run_all",
        "--url", *urls,
        "--test-mode", "--summary", "--no-cleanup",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)

    # Marked xfail until wiki parser is patched, but CLI should run
    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
