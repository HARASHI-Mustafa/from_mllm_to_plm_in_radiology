from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import UPLOADS_DIR


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _safe_upload_name(original_filename: str | None) -> str:
    extension = Path(original_filename or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image file type. Allowed extensions: {allowed}.",
        )
    return f"{uuid4().hex}{extension}"


async def save_uploaded_image(file: UploadFile) -> Path:
    filename = _safe_upload_name(file.filename)
    destination = UPLOADS_DIR / filename
    content = await file.read()
    destination.write_bytes(content)
    return destination
