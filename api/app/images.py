from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


def process_to_jpeg(src: Path, dest: Path) -> None:
    """Bake the site gallery look: slight saturate + contrast + sharpen."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        rgb = ImageOps.exif_transpose(im).convert("RGB")
        rgb = ImageEnhance.Color(rgb).enhance(1.08)
        rgb = ImageEnhance.Contrast(rgb).enhance(1.05)
        rgb = ImageEnhance.Sharpness(rgb).enhance(1.05)
        max_edge = 2400
        w, h = rgb.size
        if max(w, h) > max_edge:
            scale = max_edge / float(max(w, h))
            rgb = rgb.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        rgb.save(dest, "JPEG", quality=90, optimize=True)
