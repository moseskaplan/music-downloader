import subprocess
from pathlib import Path
import shutil

def test_wiki_parser_test_mode():
    """Test Wikipedia album parser in test-mode with cleanup skipped."""
    url = "https://en.wikipedia.org/wiki/Hydra_(Within_Temptation_album)"
    cmd = [
        "python3", "run_all.py",
        "--type", "wiki",
        "--url", url,
        "--summary",
        "--test-mode",
        "--no-cleanup"  # keep temp folder for verification
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Ensure it ran successfully
    assert result.returncode == 0, f"Process failed: {result.stderr}"

    # Verify parsing step succeeded
    assert "STEP 1" in result.stdout
    assert "succeeded" in result.stdout.lower()

    # CSV should exist in /tmp/music_downloader_test
    tmp_dir = Path("/tmp/music_downloader_test")
    csv_files = list(tmp_dir.glob("**/*.csv"))

    # Ensure at least one CSV file exists
    assert len(csv_files) > 0, "Expected CSV file in test-mode temp folder"

    # Manual cleanup after verification
    shutil.rmtree(tmp_dir)
