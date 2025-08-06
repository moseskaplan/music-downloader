"""Version information for the music downloader package.

This module defines a semantic version string and provides a helper to
retrieve the current git commit hash when available. Scripts can import
VERSION or call get_git_revision() to log version information.
"""

VERSION = "0.1.0"

def get_git_revision() -> str:
    """Return the current git commit hash, or 'unknown' if not in a git repo."""
    try:
        import subprocess
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"