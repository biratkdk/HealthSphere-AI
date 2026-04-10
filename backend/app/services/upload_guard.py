from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, status
from PIL import Image
from pydicom import dcmread
from pydicom.errors import InvalidDicomError

from backend.app.core.config import get_settings


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".dcm"}

# Magic byte signatures used to verify file content matches its declared type.
# Checked before Pillow parsing to reject mismatched or crafted files early.
_MAGIC_BYTES: dict[str, bytes] = {
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}

_DICOM_CONTENT_TYPES = {"application/dicom", "application/dicom+json", "application/octet-stream"}


def _validate_dicom_payload(payload: bytes) -> None:
    try:
        dataset = dcmread(BytesIO(payload), force=True)
    except InvalidDicomError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded DICOM study could not be parsed.",
        ) from exc

    if "PixelData" not in dataset:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded DICOM study does not contain image pixel data.",
        )

    try:
        _ = dataset.pixel_array
    except Exception as exc:  # pragma: no cover - codec dependent
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded DICOM study could not be decoded.",
        ) from exc


def validate_imaging_upload(filename: str | None, content_type: str | None, payload: bytes) -> None:
    settings = get_settings()
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A filename is required for imaging uploads.")
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    if len(payload) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="The uploaded file exceeds the allowed size limit.")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PNG, JPEG, and DICOM uploads are supported.",
        )

    if extension == ".dcm":
        if content_type and content_type.lower() not in (_DICOM_CONTENT_TYPES | settings.imaging_content_types):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported imaging content type.")
        _validate_dicom_payload(payload)
        return

    if content_type and content_type.lower() not in settings.imaging_content_types:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported imaging content type.")

    # Verify magic bytes before handing off to Pillow — this catches files
    # whose extension/content-type was spoofed (e.g. a PHP script named .jpg).
    expected_magic = _MAGIC_BYTES.get(extension, b"")
    if expected_magic and not payload.startswith(expected_magic):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file does not match its declared type.",
        )

    try:
        with Image.open(BytesIO(payload)) as image:
            if image.format not in {"PNG", "JPEG"}:
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="The uploaded payload is not a supported image.")
            image.verify()
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - pillow validation
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded image could not be verified.") from exc
