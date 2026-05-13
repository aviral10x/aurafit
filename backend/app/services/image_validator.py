"""
Image validation for uploaded photos.
Checks file size, MIME type, dimensions, blur, and basic lighting.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

from PIL import Image, ImageStat


ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_MB = 10
MIN_DIMENSION = 200
MAX_DIMENSION = 8000


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_image(content: bytes, filename: str, content_type: str) -> ValidationResult:
    result = ValidationResult()

    # 1. MIME type
    if content_type not in ALLOWED_MIME_TYPES:
        result.valid = False
        result.errors.append(f"Unsupported file type '{content_type}'. Use JPEG, PNG, or WebP.")
        return result

    # 2. File size
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        result.valid = False
        result.errors.append(f"File too large ({size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB.")
        return result

    # 3. Open with Pillow
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        img = Image.open(io.BytesIO(content))  # Re-open after verify
        img = img.convert("RGB")
    except Exception:
        result.valid = False
        result.errors.append("Could not read image file. Please upload a valid photo.")
        return result

    width, height = img.size

    # 4. Minimum dimensions
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        result.valid = False
        result.errors.append(
            f"Image too small ({width}×{height}px). Please upload a photo at least {MIN_DIMENSION}×{MIN_DIMENSION}px."
        )
        return result

    # 5. Maximum dimensions
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        result.warnings.append(
            f"Image is very large ({width}×{height}px). Consider resizing for faster analysis."
        )

    # 6. Blur detection (Laplacian variance — low = blurry)
    try:
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        # Approximate sharpness via pixel std dev
        sharpness = stat.stddev[0]
        if sharpness < 8:
            result.warnings.append("Photo appears blurry. For best results, use a sharp, well-lit photo.")
    except Exception:
        pass  # Non-fatal

    # 7. Lighting check (average brightness)
    try:
        stat = ImageStat.Stat(img)
        brightness = sum(stat.mean[:3]) / 3
        if brightness < 40:
            result.warnings.append("Photo looks very dark. A brighter photo will improve analysis accuracy.")
        elif brightness > 230:
            result.warnings.append("Photo looks overexposed. A balanced-exposure photo works best.")
    except Exception:
        pass  # Non-fatal

    # 8. Portrait orientation check (soft warning only)
    if width > height * 1.5:
        result.warnings.append(
            "Landscape photo detected. Portrait-orientation full-body photos give the best results."
        )

    return result


def validate_all(files: list[tuple[bytes, str, str]]) -> dict:
    """
    Validate a list of (content, filename, content_type) tuples.
    Returns {"valid": bool, "errors": [...], "warnings": [...]}
    """
    all_errors: list[str] = []
    all_warnings: list[str] = []

    for i, (content, filename, content_type) in enumerate(files, start=1):
        res = validate_image(content, filename, content_type)
        prefix = f"Photo {i}: "
        all_errors.extend(prefix + e for e in res.errors)
        all_warnings.extend(prefix + w for w in res.warnings)

    return {
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "warnings": all_warnings,
    }
