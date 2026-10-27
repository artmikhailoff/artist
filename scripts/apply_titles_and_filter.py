# -*- coding: utf-8 -*-
"""Apply Russian titles to works-data.js and gallery look filter to studio JPGs."""
from __future__ import annotations

import json
import pathlib

from PIL import Image, ImageEnhance

ROOT = pathlib.Path(__file__).resolve().parents[1]
TITLES = json.loads((ROOT / "scripts" / "studio-titles.json").read_text(encoding="utf-8"))
STUDIO = ROOT / "assets" / "studio"


def rebuild_works_data() -> int:
    studio = sorted(STUDIO.glob("studio-*.jpg"))
    lines = ["window.KASABOV_WORKS = ["]

    for i, vid in enumerate(["studio-video-01.mp4", "studio-video-02.mp4"], 1):
        poster = f"studio-{i:03d}.jpg"
        title = TITLES[vid]
        lines.append(
            "  { type: \"video\", category: \"video\", "
            f'src: "assets/studio/videos/{vid}", poster: "assets/studio/{poster}", '
            f'title: "{title}", capKey: "capVideo" }},'
        )

    for path in studio:
        title = TITLES[path.name]
        lines.append(
            "  { type: \"image\", category: \"studio\", "
            f'src: "assets/studio/{path.name}", title: "{title}", capKey: "capStudio" }},'
        )

    archive = [
        ("assets/artworks/facebook/fb-05.jpg", "workFbRecent", "capFbRecent"),
        ("assets/artworks/facebook/fb-03.jpg", "workFbRecent", "capFbRecent"),
        ("assets/artworks/facebook/fb-04.jpg", "workFbRecent", "capFbRecent"),
        ("assets/artworks/facebook/fb-02.jpg", "workFbStudio", "capFbRecent"),
        ("assets/artworks/facebook/fb-06.jpg", "workFbRecent", "capFbRecent"),
        ("assets/artworks/facebook/fb-07.jpg", "workFbRecent", "capFbRecent"),
        ("assets/artworks/14-angels-1990.jpg", "workAngels", "capAngels"),
        ("assets/artworks/10-visage.jpg", "workVisage", "capVisage"),
        ("assets/artworks/16-nuit-dete-1990.jpg", "workNuit", "capNuit"),
        ("assets/artworks/01-untitled.jpg", "workUntitled", "capUntitled2021"),
    ]
    for src, title_key, cap_key in archive:
        lines.append(
            "  { type: \"image\", category: \"archive\", "
            f'src: "{src}", titleKey: "{title_key}", capKey: "{cap_key}" }},'
        )

    lines[-1] = lines[-1].rstrip(",")
    lines.append("];")
    (ROOT / "works-data.js").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(studio)


def apply_gallery_filter() -> int:
    """Bake the site gallery look: slight saturate + contrast (matches CSS)."""
    count = 0
    for path in sorted(STUDIO.glob("studio-*.jpg")):
        with Image.open(path) as im:
            rgb = im.convert("RGB")
            rgb = ImageEnhance.Color(rgb).enhance(1.08)
            rgb = ImageEnhance.Contrast(rgb).enhance(1.05)
            rgb = ImageEnhance.Sharpness(rgb).enhance(1.05)
            rgb.save(path, "JPEG", quality=90, optimize=True)
        count += 1
    return count


if __name__ == "__main__":
    n_img = rebuild_works_data()
    n_filt = apply_gallery_filter()
    print(f"titles wired for {n_img} studio images + 2 videos")
    print(f"filter applied to {n_filt} jpgs")
