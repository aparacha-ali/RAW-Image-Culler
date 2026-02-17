"""Move files into keep/delete folders safely."""

import os
import shutil
from typing import Dict, List, Optional

from constants import MARK_KEEP, MARK_DELETE, KEEP_FOLDER, DELETE_FOLDER


def _unique_dest(dest_path: str) -> str:
    """If dest_path exists, append _1, _2, etc. until unique."""
    if not os.path.exists(dest_path):
        return dest_path
    base, ext = os.path.splitext(dest_path)
    counter = 1
    while True:
        candidate = f"{base}_{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def execute_sort(folder: str, marks: Dict[str, Optional[str]]) -> dict:
    """
    Move marked files into keep/ and delete/ subfolders.
    Returns {"moved": int, "errors": list[str]}.
    """
    keep_dir = os.path.join(folder, KEEP_FOLDER)
    delete_dir = os.path.join(folder, DELETE_FOLDER)
    os.makedirs(keep_dir, exist_ok=True)
    os.makedirs(delete_dir, exist_ok=True)

    moved = 0
    errors = []

    for path, mark in marks.items():
        if mark == MARK_KEEP:
            dest_dir = keep_dir
        elif mark == MARK_DELETE:
            dest_dir = delete_dir
        else:
            continue

        filename = os.path.basename(path)
        dest = _unique_dest(os.path.join(dest_dir, filename))
        try:
            shutil.move(path, dest)
            moved += 1
        except Exception as e:
            errors.append(f"{filename}: {e}")

    return {"moved": moved, "errors": errors}
