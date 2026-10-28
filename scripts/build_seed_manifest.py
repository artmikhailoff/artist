# -*- coding: utf-8 -*-
"""Build seed/manifest.json from studio assets + Russian titles."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLES = json.loads((ROOT / "scripts" / "studio-titles.json").read_text(encoding="utf-8"))
OUT = ROOT / "seed" / "manifest.json"


def main() -> None:
    items: list[dict] = []
    studio = ROOT / "assets" / "studio"
    for path in sorted(studio.glob("studio-*.jpg")):
        slug = path.stem
        items.append(
            {
                "slug": slug,
                "kind": "image",
                "title": TITLES.get(path.name, slug),
                "source": "seed",
            }
        )
    for path in sorted((studio / "videos").glob("*.mp4")):
        slug = path.stem
        poster = "studio-001" if slug.endswith("01") else "studio-002"
        items.append(
            {
                "slug": slug,
                "kind": "video",
                "ext": "mp4",
                "title": TITLES.get(path.name, slug),
                "poster": poster,
                "source": "seed",
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(items)} seed items -> {OUT}")


if __name__ == "__main__":
    main()
