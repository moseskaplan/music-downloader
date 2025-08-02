import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os

def run_downloader():
    url = url_entry.get().strip()
    selected_label = source_var.get()
    source_type = source_type_map[selected_label]
    dry_run = dry_run_var.get()
    show_summary = summary_var.get()

    print(f"[DEBUG] Dry Run checked: {dry_run}")
    print(f"[DEBUG] Show Summary checked: {show_summary}")

    if not url:
        messagebox.showerror("Missing URL", "Please enter a valid media URL.")
        return

    cmd = ["python3", "run_all.py", "--url", url, "--type", source_type, "--cascade"]

    if dry_run:
        cmd.append("--dry-run")
    if show_summary:
        cmd.append("--summary")

    print(f"[DEBUG] Running command: {' '.join(cmd)}")  # <--- Add this line

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

# Capitalized dropdown menu
ttk.Label(main_frame, text="Source Type:").grid(row=1, column=0, sticky="w")
source_type_map = {
    "Wiki": "wiki",
    "YouTube": "youtube",
    "Search": "search",
    "Apple": "apple"
}
source_labels = list(source_type_map.keys())
source_var = tk.StringVar(value=source_labels[0])
type_menu = ttk.OptionMenu(main_frame, source_var, source_labels[0], *source_labels)
type_menu.grid(row=1, column=1, sticky="w", pady=5)

# Checkboxes
dry_run_var = tk.BooleanVar(value=False)  # Default to unchecked
summary_var = tk.BooleanVar(value=False)
ttk.Checkbutton(main_frame, text="Dry Run", variable=dry_run_var).grid(row=2, column=0, sticky="w")
ttk.Checkbutton(main_frame, text="Show Summary", variable=summary_var).grid(row=2, column=1, sticky="w")

# Run Button
ttk.Button(main_frame, text="Run Downloader", command=run_downloader).grid(row=3, column=0, columnspan=4, pady=15)

# Launch window
root.mainloop()
