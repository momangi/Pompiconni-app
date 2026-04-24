"""
GridFS true chunked streaming + ETag / 304 Not Modified support.

Design notes:
- GridFS files are immutable: a new upload always produces a new `_id`.
  Therefore the ETag can simply be derived from the file_id (strong validator).
- We stream chunks directly from the GridOut stream instead of reading the
  full payload into RAM, which drops TTFB dramatically for large files.
- Cache-Control is caller-controlled because policies differ:
    immutable assets (illustrations, posters, themes)  → 1 year, immutable
    mutable assets   (brand logo, hero)                → 1 hour
    downloads (PDFs as attachment)                     → no-cache is fine

Variant resolution (phase 2):
- `stream_gridfs_response_with_variants(...)` can resolve a responsive
  variant (by size + format) with a safe fallback to the original file.
  The caller passes the ORIGINAL file_id; the helper looks up variants
  via `metadata.sourceFileId`. When a variant is missing we never 500:
  we transparently serve the original.
"""
from __future__ import annotations

from typing import Optional, AsyncIterator
from fastapi import HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from bson import ObjectId

from media_pipeline import (
    find_variant,
    normalize_format_param,
    normalize_size_param,
)


def _build_etag(file_id: ObjectId) -> str:
    """Strong ETag derived from the GridFS file_id (immutable per upload)."""
    return f'"{str(file_id)}"'


async def _iter_gridfs_chunks(grid_out) -> AsyncIterator[bytes]:
    """Yield chunks from a motor AsyncIOMotorGridOut without buffering the full file."""
    try:
        while True:
            chunk = await grid_out.readchunk()
            if not chunk:
                break
            yield chunk
    finally:
        close = getattr(grid_out, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


async def stream_gridfs_response(
    *,
    gridfs_bucket,
    file_id,
    request: Request,
    fallback_content_type: str = "application/octet-stream",
    cache_control: str = "public, max-age=3600",
    filename: Optional[str] = None,
    as_attachment: bool = False,
    not_found_detail: str = "File non trovato",
) -> Response:
    """
    Serve a GridFS file with:
      - true chunked streaming (low TTFB, constant RAM)
      - strong ETag derived from immutable file_id
      - HTTP 304 Not Modified when If-None-Match matches
      - Content-Length header when available (for progress bars)
      - Content-Disposition when as_attachment is True
    """
    if not file_id:
        raise HTTPException(status_code=404, detail=not_found_detail)

    try:
        oid = file_id if isinstance(file_id, ObjectId) else ObjectId(str(file_id))
    except Exception:
        raise HTTPException(status_code=404, detail=not_found_detail)

    etag = _build_etag(oid)

    if_none_match = request.headers.get("if-none-match") if request else None
    if if_none_match and if_none_match.strip() == etag:
        return Response(
            status_code=304,
            headers={"ETag": etag, "Cache-Control": cache_control},
        )

    try:
        grid_out = await gridfs_bucket.open_download_stream(oid)
    except Exception:
        raise HTTPException(status_code=404, detail=not_found_detail)

    metadata = getattr(grid_out, "metadata", None) or {}
    content_type = metadata.get("content_type") or fallback_content_type

    headers = {
        "ETag": etag,
        "Cache-Control": cache_control,
        "Accept-Ranges": "none",
    }

    length = getattr(grid_out, "length", None)
    if isinstance(length, int) and length >= 0:
        headers["Content-Length"] = str(length)

    if as_attachment and filename:
        safe_name = filename.replace('"', "").replace("\\", "")
        headers["Content-Disposition"] = f'attachment; filename="{safe_name}"'
    elif filename:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'

    return StreamingResponse(
        _iter_gridfs_chunks(grid_out),
        media_type=content_type,
        headers=headers,
    )


async def stream_gridfs_response_with_variants(
    *,
    db,
    gridfs_bucket,
    original_file_id,
    request: Request,
    size_param: Optional[int] = None,
    format_param: Optional[str] = None,
    fallback_content_type: str = "application/octet-stream",
    cache_control: str = "public, max-age=3600",
    not_found_detail: str = "File non trovato",
) -> Response:
    """
    Serve the best variant that matches `?w=` and `?format=`, falling back
    SAFELY to the original when the requested variant is not available.

    Resolution rules:
      1. Normalize `size_param` to a supported variant size (400/800/1600) or None.
      2. Normalize `format_param` to webp/jpg/png or None.
      3. If size_param is None AND format_param is None → serve original.
      4. Else lookup a matching variant:
           - if both supplied: (size, format) lookup
           - if only size: prefer webp, then jpg, then png
           - if only format: no variant lookup (variants are always linked to a size) → serve original
      5. If no variant found → serve original (never 500, never 404 due to missing variant).

    The function ALWAYS reuses the streaming + ETag pipeline above.
    ETag is per-file (variant vs original), so browser cache is correct.
    """
    size = normalize_size_param(size_param)
    fmt = normalize_format_param(format_param)

    target_id = None

    if size is not None:
        preferred_formats = [fmt] if fmt else ["webp", "jpg", "png"]
        for f in preferred_formats:
            target_id = await find_variant(db, original_file_id, size, f)
            if target_id:
                break

    if target_id is None:
        target_id = original_file_id

    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=target_id,
        request=request,
        fallback_content_type=fallback_content_type,
        cache_control=cache_control,
        not_found_detail=not_found_detail,
    )
