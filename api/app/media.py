from __future__ import annotations

import json
import re
import shutil
import threading
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from . import config
from .images import process_to_jpeg

_lock = threading.Lock()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def ensure_dirs() -> None:
    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    config.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


def load_manifest() -> list[dict[str, Any]]:
    items = _read_json(config.MANIFEST_PATH, [])
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict) and i.get("slug") and i.get("kind")]


def load_deleted() -> set[str]:
    items = _read_json(config.DELETED_PATH, [])
    if not isinstance(items, list):
        return set()
    return {str(s) for s in items}


def save_manifest(items: list[dict[str, Any]]) -> None:
    _write_json(config.MANIFEST_PATH, items)


def save_deleted(slugs: set[str]) -> None:
    _write_json(config.DELETED_PATH, sorted(slugs))


def _public_item(item: dict[str, Any]) -> dict[str, str]:
    slug = str(item["slug"])
    kind = str(item.get("kind") or "image")
    title = str(item.get("title") or slug)
    if kind == "video":
        ext = str(item.get("ext") or "mp4")
        out: dict[str, str] = {
            "slug": slug,
            "kind": "video",
            "title": title,
            "url": f"/media/videos/{slug}.{ext}",
            "category": "video",
        }
        poster = item.get("poster")
        if poster:
            out["poster"] = f"/media/images/{poster}.jpg"
        return out
    return {
        "slug": slug,
        "kind": "image",
        "title": title,
        "url": f"/media/images/{slug}.jpg",
        "category": "works",
    }


def public_items(
    items: list[dict[str, Any]] | None = None,
    kind: str | None = None,
) -> list[dict[str, str]]:
    if items is None:
        items = load_manifest()
    out: list[dict[str, str]] = []
    for item in items:
        if kind and str(item.get("kind")) != kind:
            continue
        out.append(_public_item(item))
    # Videos first (site gallery), then studio images — preserve relative order within kind.
    out.sort(key=lambda i: 0 if i.get("kind") == "video" else 1)
    return out


def merge_seed() -> None:
    """Additively copy seed media into the volume. Never overwrite or revive deleted."""
    ensure_dirs()
    seed_manifest_path = config.SEED_DIR / "manifest.json"
    seed_images = config.SEED_DIR / "images"
    seed_videos = config.SEED_DIR / "videos"
    seed_items = _read_json(seed_manifest_path, [])
    if not isinstance(seed_items, list):
        seed_items = []

    with _lock:
        deleted = load_deleted()
        manifest = load_manifest()
        by_slug = {str(i["slug"]): i for i in manifest}
        changed = False

        for item in seed_items:
            if not isinstance(item, dict) or not item.get("slug") or not item.get("kind"):
                continue
            slug = str(item["slug"])
            kind = str(item["kind"])
            if slug in deleted:
                continue

            if kind == "image":
                src = seed_images / f"{slug}.jpg"
                dest = config.IMAGES_DIR / f"{slug}.jpg"
            elif kind == "video":
                ext = str(item.get("ext") or "mp4")
                src = seed_videos / f"{slug}.{ext}"
                dest = config.VIDEOS_DIR / f"{slug}.{ext}"
            else:
                continue

            if not src.exists():
                continue

            if slug not in by_slug:
                shutil.copy2(src, dest)
                entry = {
                    "slug": slug,
                    "kind": kind,
                    "title": str(item.get("title") or slug),
                    "source": "seed",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                if kind == "video":
                    entry["ext"] = str(item.get("ext") or "mp4")
                    if item.get("poster"):
                        entry["poster"] = str(item["poster"])
                manifest.append(entry)
                by_slug[slug] = entry
                changed = True
            elif not dest.exists():
                shutil.copy2(src, dest)

        if changed or not config.MANIFEST_PATH.exists():
            save_manifest(manifest)
        if not config.DELETED_PATH.exists():
            save_deleted(deleted)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    value = re.sub(r"-{2,}", "-", value)
    return value[:60] or "media"


def unique_slug(base: str, existing: set[str]) -> str:
    candidate = base
    n = 2
    while candidate in existing:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def add_image(raw_bytes: bytes, filename: str, title: str) -> dict[str, str]:
    ensure_dirs()
    stem = Path(filename).stem
    base = slugify(stem) or f"image-{uuid.uuid4().hex[:8]}"
    title = (title or stem or base).strip()[:120]

    with _lock:
        manifest = load_manifest()
        deleted = load_deleted()
        existing = {str(i["slug"]) for i in manifest} | deleted
        slug = unique_slug(base, existing)

        dest = config.IMAGES_DIR / f"{slug}.jpg"
        tmp = config.IMAGES_DIR / f".{slug}.{uuid.uuid4().hex}.upload"
        try:
            tmp.write_bytes(raw_bytes)
            ImageOps.exif_transpose(Image.open(tmp)).convert("RGB")
            process_to_jpeg(tmp, dest)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)

        if slug in deleted:
            deleted.discard(slug)
            save_deleted(deleted)

        entry = {
            "slug": slug,
            "kind": "image",
            "title": title,
            "source": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        # Newest studio works first
        manifest.insert(0, entry)
        save_manifest(manifest)

    return _public_item(entry)


def add_video(raw_bytes: bytes, filename: str, title: str) -> dict[str, str]:
    ensure_dirs()
    stem = Path(filename).stem
    ext = Path(filename).suffix.lower().lstrip(".") or "mp4"
    if ext not in {"mp4", "webm"}:
        raise ValueError("Only MP4 or WEBM videos are allowed")
    base = slugify(stem) or f"video-{uuid.uuid4().hex[:8]}"
    title = (title or stem or base).strip()[:120]

    with _lock:
        manifest = load_manifest()
        deleted = load_deleted()
        existing = {str(i["slug"]) for i in manifest} | deleted
        slug = unique_slug(base, existing)

        dest = config.VIDEOS_DIR / f"{slug}.{ext}"
        dest.write_bytes(raw_bytes)

        if slug in deleted:
            deleted.discard(slug)
            save_deleted(deleted)

        entry = {
            "slug": slug,
            "kind": "video",
            "ext": ext,
            "title": title,
            "source": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest.insert(0, entry)
        save_manifest(manifest)

    return _public_item(entry)


def delete_item(slug: str) -> bool:
    slug = slug.strip()
    if not slug or "/" in slug or "\\" in slug or ".." in slug:
        return False

    with _lock:
        manifest = load_manifest()
        deleted = load_deleted()
        removed = [i for i in manifest if str(i.get("slug")) == slug]
        new_manifest = [i for i in manifest if str(i.get("slug")) != slug]
        save_manifest(new_manifest)
        deleted.add(slug)
        save_deleted(deleted)

        img = config.IMAGES_DIR / f"{slug}.jpg"
        if img.exists():
            img.unlink(missing_ok=True)
        for item in removed:
            if str(item.get("kind")) == "video":
                ext = str(item.get("ext") or "mp4")
                vid = config.VIDEOS_DIR / f"{slug}.{ext}"
                if vid.exists():
                    vid.unlink(missing_ok=True)
        for path in config.VIDEOS_DIR.glob(f"{slug}.*"):
            path.unlink(missing_ok=True)
        return True


def image_path(filename: str) -> Path | None:
    name = Path(filename).name
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]*\.jpg", name):
        return None
    path = config.IMAGES_DIR / name
    if path.exists() and path.is_file():
        return path
    return None


def video_path(filename: str) -> Path | None:
    name = Path(filename).name
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]*\.(mp4|webm)", name):
        return None
    path = config.VIDEOS_DIR / name
    if path.exists() and path.is_file():
        return path
    return None
