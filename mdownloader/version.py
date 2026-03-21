"""Package version information."""

VERSION = "0.1.0"


def get_git_revision() -> str:
    """Return the current git commit hash, or 'unknown' if unavailable."""
    try:
        import subprocess
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"
