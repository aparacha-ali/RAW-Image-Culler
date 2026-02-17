"""Configuration constants for RAW Image Culler."""

SUPPORTED_EXTENSIONS = {
    ".cr2", ".cr3", ".nef", ".arw", ".orf",
    ".raf", ".dng", ".rw2", ".pef", ".srw",
}

# Cache: current image ± PRELOAD_AHEAD/BEHIND
PRELOAD_AHEAD = 5
PRELOAD_BEHIND = 5
CACHE_SIZE = PRELOAD_AHEAD + PRELOAD_BEHIND + 1  # 11

THREAD_POOL_WORKERS = 4

# Marks
MARK_KEEP = "keep"
MARK_DELETE = "delete"
MARK_NONE = None

# Subfolder names for sorting
KEEP_FOLDER = "keep"
DELETE_FOLDER = "delete"

# UI colors
COLOR_BG = "#0a0a0a"
COLOR_KEEP = "#34d399"
COLOR_DELETE = "#f87171"
COLOR_UNMARKED = "#6b7280"
COLOR_STATUS_BG = "#18181b"
COLOR_STATUS_FG = "#a1a1aa"
COLOR_FILENAME = "#e4e4e7"
COLOR_POSITION = "#f4f4f5"
COLOR_REVIEW_BG = "#292524"
COLOR_REVIEW_ACCENT = "#f59e0b"

# Pill badge colors (background tints)
COLOR_KEEP_PILL_BG = "#064e3b"
COLOR_DELETE_PILL_BG = "#7f1d1d"
COLOR_UNMARKED_PILL_BG = "#27272a"

# Keyboard hint styling
COLOR_HINT_KEY_BG = "#27272a"
COLOR_HINT_KEY_FG = "#a1a1aa"

# Mark overlay flash
OVERLAY_FLASH_MS = 400
COLOR_OVERLAY_KEEP = "#34d399"
COLOR_OVERLAY_DELETE = "#f87171"

# Status bar height
STATUS_BAR_HEIGHT = 48
