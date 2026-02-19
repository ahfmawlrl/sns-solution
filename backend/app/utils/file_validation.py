"""File upload validation with MIME + magic byte dual verification.

Security measures:
- Content-Type header check against allowlist
- Magic byte detection for real file type verification
- File size limits per type
- Filename sanitization (UUID regeneration, path traversal block)
- Platform-specific aspect ratio recommendations
"""
import logging
import os
import re
import uuid
from enum import Enum

logger = logging.getLogger(__name__)


class FileType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"


ALLOWED_MIMES: dict[str, list[str]] = {
    "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
    "video": ["video/mp4", "video/quicktime", "video/x-msvideo"],
    "document": ["application/pdf"],
}

MAX_SIZES: dict[str, int] = {
    "image": 20_971_520,       # 20 MB
    "video": 524_288_000,      # 500 MB
    "document": 10_485_760,    # 10 MB
}

EXTENSION_MAP: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "application/pdf": ".pdf",
}

# Magic byte signatures for file type detection
MAGIC_SIGNATURES: dict[str, list[tuple[bytes, int]]] = {
    "image/jpeg": [(b"\xff\xd8\xff", 0)],
    "image/png": [(b"\x89PNG\r\n\x1a\n", 0)],
    "image/gif": [(b"GIF87a", 0), (b"GIF89a", 0)],
    "image/webp": [(b"RIFF", 0)],  # RIFF....WEBP
    "video/mp4": [(b"ftyp", 4)],   # ....ftyp
    "video/quicktime": [(b"ftyp", 4), (b"moov", 4), (b"free", 4), (b"mdat", 4)],
    "video/x-msvideo": [(b"RIFF", 0)],  # RIFF....AVI
    "application/pdf": [(b"%PDF", 0)],
}

# Platform aspect ratios
PLATFORM_ASPECT_RATIOS = {
    "instagram_feed": (1, 1),
    "instagram_portrait": (4, 5),
    "instagram_story": (9, 16),
    "facebook_link": (1.91, 1),
    "youtube_thumbnail": (16, 9),
}


class FileValidationError(ValueError):
    """Raised when file validation fails."""
    pass


def detect_mime_by_magic(file_bytes: bytes) -> str | None:
    """Detect MIME type by examining magic bytes."""
    if len(file_bytes) < 12:
        return None

    for mime, signatures in MAGIC_SIGNATURES.items():
        for magic_bytes, offset in signatures:
            end = offset + len(magic_bytes)
            if len(file_bytes) >= end and file_bytes[offset:end] == magic_bytes:
                # Special checks for ambiguous RIFF-based formats
                if mime == "image/webp" and len(file_bytes) >= 12:
                    if file_bytes[8:12] == b"WEBP":
                        return "image/webp"
                    continue
                if mime == "video/x-msvideo" and len(file_bytes) >= 12:
                    if file_bytes[8:12] == b"AVI ":
                        return "video/x-msvideo"
                    continue
                return mime

    return None


def validate_content_type(content_type: str, file_type: str) -> None:
    """Validate Content-Type header against allowlist."""
    allowed = ALLOWED_MIMES.get(file_type, [])
    if not allowed:
        raise FileValidationError(f"Unknown file type: {file_type}")
    if content_type not in allowed:
        raise FileValidationError(
            f"Invalid content type '{content_type}' for {file_type}. "
            f"Allowed: {', '.join(allowed)}"
        )


def validate_magic_bytes(file_bytes: bytes, content_type: str, file_type: str) -> None:
    """Verify magic bytes match the declared content type."""
    detected = detect_mime_by_magic(file_bytes)
    allowed = ALLOWED_MIMES.get(file_type, [])
    if detected is None:
        raise FileValidationError("Cannot determine file type from magic bytes")
    if detected not in allowed:
        raise FileValidationError(
            f"MIME mismatch: header={content_type}, detected={detected}"
        )


def validate_file_size(size: int, file_type: str) -> None:
    """Validate file size against limits."""
    max_size = MAX_SIZES.get(file_type)
    if max_size is None:
        raise FileValidationError(f"Unknown file type: {file_type}")
    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise FileValidationError(
            f"File too large for {file_type}: {size} bytes (max: {max_mb:.0f} MB)"
        )


def sanitize_filename(original_filename: str) -> str:
    """Generate a safe filename using UUID, preserving extension.

    - Blocks path traversal (../)
    - Strips dangerous characters
    - Generates new UUID filename
    """
    # Block path traversal
    if ".." in original_filename or "/" in original_filename or "\\" in original_filename:
        raise FileValidationError(f"Invalid filename: path traversal detected")

    # Extract and validate extension
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    safe_ext = re.sub(r"[^a-z0-9.]", "", ext)
    if not safe_ext:
        safe_ext = ""

    return f"{uuid.uuid4().hex}{safe_ext}"


def validate_file(
    file_bytes: bytes,
    content_type: str,
    file_type: str,
    filename: str | None = None,
) -> dict[str, str]:
    """Full file validation pipeline.

    Args:
        file_bytes: Raw file bytes (at least first 2048 for magic check)
        content_type: Content-Type header value
        file_type: One of 'image', 'video', 'document'
        filename: Original filename (optional, for sanitization)

    Returns:
        dict with safe_filename and detected_mime

    Raises:
        FileValidationError: If any validation fails
    """
    # 1. Content-Type check
    validate_content_type(content_type, file_type)

    # 2. File size check
    validate_file_size(len(file_bytes), file_type)

    # 3. Magic bytes check
    validate_magic_bytes(file_bytes, content_type, file_type)

    # 4. Generate safe filename
    safe_name = sanitize_filename(filename or "file")
    if not os.path.splitext(safe_name)[1]:
        # Add extension from MIME type
        safe_name += EXTENSION_MAP.get(content_type, "")

    return {
        "safe_filename": safe_name,
        "detected_mime": detect_mime_by_magic(file_bytes) or content_type,
    }


def auto_resize_image(
    file_bytes: bytes,
    platform: str,
    content_type: str = "feed",
) -> bytes:
    """Resize image to match platform aspect ratio requirements.

    Args:
        file_bytes: Raw image bytes
        platform: Target platform (instagram, facebook, youtube)
        content_type: Content type (feed, story, reel, etc.)

    Returns:
        Resized image bytes (JPEG format, or PNG if RGBA)
    """
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(file_bytes))

        # Platform-specific target dimensions
        PLATFORM_SIZES = {
            ("instagram", "feed"): (1080, 1080),       # 1:1
            ("instagram", "story"): (1080, 1920),       # 9:16
            ("instagram", "reel"): (1080, 1920),        # 9:16
            ("facebook", "feed"): (1200, 630),          # 1.91:1
            ("facebook", "story"): (1080, 1920),        # 9:16
            ("youtube", "thumbnail"): (1280, 720),      # 16:9
            ("youtube", "short"): (1080, 1920),         # 9:16
        }

        target = PLATFORM_SIZES.get((platform, content_type))
        if not target:
            return file_bytes  # No resize needed

        target_w, target_h = target
        target_ratio = target_w / target_h
        img_ratio = img.width / img.height

        # Crop to target aspect ratio (center crop)
        if img_ratio > target_ratio:
            # Too wide -- crop sides
            new_w = int(img.height * target_ratio)
            left = (img.width - new_w) // 2
            img = img.crop((left, 0, left + new_w, img.height))
        elif img_ratio < target_ratio:
            # Too tall -- crop top/bottom
            new_h = int(img.width / target_ratio)
            top = (img.height - new_h) // 2
            img = img.crop((0, top, img.width, top + new_h))

        # Resize to target dimensions
        img = img.resize((target_w, target_h), Image.LANCZOS)

        # Save to bytes
        output = io.BytesIO()
        fmt = "JPEG"
        if img.mode == "RGBA":
            fmt = "PNG"
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(output, format=fmt, quality=90)
        return output.getvalue()

    except ImportError:
        logger.warning("Pillow not installed, skipping image resize")
        return file_bytes
    except Exception:
        logger.warning("Image resize failed, returning original")
        return file_bytes


def generate_s3_key(client_id: str, file_type: str, filename: str) -> str:
    """Generate S3 object key with organized path structure."""
    return f"clients/{client_id}/{file_type}s/{filename}"
