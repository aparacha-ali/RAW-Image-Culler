#!/usr/bin/env python3
"""RAW Image Culler - Fast review and sorting of RAW photo files."""

import sys
import os
from tkinter import filedialog
import tkinter as tk

from app import CullerApp


def main():
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        # No argument — open folder picker
        root = tk.Tk()
        root.withdraw()
        folder = filedialog.askdirectory(title="Select folder with RAW images")
        root.destroy()
        if not folder:
            print("No folder selected. Exiting.")
            sys.exit(0)

    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        print(f"Error: '{folder}' is not a valid directory.")
        sys.exit(1)

    print(f"Opening RAW Culler for: {folder}")
    CullerApp(folder)


if __name__ == "__main__":
    main()
