import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os

def run_downloader():
    """Callback for the Run Downloader button.

    This function collects one or more URLs from the multi‑line text box and
    executes the pipeline via run_all.py. Users can paste multiple links
    separated by newlines or commas. The type is inferred automatically
    for each URL by run_all. Developer options like dry‑run or summary
    remain available via CLI.
    """
    # Gather URLs from the Text widget. Split on newlines and commas.
    raw_text = url_text.get("1.0", tk.END)
    # Split on comma and newline, then strip whitespace
    candidates = [part.strip() for line in raw_text.strip().splitlines() for part in line.split(",")]
    # Filter out empty strings
    urls = [u for u in candidates if u]

    if not urls:
        messagebox.showerror("Missing URL", "Please enter at least one valid media URL.")
        return

    # Build the command: supply --url once followed by all URLs. run_all.py
    # accepts multiple URLs via nargs='+' and will process them in order.
    cmd = ["python3", "-m", "mdownloader.core.run_all", "--url"] + urls
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    print(f"[DEBUG] Running command: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True, env=env)
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
ttk.Label(main_frame, text="Media URL(s):").grid(row=0, column=0, sticky="nw")
url_text = tk.Text(main_frame, width=50, height=4)
url_text.grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky="we")

# Previously a drop‑down allowed users to choose the parser type. Since the
# system can now infer the correct parser from the URL, the drop‑down has
# been removed to streamline the UI.

# Run Button (row 2 since checkboxes were removed)
ttk.Button(main_frame, text="Run Downloader", command=run_downloader).grid(row=2, column=0, columnspan=4, pady=15)

# Launch window
root.mainloop()

if __name__ == "__main__":
    root.mainloop()
