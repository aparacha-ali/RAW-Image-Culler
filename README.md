# RAW Image Culler

A fast, keyboard-driven desktop tool for reviewing and sorting large batches of RAW photos. 

## Features

- **Fast previews** — Uses macOS `sips` to extract previews from RAW files without full demosaicing
- **Threaded preloading** — Background thread pool keeps the next 5 images ready in memory for instant navigation
- **Keyboard-first workflow** — Mark, navigate, undo, and sort without touching the mouse
- **Non-destructive** — Files are moved into `keep/` and `delete/` subfolders, never deleted
- **Re-processable** — Run again on the same folder to review previous decisions and change marks
- **Session tracking** — Distinguishes between marks made this session vs. previous sessions during delete review
- **Image rotation** — Rotate images for proper viewing (display-only, doesn't modify files)

## Supported RAW Formats

CR2, CR3, NEF, ARW, ORF, RAF, DNG, RW2, PEF, SRW

## Requirements

- macOS (uses built-in `sips` for RAW conversion)
- Python 3.10+
- Pillow

## Setup

```bash
cd raw_culler
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# With a folder path
python main.py /path/to/raw/photos

# Or launch a folder picker
python main.py
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `K` | Mark as keep + auto-advance |
| `X` | Mark as delete + auto-advance |
| `U` | Clear mark |
| `Z` | Undo last mark |
| `R` | Rotate 90° clockwise |
| `L` | Rotate 90° counter-clockwise |
| `N` | Jump to first unmarked photo |
| `←` `→` | Navigate between images |
| `Enter` | Execute sort (with confirmation) |
| `Esc` | Quit (or cancel review mode) |

## Workflow

1. Open a folder of RAW images
2. Fly through images with arrow keys
3. Press `K` to keep, `X` to delete — each auto-advances to the next image
4. Press `Enter` when done — review deletes if needed, then files are sorted into `keep/` and `delete/` subfolders
5. Unmarked files stay in place

## Project Structure

```
raw_culler/
    main.py            # Entry point, folder selection
    app.py             # Tkinter UI, key bindings, display loop
    image_loader.py    # RAW preview extraction, threaded preloading, LRU cache
    culler_model.py    # Data model: image list, marks, undo stack
    file_mover.py      # Move files into keep/delete folders
    constants.py       # Config: supported extensions, colors, cache size
    requirements.txt   # Python dependencies
```

## License

MIT
