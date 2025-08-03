import subprocess
from pathlib import Path

def test_wiki_parser_dry_run():
    """Test Wikipedia album parser in dry-run mode with test-mode cleanup."""
    url = "https://en.wikipedia.org/wiki/Hydra_(Within_Temptation_album)"
    cmd = [
        "python3", "run_all.py",
        "--type", "wiki",
        "--url", url,
        "--dry-run",
        "--summary",
        "--test-mode"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Ensure it ran successfully
    assert result.returncode == 0, f"Process failed: {result.stderr}"

    # Check for any "succeeded" in parsing step rather than hardcoded phrase
    assert "STEP 1" in result.stdout
    assert "succeeded" in result.stdout.lower()

    # CSV should exist in /tmp/music_downloader_dryrun (before cleanup)
    tmp_dir = Path("/tmp/music_downloader_dryrun")
    csv_files = list(tmp_dir.glob("**/*.csv"))

    # Ensure at least one CSV existed before cleanup
    assert len(csv_files) > 0, "Expected CSV file in dry-run temp folder"

    # In test mode cleanup, temp dir should be deleted
    assert not tmp_dir.exists(), "Temp dir should be removed in --test-mode cleanup"
