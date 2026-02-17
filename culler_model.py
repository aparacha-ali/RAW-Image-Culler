"""Data model: image list, marks, and undo stack."""

import os
from typing import Dict, List, Optional, Tuple
from constants import SUPPORTED_EXTENSIONS, MARK_KEEP, MARK_DELETE, MARK_NONE, KEEP_FOLDER, DELETE_FOLDER


class CullerModel:
    def __init__(self, folder: str):
        self.folder = folder
        self.images: List[str] = []  # full paths
        self.marks: Dict[str, Optional[str]] = {}  # path -> mark
        self.initial_marks: Dict[str, Optional[str]] = {}  # marks at load time
        self.undo_stack: List[Tuple[str, Optional[str]]] = []  # (path, previous_mark)
        self._scan_folder()

    def _scan_folder(self):
        # Scan root folder (unmarked files)
        entries = []  # (full_path, sort_key, mark)
        for name in os.listdir(self.folder):
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                entries.append((os.path.join(self.folder, name), name.lower(), MARK_NONE))

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

    def summary(self) -> dict:
        keeps = sum(1 for m in self.marks.values() if m == MARK_KEEP)
        deletes = sum(1 for m in self.marks.values() if m == MARK_DELETE)
        unmarked = self.count - keeps - deletes
        return {"keep": keeps, "delete": deletes, "unmarked": unmarked}
