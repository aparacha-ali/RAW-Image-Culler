"""Tkinter window, layout, key bindings, and display loop."""

import os
import tkinter as tk
from tkinter import messagebox
from PIL import ImageTk

from constants import (
    MARK_KEEP, MARK_DELETE, MARK_NONE,
    COLOR_BG, COLOR_KEEP, COLOR_DELETE, COLOR_UNMARKED,
    COLOR_STATUS_BG, COLOR_STATUS_FG, COLOR_FILENAME, COLOR_POSITION,
    COLOR_KEEP_PILL_BG, COLOR_DELETE_PILL_BG, COLOR_UNMARKED_PILL_BG,
    COLOR_HINT_KEY_BG, COLOR_HINT_KEY_FG,
    COLOR_REVIEW_BG, COLOR_REVIEW_ACCENT,
    COLOR_OVERLAY_KEEP, COLOR_OVERLAY_DELETE, OVERLAY_FLASH_MS,
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

        self.folder_name = os.path.basename(folder)
        self.loader = ImageLoader(self.model.images)
        self.index = 0
        self._photo = None  # prevent GC of PhotoImage
        self._rotations = {}  # path -> rotation angle (0, 90, 180, 270)
        self._in_review = False
        self._flash_id = None  # for cancelling pending flash clear

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

        # Thin accent line above status bar
        self.accent_line = tk.Frame(self.root, bg="#27272a", height=1)
        self.accent_line.pack(fill=tk.X, side=tk.BOTTOM)

        # Left section: position counter
        left_frame = tk.Frame(self.status_frame, bg=COLOR_STATUS_BG)
        left_frame.pack(side=tk.LEFT, padx=(12, 0))

        self.lbl_position = tk.Label(
            left_frame, text="", bg=COLOR_STATUS_BG, fg=COLOR_POSITION,
            font=("Helvetica", 16, "bold"),
        )
        self.lbl_position.pack(side=tk.LEFT)

        # Separator
        sep1 = tk.Frame(self.status_frame, bg="#3f3f46", width=1)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=8)

        # Mark pill badge
        self.mark_pill = tk.Label(
            self.status_frame, text="", font=("Helvetica", 11, "bold"),
            padx=10, pady=2,
        )
        self.mark_pill.pack(side=tk.LEFT, padx=(0, 8))

        # Filename
        self.lbl_filename = tk.Label(
            self.status_frame, text="", bg=COLOR_STATUS_BG, fg=COLOR_FILENAME,
            font=("Helvetica", 12),
        )
        self.lbl_filename.pack(side=tk.LEFT, padx=4)

        # Right section: hints and summary
        right_frame = tk.Frame(self.status_frame, bg=COLOR_STATUS_BG)
        right_frame.pack(side=tk.RIGHT, padx=(0, 12))

        self.hints_frame = tk.Frame(right_frame, bg=COLOR_STATUS_BG)
        self.hints_frame.pack(side=tk.RIGHT)

        # Separator before summary
        sep2 = tk.Frame(self.status_frame, bg="#3f3f46", width=1)
        sep2.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=8)

        self.lbl_summary = tk.Label(
            self.status_frame, text="", bg=COLOR_STATUS_BG, fg=COLOR_STATUS_FG,
            font=("Helvetica", 12),
        )
        self.lbl_summary.pack(side=tk.RIGHT)

        self._build_hints()

        # Handle resize
        self.canvas.bind("<Configure>", lambda e: self._show_current())

    def _build_hints(self, review=False):
        """Build pill-shaped keyboard hint badges."""
        for w in self.hints_frame.winfo_children():
            w.destroy()

        if review:
            hints = [
                ("K", "keep"), ("U", "unmark"), ("\u2190\u2192", "nav"),
                ("\u21b5", "sort"), ("Esc", "cancel"),
            ]
        else:
            hints = [
                ("K", "keep"), ("X", "del"), ("U", "clear"), ("Z", "undo"),
                ("R/L", "rotate"), ("\u2190\u2192", "nav"), ("G", "go to"),
                ("\u21b5", "sort"), ("Esc", "quit"),
            ]

        bg = COLOR_REVIEW_BG if review else COLOR_STATUS_BG

        for i, (key, label) in enumerate(hints):
            pill = tk.Frame(self.hints_frame, bg=bg)
            pill.pack(side=tk.LEFT, padx=2)

            tk.Label(
                pill, text=f" {key} ", bg=COLOR_HINT_KEY_BG, fg=COLOR_HINT_KEY_FG,
                font=("Menlo", 10, "bold"), padx=2, pady=1,
            ).pack(side=tk.LEFT)
            tk.Label(
                pill, text=label, bg=bg, fg="#52525b",
                font=("Helvetica", 10), padx=3,
            ).pack(side=tk.LEFT)

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
        self.root.bind("<g>", lambda e: self._jump_to())
        self.root.bind("<G>", lambda e: self._jump_to())
        self.root.bind("<Return>", lambda e: self._execute_sort())
        self.root.bind("<Escape>", lambda e: self._escape())

    def _navigate(self, delta: int):
        new_index = self.index + delta
        if 0 <= new_index < self.model.count:
            self.index = new_index
            self._show_current()

    def _jump_to(self):
        """Open a small dialog to jump to a specific photo number."""
        jump_win = tk.Toplevel(self.root)
        jump_win.title("Go to photo")
        jump_win.configure(bg=COLOR_STATUS_BG)
        jump_win.resizable(False, False)
        jump_win.transient(self.root)
        jump_win.grab_set()

        tk.Label(
            jump_win, bg=COLOR_STATUS_BG, fg=COLOR_STATUS_FG,
            font=("Helvetica", 13),
            text=f"Jump to photo (1\u2013{self.model.count}):",
            padx=15, pady=10,
        ).pack()

        entry = tk.Entry(
            jump_win, font=("Menlo", 16), width=8, justify=tk.CENTER,
        )
        entry.pack(padx=15, pady=10)
        entry.focus_set()

        def _go(*_args):
            try:
                num = int(entry.get())
                if 1 <= num <= self.model.count:
                    self.index = num - 1
                    jump_win.destroy()
                    self._show_current()
                    return
            except ValueError:
                pass
            entry.delete(0, tk.END)

        entry.bind("<Return>", _go)
        jump_win.bind("<Escape>", lambda e: jump_win.destroy())

        jump_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - jump_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - jump_win.winfo_height()) // 2
        jump_win.geometry(f"+{x}+{y}")

    def _mark(self, mark):
        path = self.model.images[self.index]
        if mark is MARK_NONE:
            self.model.set_mark(path, MARK_NONE)
            self._update_status()
        else:
            self.model.set_mark(path, mark)
            self._flash_overlay(mark)
            # Auto-advance after a brief moment
            if self.index < self.model.count - 1:
                self.index += 1
            self._show_current()

    def _flash_overlay(self, mark):
        """Show a brief overlay label on the canvas indicating the mark."""
        if self._flash_id:
            self.root.after_cancel(self._flash_id)
            self.canvas.delete("overlay")

        text = "KEEP" if mark == MARK_KEEP else "DELETE"
        color = COLOR_OVERLAY_KEEP if mark == MARK_KEEP else COLOR_OVERLAY_DELETE

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        # Semi-transparent background rectangle
        pad_x, pad_y = 60, 20
        font = ("Helvetica", 48, "bold")
        text_id = self.canvas.create_text(
            cw // 2, ch // 2, text=text, fill=color,
            font=font, tags="overlay",
        )
        bbox = self.canvas.bbox(text_id)
        if bbox:
            self.canvas.create_rectangle(
                bbox[0] - pad_x, bbox[1] - pad_y,
                bbox[2] + pad_x, bbox[3] + pad_y,
                fill="#000000", outline=color, width=2,
                stipple="gray50", tags="overlay",
            )
            # Re-draw text on top of rectangle
            self.canvas.delete(text_id)
            self.canvas.create_text(
                cw // 2, ch // 2, text=text, fill=color,
                font=font, tags="overlay",
            )

        self._flash_id = self.root.after(
            OVERLAY_FLASH_MS, lambda: self.canvas.delete("overlay")
        )

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

        # Position counter
        if self._in_review:
            pos_text = f"{self._review_pos + 1}/{len(self._delete_review_list)}"
            self.lbl_position.config(text=pos_text, fg=COLOR_REVIEW_ACCENT)
        else:
            pos_text = f"{self.index + 1}/{self.model.count}"
            self.lbl_position.config(text=pos_text, fg=COLOR_POSITION)

        self.lbl_filename.config(text=filename)

        # Mark pill badge
        if mark == MARK_KEEP:
            self.mark_pill.config(
                text=" KEEP ", fg=COLOR_KEEP, bg=COLOR_KEEP_PILL_BG,
            )
        elif mark == MARK_DELETE:
            self.mark_pill.config(
                text=" DELETE ", fg=COLOR_DELETE, bg=COLOR_DELETE_PILL_BG,
            )
        else:
            self.mark_pill.config(
                text=" UNMARKED ", fg=COLOR_UNMARKED, bg=COLOR_UNMARKED_PILL_BG,
            )

        # Summary with colored counts
        self.lbl_summary.config(
            text=f"Keep:{summary['keep']}  Del:{summary['delete']}  Unmarked:{summary['unmarked']}"
        )

        # Window title
        mode = " [REVIEW]" if self._in_review else ""
        self.root.title(
            f"RAW Culler \u2014 {self.folder_name} ({pos_text}){mode}"
        )

    def _set_review_theme(self, active: bool):
        """Switch status bar between normal and review mode styling."""
        bg = COLOR_REVIEW_BG if active else COLOR_STATUS_BG
        accent = COLOR_REVIEW_ACCENT if active else "#27272a"

        self.status_frame.config(bg=bg)
        self.accent_line.config(bg=accent)
        self.lbl_position.master.config(bg=bg)
        self.lbl_position.config(bg=bg)
        self.lbl_filename.config(bg=bg)
        self.lbl_summary.config(bg=bg)
        self.mark_pill.master.config(bg=bg)

        # Update hint pill backgrounds
        self._build_hints(review=active)

    def _start_review_deletes(self, session_only=False):
        """Enter review mode: cycle through delete-marked images only."""
        self._delete_review_list = [
            i for i, p in enumerate(self.model.images)
            if self.model.get_mark(p) == MARK_DELETE
            and (not session_only or self.model.initial_marks.get(p) != MARK_DELETE)
        ]
        if not self._delete_review_list:
            self._finish_sort()
            return

        self._review_pos = 0
        self._in_review = True
        self._set_review_theme(True)

        # Temporarily rebind keys for review mode
        self.root.unbind("<Return>")
        self.root.bind("<Return>", lambda e: self._finish_sort())
        self.root.bind("<Right>", lambda e: self._review_navigate(1))
        self.root.bind("<Left>", lambda e: self._review_navigate(-1))

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
        self._set_review_theme(False)
        self.root.unbind("<Return>")
        self.root.unbind("<Right>")
        self.root.unbind("<Left>")
        self.root.bind("<Right>", lambda e: self._navigate(1))
        self.root.bind("<Left>", lambda e: self._navigate(-1))
        self.root.bind("<Return>", lambda e: self._execute_sort())

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
            session_deletes = sum(
                1 for p in self.model.images
                if self.model.get_mark(p) == MARK_DELETE
                and self.model.initial_marks.get(p) != MARK_DELETE
            )

            if session_deletes > 0 and session_deletes < summary["delete"]:
                # Mix of session and pre-existing deletes — offer choice
                review_win = tk.Toplevel(self.root)
                review_win.title("Review Deletes")
                review_win.configure(bg=COLOR_STATUS_BG)
                review_win.resizable(False, False)
                review_win.transient(self.root)
                review_win.grab_set()

                tk.Label(
                    review_win, bg=COLOR_STATUS_BG, fg=COLOR_STATUS_FG,
                    font=("Helvetica", 13),
                    text=(
                        f"You have {summary['delete']} total files marked for deletion:\n"
                        f"  {session_deletes} marked this session\n"
                        f"  {summary['delete'] - session_deletes} from a previous session\n\n"
                        "What would you like to review?"
                    ),
                    justify=tk.LEFT, padx=20, pady=15,
                ).pack()

                btn_frame = tk.Frame(review_win, bg=COLOR_STATUS_BG)
                btn_frame.pack(pady=(0, 15))

                def _review(session_only):
                    review_win.destroy()
                    self._start_review_deletes(session_only=session_only)

                tk.Button(btn_frame, text=f"This session only ({session_deletes})",
                          command=lambda: _review(True), width=25).pack(pady=3)
                tk.Button(btn_frame, text=f"All deletes ({summary['delete']})",
                          command=lambda: _review(False), width=25).pack(pady=3)
                tk.Button(btn_frame, text="Skip review",
                          command=lambda: (review_win.destroy(), self._finish_sort()),
                          width=25).pack(pady=3)

                review_win.update_idletasks()
                x = self.root.winfo_x() + (self.root.winfo_width() - review_win.winfo_width()) // 2
                y = self.root.winfo_y() + (self.root.winfo_height() - review_win.winfo_height()) // 2
                review_win.geometry(f"+{x}+{y}")
                return
            else:
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
