import subprocess
import os
from pathlib import Path
from pathlib import Path
import shutil

def test_apple_parser_test_mode():
    """Test Apple Music album parser in test-mode with cleanup skipped."""
    url = "https://music.apple.com/us/album/abbey-road-remastered/1441164426"  # Beatles album
    # Use the package orchestrator; type will be inferred automatically.
    cmd = [
        "python3", "-m", "mdownloader.core.run_all",
        "--url", url,
        "--summary",
        "--test-mode",
        "--no-cleanup"  # keep temp folder for verification
    ]
    # Ensure the mdownloader package can be discovered by setting PYTHONPATH
    env = os.environ.copy()
    # Discover the project root by walking up until we find the 'mdownloader' package
    current = Path(__file__).resolve()
    root_dir = None
    for parent in current.parents:
        if (parent / "mdownloader").exists():
            root_dir = parent
            break
    # Fallback to current working directory if not found
    if root_dir is None:
        root_dir = Path(os.getcwd()).parent
    env["PYTHONPATH"] = str(root_dir)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

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

    # Cleanup manually (TO DO: automate in future)
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
