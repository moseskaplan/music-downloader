"""Graphical user interface for the music downloader.

Users can paste one or more media URLs and click "Run Downloader" to
download and tag tracks. This module invokes the orchestrator module via
`python3 -m mdownloader.core.run_all`.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess


def run_downloader():
    """Callback for the Run Downloader button.

    Collects one or more URLs from the text box, constructs the
    appropriate command and runs it using subprocess. Each URL will be
    processed in sequence by the orchestrator. Errors are surfaced via
    message boxes.
    """
    raw_text = url_text.get("1.0", tk.END)
    candidates = [part.strip() for line in raw_text.strip().splitlines() for part in line.split(",")]
    urls = [u for u in candidates if u]
    if not urls:
        messagebox.showerror("Missing URL", "Please enter at least one valid media URL.")
        return

    # Use -m to run the orchestrator from within the package
    cmd = ["python3", "-m", "mdownloader.core.run_all", "--url"] + urls
    # Append workers argument if provided and greater than 1
    workers_val = workers_var.get()
    try:
        workers_int = int(workers_val)
    except Exception:
        workers_int = 0
    if workers_int and workers_int > 1:
        cmd += ["--workers", str(workers_int)]
    try:
        subprocess.run(cmd, check=True)
        messagebox.showinfo("Success", "Download completed successfully.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Download failed:\n{e}")


def main():
    """Launch the GUI application."""
    root = tk.Tk()
    root.title("Music Downloader")
    root.geometry("600x200")

    style = ttk.Style()
    style.theme_use("clam")

    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill="both", expand=True)

    ttk.Label(main_frame, text="Media URL(s):").grid(row=0, column=0, sticky="nw")
    global url_text
    url_text = tk.Text(main_frame, width=50, height=4)
    url_text.grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky="we")

    # Workers selection
    ttk.Label(main_frame, text="Concurrent workers:").grid(row=1, column=0, sticky="nw", pady=(10, 0))
    global workers_var
    workers_var = tk.StringVar(value="2")
    workers_spin = tk.Spinbox(main_frame, from_=1, to=8, textvariable=workers_var, width=5)
    workers_spin.grid(row=1, column=1, sticky="w", pady=(10, 0))

    ttk.Button(main_frame, text="Run Downloader", command=run_downloader).grid(row=3, column=0, columnspan=4, pady=15)

    root.mainloop()


if __name__ == "__main__":
    main()
