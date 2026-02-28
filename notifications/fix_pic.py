"""
optimize_phone_screen.py

Takes a JPG image (e.g. from a webcam capturing a phone screen) and produces
an optimized PNG for AI text/notification parsing.

Steps:
  1. Auto-detect and crop the phone screen region (brightest rectangle)
  2. Fix EXIF orientation
  3. Enhance contrast & sharpness for text readability
  4. Resize to a sensible resolution (not too large, not too small)
  5. Save as optimized PNG (lossless, best for text)

Usage:
    python optimize_phone_screen.py input.jpg [output.png]
    python optimize_phone_screen.py input.jpg --no-crop   # skip auto-crop
"""

import sys
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    import numpy as np
except ImportError:
    print("Install dependencies: pip install Pillow numpy")
    sys.exit(1)


# ── Configuration ─────────────────────────────────────────────────────────────

# Target longest edge in pixels (good balance for AI APIs like Claude/GPT-4V)
TARGET_LONG_EDGE = 1280

# Enhancement tuning (1.0 = no change)
CONTRAST_FACTOR   = 1.5   # boost contrast for text legibility
SHARPNESS_FACTOR  = 1.8   # sharpen slightly
BRIGHTNESS_FACTOR = 1.1   # slight brightness bump for dim screens


# ── Core functions ─────────────────────────────────────────────────────────────

def load_image(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")


def auto_crop_screen(img: Image.Image, padding: int = 10) -> Image.Image:
    """
    Isolate the phone screen by finding the brightest rectangular region.
    Falls back to the full image if detection looks unreliable.
    """
    gray = img.convert("L")
    arr = np.array(gray)

    # Keep pixels brighter than the 80th percentile
    threshold = np.percentile(arr, 80)
    bright_mask = arr > threshold

    rows = np.any(bright_mask, axis=1)
    cols = np.any(bright_mask, axis=0)

    if not rows.any() or not cols.any():
        print("  [crop] No bright region found, using full image.")
        return img

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    # Sanity check: cropped area should be at least 20% of the original
    crop_area = (rmax - rmin) * (cmax - cmin)
    full_area = arr.shape[0] * arr.shape[1]
    if crop_area < 0.20 * full_area:
        print("  [crop] Detected region too small, using full image.")
        return img

    h, w = arr.shape
    left   = max(0, cmin - padding)
    top    = max(0, rmin - padding)
    right  = min(w, cmax + padding)
    bottom = min(h, rmax + padding)

    print(f"  [crop] Cropped to ({left},{top}) -> ({right},{bottom})")
    return img.crop((left, top, right, bottom))


def resize_for_ai(img: Image.Image, max_long_edge: int = TARGET_LONG_EDGE) -> Image.Image:
    """Resize so the longest edge equals max_long_edge, preserving aspect ratio."""
    w, h = img.size
    long_edge = max(w, h)
    if long_edge <= max_long_edge:
        return img
    scale = max_long_edge / long_edge
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def enhance_for_text(img: Image.Image) -> Image.Image:
    """Boost contrast, sharpness, and brightness so text is crisp and clear."""
    img = ImageEnhance.Contrast(img).enhance(CONTRAST_FACTOR)
    img = ImageEnhance.Sharpness(img).enhance(SHARPNESS_FACTOR)
    img = ImageEnhance.Brightness(img).enhance(BRIGHTNESS_FACTOR)
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
    return img


def fix_orientation(img: Image.Image) -> Image.Image:
    """Respect EXIF orientation tag (e.g. rotated phone/webcam photos)."""
    return ImageOps.exif_transpose(img)


def save_png(img: Image.Image, output_path: str):
    img.save(output_path, format="PNG", optimize=True, compress_level=7)
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  [save] Saved {output_path} -- {size_kb:.1f} KB")


# ── Main pipeline ──────────────────────────────────────────────────────────────

def process_image(input_path: str, output_path: str = None, crop: bool = True):
    input_path = Path(input_path)
    if output_path is None:
        output_path = str(input_path.stem) + "_optimized.png"

    print(f"\nProcessing: {input_path}")

    img = load_image(str(input_path))
    print(f"  [load]   Original size: {img.size[0]}x{img.size[1]}")

    img = fix_orientation(img)

    if crop:
        img = auto_crop_screen(img)
        print(f"  [crop]   After crop: {img.size[0]}x{img.size[1]}")

    img = resize_for_ai(img)
    print(f"  [resize] After resize: {img.size[0]}x{img.size[1]}")

    img = enhance_for_text(img)
    print(f"  [enhance] Contrast x{CONTRAST_FACTOR}, Sharpness x{SHARPNESS_FACTOR}")

    save_png(img, output_path)
    print(f"  Done -> {output_path}")
    return output_path


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Optimize a phone-screen JPG for AI text/notification parsing."
    )
    parser.add_argument("input", help="Input JPG (or any image) file")
    parser.add_argument("output", nargs="?", help="Output PNG file (default: <input>_optimized.png)")
    parser.add_argument(
        "--no-crop", action="store_true",
        help="Skip auto-crop; process the full frame"
    )

    args = parser.parse_args()
    process_image(args.input, args.output, crop=not args.no_crop)


if __name__ == "__main__":
    main()