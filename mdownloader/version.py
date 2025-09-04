"""Package version information and git revision helper.

This module defines a semantic version string for the music
downloader package and provides a helper function to retrieve the
current git commit hash.  Scripts can import ``VERSION`` or call
``get_git_revision()`` to include version information in logs.
"""

VERSION = "0.1.0"


def get_git_revision() -> str:
    """Return the current git commit hash, or 'unknown' if unavailable."""
    try:
        import subprocess
        return subprocess.check_output([
            "git", "rev-parse", "--short", "HEAD"
        ], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"