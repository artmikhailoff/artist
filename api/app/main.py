from __future__ import annotations

from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse

from . import config
from .auth import (
    clear_login_failures,
    create_session_token,
    login_allowed,
    read_session_token,
    record_login_failure,
    verify_password,
)
from .media import (
    add_image,
    add_video,
    delete_item,
    image_path,
    merge_seed,
    public_items,
    video_path,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not config.SECRET_KEY:
        raise RuntimeError("SECRET_KEY env var is required")
    if not config.ADMIN_PASSWORD_HASH:
        raise RuntimeError("ADMIN_PASSWORD_HASH env var is required")
    merge_seed()
    yield


app = FastAPI(title="Kasabov Studio API", docs_url=None, redoc_url=None, lifespan=lifespan)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def require_admin(request: Request) -> str:
    token = request.cookies.get(config.COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = read_session_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=config.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=config.SESSION_MAX_AGE,
        path="/",
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/gallery")
def gallery() -> dict:
    return {"items": public_items()}


@app.get("/api/me")
def me(user: str = Depends(require_admin)) -> dict[str, str]:
    return {"user": user}


@app.post("/api/login")
async def login(request: Request, response: Response) -> dict[str, str]:
    ip = client_ip(request)
    if not login_allowed(ip):
        raise HTTPException(status_code=429, detail="Too many attempts. Try later.")

    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))

    if username != config.ADMIN_USER or not verify_password(password):
        record_login_failure(ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    clear_login_failures(ip)
    token = create_session_token(username)
    set_session_cookie(response, token)
    return {"user": username}


@app.post("/api/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(config.COOKIE_NAME, path="/")
    return {"ok": True}


@app.post("/api/photos")
async def upload_photo(
    title: str = Form(""),
    file: UploadFile = File(...),
    _user: str = Depends(require_admin),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, or WEBP uploads are allowed")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > config.MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 15 MB)")

    try:
        item = add_image(data, file.filename, title)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}") from exc
    return {"item": item}


@app.post("/api/videos")
async def upload_video(
    title: str = Form(""),
    file: UploadFile = File(...),
    _user: str = Depends(require_admin),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp4", ".webm"}:
        raise HTTPException(status_code=400, detail="Only MP4 or WEBM uploads are allowed")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > config.MAX_VIDEO_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 100 MB)")

    try:
        item = add_video(data, file.filename, title)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not store video: {exc}") from exc
    return {"item": item}


@app.delete("/api/media/{slug}")
def remove_media(slug: str, _user: str = Depends(require_admin)) -> dict[str, bool]:
    ok = delete_item(slug)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid slug")
    return {"ok": True}


@app.get("/media/images/{filename}")
def media_image(filename: str) -> FileResponse:
    path = image_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=604800"},
    )


@app.get("/media/videos/{filename}")
def media_video(filename: str) -> FileResponse:
    path = video_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Not found")
    media_type = "video/webm" if path.suffix.lower() == ".webm" else "video/mp4"
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=604800"},
    )
