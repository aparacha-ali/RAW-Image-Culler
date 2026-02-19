"""Data model: image list, marks, and undo stack."""

import os
from typing import Dict, List, Optional, Tuple
from constants import SUPPORTED_EXTENSIONS, MARK_KEEP, MARK_DELETE, MARK_NONE, KEEP_FOLDER, DELETE_FOLDER


def _find_xmp(raw_path: str) -> Optional[str]:
    """Return the XMP sidecar path if one exists alongside the RAW file, else None."""
    base = os.path.splitext(raw_path)[0]
    for candidate in (base + ".xmp", base + ".XMP", raw_path + ".xmp", raw_path + ".XMP"):
        if os.path.isfile(candidate):
            return candidate
    return None


class CullerModel:
    def __init__(self, folder: str):
        self.folder = folder
        self.images: List[str] = []  # full paths
        self.marks: Dict[str, Optional[str]] = {}  # path -> mark
        self.initial_marks: Dict[str, Optional[str]] = {}  # marks at load time
        self.undo_stack: List[Tuple[str, Optional[str]]] = []  # (path, previous_mark)
        self.pre_edited: Dict[str, str] = {}  # raw_path -> xmp_path (auto-keep)
        self._scan_folder()

    def _scan_folder(self):
        # Scan root folder (unmarked files), skipping any with XMP sidecars
        entries = []  # (full_path, sort_key, mark)
        for name in os.listdir(self.folder):
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                raw_path = os.path.join(self.folder, name)
                xmp_path = _find_xmp(raw_path)
                if xmp_path:
                    self.pre_edited[raw_path] = xmp_path
                else:
                    entries.append((raw_path, name.lower(), MARK_NONE))

        # Scan keep/ subfolder if it exists
        keep_dir = os.path.join(self.folder, KEEP_FOLDER)
        if os.path.isdir(keep_dir):
            for name in os.listdir(keep_dir):
                ext = os.path.splitext(name)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    entries.append((os.path.join(keep_dir, name), name.lower(), MARK_KEEP))

        # Scan delete/ subfolder if it exists
        delete_dir = os.path.join(self.folder, DELETE_FOLDER)
        if os.path.isdir(delete_dir):
            for name in os.listdir(delete_dir):
                ext = os.path.splitext(name)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    entries.append((os.path.join(delete_dir, name), name.lower(), MARK_DELETE))

        entries.sort(key=lambda e: e[1])
        self.images = [e[0] for e in entries]
        for path, _, mark in entries:
            self.marks[path] = mark
            self.initial_marks[path] = mark

    @property
    def count(self) -> int:
        return len(self.images)

    def get_mark(self, path: str) -> Optional[str]:
        return self.marks.get(path, MARK_NONE)

    def set_mark(self, path: str, mark: Optional[str]):
        prev = self.marks.get(path, MARK_NONE)
        self.undo_stack.append((path, prev))
        self.marks[path] = mark

    def undo(self) -> Optional[str]:
        """Undo last mark. Returns the path that was restored, or None."""
        if not self.undo_stack:
            return None
        path, prev_mark = self.undo_stack.pop()
        self.marks[path] = prev_mark
        return path

    def first_unmarked(self, start: int = 0) -> Optional[int]:
        """Return index of the first unmarked image at or after start, or None."""
        for i in range(start, self.count):
            if self.marks.get(self.images[i], MARK_NONE) == MARK_NONE:
                return i
        return None

    def summary(self) -> dict:
        keeps = sum(1 for m in self.marks.values() if m == MARK_KEEP)
        deletes = sum(1 for m in self.marks.values() if m == MARK_DELETE)
        unmarked = self.count - keeps - deletes
        return {"keep": keeps, "delete": deletes, "unmarked": unmarked}
