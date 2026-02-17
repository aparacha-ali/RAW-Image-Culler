"""Tkinter window, layout, key bindings, and display loop."""

import os
import tkinter as tk
from tkinter import messagebox
from PIL import ImageTk

from constants import (
    MARK_KEEP, MARK_DELETE, MARK_NONE,
    COLOR_BG, COLOR_KEEP, COLOR_DELETE, COLOR_UNMARKED,
    COLOR_STATUS_BG, COLOR_STATUS_FG, COLOR_FILENAME,
    STATUS_BAR_HEIGHT,
)
from culler_model import CullerModel
from image_loader import ImageLoader
from file_mover import execute_sort


class CullerApp:
    def __init__(self, folder: str):
        self.model = CullerModel(folder)
        if self.model.count == 0:
            messagebox.showerror("No Images", f"No supported RAW files found in:\n{folder}")
            return

        self.loader = ImageLoader(self.model.images)
        self.index = 0
        self._photo = None  # prevent GC of PhotoImage
        self._rotations = {}  # path -> rotation angle (0, 90, 180, 270)
        self._in_review = False

        self._build_ui()
        self._bind_keys()
        self._show_current()
        self.root.mainloop()

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title("RAW Culler")
        self.root.configure(bg=COLOR_BG)
        self.root.geometry("1280x800")
        self.root.minsize(640, 480)

        # Main canvas for the image
        self.canvas = tk.Canvas(self.root, bg=COLOR_BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Status bar frame at bottom
        self.status_frame = tk.Frame(self.root, bg=COLOR_STATUS_BG, height=STATUS_BAR_HEIGHT)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_frame.pack_propagate(False)

        # Status labels
        self.lbl_position = tk.Label(
            self.status_frame, text="", bg=COLOR_STATUS_BG, fg=COLOR_STATUS_FG,
            font=("Helvetica", 14, "bold"), padx=10,
        )
        self.lbl_position.pack(side=tk.LEFT)

        self.lbl_mark = tk.Label(
            self.status_frame, text="", bg=COLOR_STATUS_BG,
            font=("Helvetica", 14, "bold"), padx=10,
        )
        self.lbl_mark.pack(side=tk.LEFT)

        self.lbl_filename = tk.Label(
            self.status_frame, text="", bg=COLOR_STATUS_BG, fg=COLOR_FILENAME,
            font=("Helvetica", 12), padx=10,
        )
        self.lbl_filename.pack(side=tk.LEFT)

        self.lbl_hints = tk.Label(
            self.status_frame, text="K:keep  X:delete  U:clear  Z:undo  R/L:rotate  \u2190\u2192:nav  Enter:sort  Esc:quit",
            bg=COLOR_STATUS_BG, fg="#666666", font=("Helvetica", 11), padx=10,
        )
        self.lbl_hints.pack(side=tk.RIGHT)

        self.lbl_summary = tk.Label(
            self.status_frame, text="", bg=COLOR_STATUS_BG, fg=COLOR_STATUS_FG,
            font=("Helvetica", 12), padx=10,
        )
        self.lbl_summary.pack(side=tk.RIGHT)

        # Handle resize
        self.canvas.bind("<Configure>", lambda e: self._show_current())

    def _bind_keys(self):
        self.root.bind("<Right>", lambda e: self._navigate(1))
        self.root.bind("<Left>", lambda e: self._navigate(-1))
        self.root.bind("<k>", lambda e: self._mark(MARK_KEEP))
        self.root.bind("<K>", lambda e: self._mark(MARK_KEEP))
        self.root.bind("<x>", lambda e: self._mark(MARK_DELETE))
        self.root.bind("<X>", lambda e: self._mark(MARK_DELETE))
        self.root.bind("<u>", lambda e: self._mark(MARK_NONE))
        self.root.bind("<U>", lambda e: self._mark(MARK_NONE))
        self.root.bind("<z>", lambda e: self._undo())
        self.root.bind("<Z>", lambda e: self._undo())
        self.root.bind("<r>", lambda e: self._rotate(90))
        self.root.bind("<R>", lambda e: self._rotate(90))
        self.root.bind("<l>", lambda e: self._rotate(-90))
        self.root.bind("<L>", lambda e: self._rotate(-90))
        self.root.bind("<Return>", lambda e: self._execute_sort())
        self.root.bind("<Escape>", lambda e: self._escape())

    def _navigate(self, delta: int):
        new_index = self.index + delta
        if 0 <= new_index < self.model.count:
            self.index = new_index
            self._show_current()

    def _mark(self, mark):
        path = self.model.images[self.index]
        if mark is MARK_NONE:
            self.model.set_mark(path, MARK_NONE)
            self._update_status()
        else:
            self.model.set_mark(path, mark)
            # Auto-advance
            if self.index < self.model.count - 1:
                self.index += 1
            self._show_current()

    def _undo(self):
        restored_path = self.model.undo()
        if restored_path and restored_path in self.model.images:
            self.index = self.model.images.index(restored_path)
            self._show_current()

    def _rotate(self, degrees: int):
        path = self.model.images[self.index]
        current = self._rotations.get(path, 0)
        self._rotations[path] = (current + degrees) % 360
        self._show_current()

    def _show_current(self):
        if self.model.count == 0:
            return
        img = self.loader.get(self.index)

        # Apply rotation if any
        path = self.model.images[self.index]
        rotation = self._rotations.get(path, 0)
        if rotation:
            img = img.rotate(-rotation, expand=True)  # negative because PIL rotates CCW

        # Fit image to canvas
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 2 or ch < 2:
            return

        iw, ih = img.size
        scale = min(cw / iw, ch / ih)
        new_w = max(1, int(iw * scale))
        new_h = max(1, int(ih * scale))
        resized = img.resize((new_w, new_h), resample=1)  # BILINEAR

        self._photo = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=self._photo, anchor=tk.CENTER)

        self._update_status()

    def _update_status(self):
        path = self.model.images[self.index]
        filename = os.path.basename(path)
        mark = self.model.get_mark(path)
        summary = self.model.summary()

        self.lbl_position.config(text=f"{self.index + 1}/{self.model.count}")
        self.lbl_filename.config(text=filename)

        if mark == MARK_KEEP:
            self.lbl_mark.config(text="KEEP", fg=COLOR_KEEP)
        elif mark == MARK_DELETE:
            self.lbl_mark.config(text="DELETE", fg=COLOR_DELETE)
        else:
            self.lbl_mark.config(text="UNMARKED", fg=COLOR_UNMARKED)

        self.lbl_summary.config(
            text=f"Keep:{summary['keep']}  Del:{summary['delete']}  Unmarked:{summary['unmarked']}"
        )

    def _start_review_deletes(self):
        """Enter review mode: cycle through delete-marked images only."""
        self._delete_review_list = [
            i for i, p in enumerate(self.model.images)
            if self.model.get_mark(p) == MARK_DELETE
        ]
        if not self._delete_review_list:
            self._finish_sort()
            return

        self._review_pos = 0
        self._in_review = True

        # Temporarily rebind keys for review mode
        self.root.unbind("<Return>")
        self.root.bind("<Return>", lambda e: self._finish_sort())
        self.root.bind("<Right>", lambda e: self._review_navigate(1))
        self.root.bind("<Left>", lambda e: self._review_navigate(-1))

        self.lbl_hints.config(
            text="K:change to keep  U:unmark  \u2190\u2192:nav deletes  Enter:confirm sort  Esc:cancel"
        )

        self.index = self._delete_review_list[0]
        self._show_current()

    def _review_navigate(self, delta: int):
        new_pos = self._review_pos + delta
        if 0 <= new_pos < len(self._delete_review_list):
            self._review_pos = new_pos
            self.index = self._delete_review_list[self._review_pos]
            self._show_current()

    def _exit_review(self):
        """Exit review mode and restore normal key bindings."""
        self._in_review = False
        self.root.unbind("<Return>")
        self.root.unbind("<Right>")
        self.root.unbind("<Left>")
        self.root.bind("<Right>", lambda e: self._navigate(1))
        self.root.bind("<Left>", lambda e: self._navigate(-1))
        self.root.bind("<Return>", lambda e: self._execute_sort())
        self.lbl_hints.config(
            text="K:keep  X:delete  U:clear  Z:undo  R/L:rotate  \u2190\u2192:nav  Enter:sort  Esc:quit"
        )

    def _finish_sort(self):
        """Actually execute the sort after review."""
        self._exit_review()
        result = execute_sort(self.model.folder, self.model.marks)

        if result["errors"]:
            error_msg = "\n".join(result["errors"][:20])
            messagebox.showwarning(
                "Sort Complete (with errors)",
                f"Moved {result['moved']} files.\n\nErrors:\n{error_msg}"
            )
        else:
            messagebox.showinfo("Sort Complete", f"Successfully moved {result['moved']} files.")

        self._quit()

    def _execute_sort(self):
        summary = self.model.summary()
        if summary["keep"] == 0 and summary["delete"] == 0:
            messagebox.showinfo("Nothing to sort", "No images have been marked yet.")
            return

        msg = (
            f"Move files?\n\n"
            f"  KEEP:     {summary['keep']} files \u2192 keep/\n"
            f"  DELETE:   {summary['delete']} files \u2192 delete/\n"
            f"  UNMARKED: {summary['unmarked']} files (stay in place)\n\n"
            f"This will move the files. Continue?"
        )
        if not messagebox.askyesno("Confirm Sort", msg):
            return

        if summary["delete"] > 0:
            review = messagebox.askyesno(
                "Review Deletes",
                f"You have {summary['delete']} files marked for deletion.\n\n"
                "Would you like to review them before sorting?\n\n"
                "You can change any to Keep or Unmarked during review."
            )
            if review:
                self._start_review_deletes()
                return

        result = execute_sort(self.model.folder, self.model.marks)

        if result["errors"]:
            error_msg = "\n".join(result["errors"][:20])
            messagebox.showwarning(
                "Sort Complete (with errors)",
                f"Moved {result['moved']} files.\n\nErrors:\n{error_msg}"
            )
        else:
            messagebox.showinfo("Sort Complete", f"Successfully moved {result['moved']} files.")

        self._quit()

    def _escape(self):
        if self._in_review:
            self._exit_review()
            self._show_current()
        else:
            self._quit()

    def _quit(self):
        self.loader.shutdown()
        self.root.destroy()
