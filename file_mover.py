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


def execute_sort(
    folder: str,
    marks: Dict[str, Optional[str]],
    pre_edited: Optional[Dict[str, str]] = None,
) -> dict:
    """
    Move marked files into keep/ and delete/ subfolders.
    Files already in the correct subfolder are skipped.
    Unmarked files in subfolders are moved back to the root.
    Pre-edited files (RAW + XMP pairs) are moved to keep/.
    Returns {"moved": int, "pre_edited_moved": int, "errors": list[str]}.
    """
    keep_dir = os.path.join(folder, KEEP_FOLDER)
    delete_dir = os.path.join(folder, DELETE_FOLDER)
    os.makedirs(keep_dir, exist_ok=True)
    os.makedirs(delete_dir, exist_ok=True)

    moved = 0
    pre_edited_moved = 0
    errors = []

    for path, mark in marks.items():
        current_dir = os.path.dirname(path)

        if mark == MARK_KEEP:
            dest_dir = keep_dir
        elif mark == MARK_DELETE:
            dest_dir = delete_dir
        else:
            # Unmarked: move back to root if currently in a subfolder
            if current_dir in (keep_dir, delete_dir):
                dest_dir = folder
            else:
                continue

        # Skip if already in the correct folder
        if current_dir == dest_dir:
            continue

        filename = os.path.basename(path)
        dest = _unique_dest(os.path.join(dest_dir, filename))
        try:
            shutil.move(path, dest)
            moved += 1
        except Exception as e:
            errors.append(f"{filename}: {e}")

    # Move pre-edited files (RAW + XMP sidecar) to keep/
    for raw_path, xmp_path in (pre_edited or {}).items():
        for src in (raw_path, xmp_path):
            filename = os.path.basename(src)
            dest = _unique_dest(os.path.join(keep_dir, filename))
            try:
                shutil.move(src, dest)
                pre_edited_moved += 1
            except Exception as e:
                errors.append(f"{filename}: {e}")

    return {"moved": moved, "pre_edited_moved": pre_edited_moved, "errors": errors}
