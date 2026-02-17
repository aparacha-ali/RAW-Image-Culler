"""Data model: image list, marks, and undo stack."""

import os
from typing import Dict, List, Optional, Tuple
from constants import SUPPORTED_EXTENSIONS, MARK_KEEP, MARK_DELETE, MARK_NONE


class CullerModel:
    def __init__(self, folder: str):
        self.folder = folder
        self.images: List[str] = []  # full paths
        self.marks: Dict[str, Optional[str]] = {}  # path -> mark
        self.undo_stack: List[Tuple[str, Optional[str]]] = []  # (path, previous_mark)
        self._scan_folder()

    def _scan_folder(self):
        entries = []
        for name in os.listdir(self.folder):
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                entries.append(name)
        entries.sort(key=str.lower)
        self.images = [os.path.join(self.folder, n) for n in entries]
        for path in self.images:
            self.marks[path] = MARK_NONE

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
