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
COLOR_BG = "#000000"
COLOR_KEEP = "#00cc00"
COLOR_DELETE = "#ff3333"
COLOR_UNMARKED = "#888888"
COLOR_STATUS_BG = "#1a1a1a"
COLOR_STATUS_FG = "#cccccc"
COLOR_FILENAME = "#ffffff"

# Status bar height
STATUS_BAR_HEIGHT = 40
