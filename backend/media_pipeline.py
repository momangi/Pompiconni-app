"""
Media pipeline: generate responsive variants for images stored in GridFS.

Design
------
- Every variant is a SEPARATE GridFS file (new fs.files doc).
- Variants are linked to their source via `metadata.sourceFileId`.
- Variants never overwrite the original. The original is kept untouched.
- Idempotent: a variant is generated only if the exact (size, format)
  combination does not already exist for the given source.
- Fallback: if a variant is missing the caller can still serve the original.

Metadata schema
---------------
Original file (existing uploads, or marked explicitly):
  {
    "variant": "original",
    "content_type": "image/png",
    "width": 2048, "height": 2048,
    "size": 1234567,
  }

Derived variant:
  {
    "variant": "derived",
    "variantSize": 400 | 800 | 1600,      # target long side in px
    "variantFormat": "webp" | "jpg" | "png",
    "sourceFileId": "<ObjectId of original, as str>",
    "content_type": "image/webp" | "image/jpeg" | "image/png",
    "width": 400, "height": 300,
    "size": 28471,
  }

Variants produced per image: 3 sizes × 2 formats = 6 variants.
  sizes: 400, 800, 1600 (long side; aspect ratio preserved; upscale avoided)
  formats: webp (primary) + jpg (fallback); png used as fallback only for RGBA
"""
from __future__ import annotations

import io
import logging
from typing import Optional, List, Dict, Any, Tuple
from bson import ObjectId
from PIL import Image as PILImage, ImageOps

logger = logging.getLogger(__name__)


VARIANT_SIZES = (400, 800, 1600)
PRIMARY_FORMAT = "webp"
FALLBACK_FORMAT_RGB = "jpg"
FALLBACK_FORMAT_RGBA = "png"

WEBP_QUALITY = 82
JPG_QUALITY = 85
PNG_OPTIMIZE = True

CONTENT_TYPES = {
    "webp": "image/webp",
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "png":  "image/png",
}


def _pil_format(fmt: str) -> str:
    f = fmt.lower()
    if f in ("jpg", "jpeg"):
        return "JPEG"
    if f == "webp":
        return "WEBP"
    if f == "png":
        return "PNG"
    raise ValueError(f"Unsupported format: {fmt}")


def _has_alpha(img: PILImage.Image) -> bool:
    return img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)


def _compute_size(w: int, h: int, target_long: int) -> Tuple[int, int]:
    """Keep aspect ratio; never upscale."""
    long_side = max(w, h)
    if long_side <= target_long:
        return w, h
    ratio = target_long / long_side
    return max(1, int(round(w * ratio))), max(1, int(round(h * ratio)))


def _encode(img: PILImage.Image, fmt: str) -> bytes:
    buf = io.BytesIO()
    pil_fmt = _pil_format(fmt)
    if pil_fmt == "JPEG":
        # JPEG has no alpha — flatten onto white when needed
        if _has_alpha(img):
            bg = PILImage.new("RGB", img.size, (255, 255, 255))
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=JPG_QUALITY, optimize=True, progressive=True)
    elif pil_fmt == "WEBP":
        # WebP supports alpha — preserve it when present
        img.save(buf, format="WEBP", quality=WEBP_QUALITY, method=6)
    else:  # PNG
        img.save(buf, format="PNG", optimize=PNG_OPTIMIZE)
    return buf.getvalue()


def _variant_filename(source_name: str, size: int, fmt: str) -> str:
    stem = source_name.rsplit(".", 1)[0] if source_name else "image"
    return f"{stem}_w{size}.{fmt}"


async def find_variant(
    db,
    source_file_id,
    size: int,
    fmt: str,
) -> Optional[ObjectId]:
    """Return the GridFS _id of an existing variant, or None."""
    if not source_file_id:
        return None
    src_str = str(source_file_id)
    doc = await db["fs.files"].find_one(
        {
            "metadata.variant": "derived",
            "metadata.sourceFileId": src_str,
            "metadata.variantSize": int(size),
            "metadata.variantFormat": fmt.lower(),
        },
        {"_id": 1},
    )
    return doc["_id"] if doc else None


def _chosen_formats_for(image_mode: str) -> List[str]:
    """Primary WebP always; fallback PNG (alpha) or JPG (no alpha)."""
    has_alpha = image_mode in ("RGBA", "LA")
    fallback = FALLBACK_FORMAT_RGBA if has_alpha else FALLBACK_FORMAT_RGB
    return [PRIMARY_FORMAT, fallback]


async def ensure_variants(
    *,
    db,
    gridfs_bucket,
    source_file_id,
    skip_if_exists: bool = True,
) -> Dict[str, Any]:
    """
    Generate all (size × format) variants for the given source file.

    Returns a structured report:
      {
        "sourceFileId": "...",
        "originalSize": 1234567,
        "originalWidth": 2048, "originalHeight": 2048,
        "originalContentType": "image/png",
        "variants": [
           {"size": 400, "format": "webp", "fileId": "...", "bytes": 28471, "created": True},
           ...
        ],
        "errors": ["..."],
      }
    Never raises for a single-variant failure; collects errors instead.
    """
    report: Dict[str, Any] = {
        "sourceFileId": str(source_file_id),
        "variants": [],
        "errors": [],
    }

    try:
        oid = source_file_id if isinstance(source_file_id, ObjectId) else ObjectId(str(source_file_id))
    except Exception as e:
        report["errors"].append(f"invalid sourceFileId: {e}")
        return report

    # Load source bytes
    try:
        grid_out = await gridfs_bucket.open_download_stream(oid)
        original_bytes = await grid_out.read()
        report["originalSize"] = len(original_bytes)
        report["originalContentType"] = (getattr(grid_out, "metadata", None) or {}).get("content_type", "")
        source_filename = getattr(grid_out, "filename", None) or "image"
    except Exception as e:
        report["errors"].append(f"cannot read source: {e}")
        return report

    # Decode
    try:
        img = PILImage.open(io.BytesIO(original_bytes))
        img.load()
        img = ImageOps.exif_transpose(img)  # respect EXIF orientation
    except Exception as e:
        report["errors"].append(f"cannot decode image: {e}")
        return report

    report["originalWidth"], report["originalHeight"] = img.size
    formats = _chosen_formats_for(img.mode)

    for size in VARIANT_SIZES:
        w, h = _compute_size(img.width, img.height, size)
        if (w, h) == img.size:
            resized = img
        else:
            resized = img.resize((w, h), PILImage.LANCZOS)

        for fmt in formats:
            # Skip if an equivalent variant already exists
            if skip_if_exists:
                existing = await find_variant(db, oid, size, fmt)
                if existing:
                    report["variants"].append({
                        "size": size, "format": fmt, "fileId": str(existing),
                        "bytes": None, "created": False, "skipped": "already_exists",
                    })
                    continue

            try:
                data = _encode(resized, fmt)
            except Exception as e:
                report["errors"].append(f"encode {size}/{fmt} failed: {e}")
                continue

            filename = _variant_filename(source_filename, size, fmt)
            try:
                file_id = await gridfs_bucket.upload_from_stream(
                    filename,
                    io.BytesIO(data),
                    metadata={
                        "variant": "derived",
                        "variantSize": int(size),
                        "variantFormat": fmt,
                        "sourceFileId": str(oid),
                        "content_type": CONTENT_TYPES[fmt],
                        "width": w,
                        "height": h,
                        "size": len(data),
                    },
                )
                report["variants"].append({
                    "size": size, "format": fmt, "fileId": str(file_id),
                    "bytes": len(data), "created": True, "skipped": None,
                })
            except Exception as e:
                report["errors"].append(f"upload {size}/{fmt} failed: {e}")

    return report


def pick_format_for_variants(original_content_type: Optional[str]) -> str:
    """Default fallback format when client does not specify one."""
    ct = (original_content_type or "").lower()
    if "png" in ct:
        return "png"
    return "jpg"


def normalize_format_param(fmt: Optional[str]) -> Optional[str]:
    """Validate and normalize the client-supplied format query param."""
    if not fmt:
        return None
    f = fmt.lower().strip()
    if f == "jpeg":
        f = "jpg"
    if f not in ("webp", "jpg", "png"):
        return None
    return f


def normalize_size_param(size: Optional[int]) -> Optional[int]:
    """Clamp client-supplied width to a supported variant size; None if invalid."""
    if size is None:
        return None
    try:
        s = int(size)
    except (TypeError, ValueError):
        return None
    if s <= 0:
        return None
    # Round up to closest supported size. Values larger than 1600 return None -> serve original.
    for target in VARIANT_SIZES:
        if s <= target:
            return target
    return None
