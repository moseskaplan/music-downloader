# mdownloader/gui/main_window.py

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os

def run_downloader():
    raw_text = url_text.get("1.0", tk.END)
    candidates = [part.strip() for line in raw_text.strip().splitlines() for part in line.split(",")]
    urls = [u for u in candidates if u]

    if not urls:
        messagebox.showerror("Missing URL", "Please enter at least one valid media URL.")
        return

    cmd = ["python3", "-m", "mdownloader.core.run_all", "--url"] + urls
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    print(f"[DEBUG] Running command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, env=env)
        messagebox.showinfo("Success", "Download completed successfully.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Download failed:\n{e}")

def launch_gui():
    global url_text  # Required to allow run_downloader to access this
    root = tk.Tk()
    root.title("Music Downloader")
    root.geometry("600x200")

    style = ttk.Style()
    style.theme_use("clam")

    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill="both", expand=True)

    ttk.Label(main_frame, text="Media URL(s):").grid(row=0, column=0, sticky="nw")
    url_text = tk.Text(main_frame, width=50, height=4)
    url_text.grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky="we")

    ttk.Button(main_frame, text="Run Downloader", command=run_downloader).grid(row=2, column=0, columnspan=4, pady=15)

    root.mainloop()
