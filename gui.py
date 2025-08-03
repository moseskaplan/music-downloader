import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os

def run_downloader():
    """Callback for the Run Downloader button.

    This function reads the URL and source type from the GUI and executes
    the pipeline via run_all.py. Dry‑run and summary options have been
    removed from the UI for end‑users; those modes remain available via
    CLI for developers and testers.
    """
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Missing URL", "Please enter a valid media URL.")
        return

    # Build the command: run_all orchestrates parsing, downloading and tagging.
    # Omit the --type flag so run_all can infer the correct parser from the URL.
    cmd = ["python3", "run_all.py", "--url", url]

    print(f"[DEBUG] Running command: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)
        messagebox.showinfo("Success", "Download completed successfully.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Download failed:\n{e}")

# === Setup GUI ===
root = tk.Tk()
root.title("Music Downloader")
root.geometry("600x200")

# Apply theme (after root init)
style = ttk.Style()
style.theme_use("clam")

main_frame = ttk.Frame(root, padding=20)
main_frame.pack(fill="both", expand=True)

# === Widgets ===
ttk.Label(main_frame, text="Media URL:").grid(row=0, column=0, sticky="w")
url_entry = ttk.Entry(main_frame, width=50)
url_entry.grid(row=0, column=1, columnspan=3, padx=10, pady=5)

# Previously a drop‑down allowed users to choose the parser type. Since the
# system can now infer the correct parser from the URL, the drop‑down has
# been removed to streamline the UI.

# Run Button (row 2 since checkboxes were removed)
ttk.Button(main_frame, text="Run Downloader", command=run_downloader).grid(row=2, column=0, columnspan=4, pady=15)

# Launch window
root.mainloop()
