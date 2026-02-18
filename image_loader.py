"""RAW preview extraction with threaded preloading and LRU cache.

Uses macOS built-in 'sips' to convert RAW files to JPEG, avoiding
third-party binary compatibility issues with rawpy/libraw.
"""

import os
import subprocess
import tempfile
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageOps

from constants import CACHE_SIZE, THREAD_POOL_WORKERS, PRELOAD_AHEAD, PRELOAD_BEHIND

# Shared temp directory for converted previews
_TEMP_DIR = tempfile.mkdtemp(prefix="raw_culler_")


def _extract_preview(path: str) -> Image.Image:
    """Convert RAW to JPEG using macOS sips and load it."""
    try:
        tmp_path = os.path.join(_TEMP_DIR, os.path.basename(path) + ".jpg")
        result = subprocess.run(
            ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "85",
             path, "--out", tmp_path],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0 and os.path.exists(tmp_path):
            img = Image.open(tmp_path)
            img.load()  # force read before we delete the temp file
            os.unlink(tmp_path)
            img = ImageOps.exif_transpose(img)
            return img
    except Exception:
        pass
    return _placeholder("No preview available")


def _placeholder(text: str, size=(800, 600)) -> Image.Image:
    """Create a dark placeholder image with centered text."""
    img = Image.new("RGB", size, (30, 30, 30))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size[0] - tw) // 2
    y = (size[1] - th) // 2
    draw.text((x, y), text, fill=(150, 150, 150), font=font)
    return img


class ImageLoader:
    def __init__(self, paths: List[str]):
        self.paths = paths
        self._cache: OrderedDict[str, Image.Image] = OrderedDict()
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=THREAD_POOL_WORKERS)

    def get(self, index: int) -> Image.Image:
        """Get image at index, loading if needed. Triggers preload."""
        if not self.paths:
            return _placeholder("No images found")
        path = self.paths[index]
        img = self._cache_get(path)
        if img is None:
            img = _extract_preview(path)
            self._cache_put(path, img)
        self._preload(index)
        return img

    def _preload(self, center: int):
        """Submit preload tasks for images around center index."""
        start = max(0, center - PRELOAD_BEHIND)
        end = min(len(self.paths), center + PRELOAD_AHEAD + 1)
        for i in range(start, end):
            path = self.paths[i]
            with self._lock:
                if path in self._cache:
                    continue
            self._pool.submit(self._load_into_cache, path)

    def _load_into_cache(self, path: str):
        with self._lock:
            if path in self._cache:
                return
        img = _extract_preview(path)
        self._cache_put(path, img)

    def _cache_get(self, path: str) -> Optional[Image.Image]:
        with self._lock:
            if path in self._cache:
                self._cache.move_to_end(path)
                return self._cache[path]
        return None

    def _cache_put(self, path: str, img: Image.Image):
        with self._lock:
            self._cache[path] = img
            self._cache.move_to_end(path)
            while len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)

    def shutdown(self):
        self._pool.shutdown(wait=False)
        # Clean up temp directory
        try:
            for f in os.listdir(_TEMP_DIR):
                os.unlink(os.path.join(_TEMP_DIR, f))
            os.rmdir(_TEMP_DIR)
        except Exception:
            pass
