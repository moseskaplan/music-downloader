# mdownloader/tests/test_gui.py
import os
import sys
import pytest

# If Tk isn't available, skip. On GitHub Actions "CI=true" by default; we skip GUI entirely there.
if os.environ.get("CI") == "true" or sys.platform.startswith("linux"):
    pytest.skip("Skipping GUI test in headless CI environment.", allow_module_level=True)

tk = pytest.importorskip("tkinter")

def test_gui_launch(monkeypatch):
    """Smoke test that GUI launches without entering an infinite loop."""
    from mdownloader.gui.main_window import launch_gui

    # Prevent the real event loop from blocking the test
    monkeypatch.setattr("tkinter.Tk.mainloop", lambda self: None)

    try:
        launch_gui()
    except Exception as e:
        pytest.fail(f"GUI failed to launch: {e}")
