from __future__ import annotations

import os
from pathlib import Path


DATA_DIR = Path(os.environ.get("ARTIST_DATA_DIR", "/data"))
SEED_DIR = Path(os.environ.get("ARTIST_SEED_DIR", "/seed"))

IMAGES_DIR = DATA_DIR / "images"
VIDEOS_DIR = DATA_DIR / "videos"
MANIFEST_PATH = DATA_DIR / "manifest.json"
DELETED_PATH = DATA_DIR / "deleted.json"

ADMIN_USER = os.environ.get("ADMIN_USER", "kasabov")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
SESSION_MAX_AGE = int(os.environ.get("SESSION_MAX_AGE", str(60 * 60 * 12)))
COOKIE_NAME = "artist_admin"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() in {"1", "true", "yes"}
MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", str(15 * 1024 * 1024)))
MAX_VIDEO_BYTES = int(os.environ.get("MAX_VIDEO_BYTES", str(100 * 1024 * 1024)))
LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "8"))
LOGIN_WINDOW_SEC = int(os.environ.get("LOGIN_WINDOW_SEC", "900"))
