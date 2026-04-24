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
"""
from __future__ import annotations

from typing import Optional, AsyncIterator
from fastapi import HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from bson import ObjectId


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
        # Motor GridOut does not strictly require close(), but be defensive.
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

    # Normalize file_id to ObjectId
    try:
        oid = file_id if isinstance(file_id, ObjectId) else ObjectId(str(file_id))
    except Exception:
        raise HTTPException(status_code=404, detail=not_found_detail)

    etag = _build_etag(oid)

    # Conditional GET — short-circuit before opening the GridFS stream
    if_none_match = request.headers.get("if-none-match") if request else None
    if if_none_match and if_none_match.strip() == etag:
        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": cache_control,
            },
        )

    # Open the stream (one round-trip to Mongo for metadata)
    try:
        grid_out = await gridfs_bucket.open_download_stream(oid)
    except Exception:
        raise HTTPException(status_code=404, detail=not_found_detail)

    # Resolve content-type from stored metadata when possible
    metadata = getattr(grid_out, "metadata", None) or {}
    content_type = metadata.get("content_type") or fallback_content_type

    headers = {
        "ETag": etag,
        "Cache-Control": cache_control,
        "Accept-Ranges": "none",  # explicit: we do not support Range yet
    }

    length = getattr(grid_out, "length", None)
    if isinstance(length, int) and length >= 0:
        headers["Content-Length"] = str(length)

    if as_attachment and filename:
        # RFC 5987 safe filename handling
        safe_name = filename.replace('"', "").replace("\\", "")
        headers["Content-Disposition"] = f'attachment; filename="{safe_name}"'
    elif filename:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'

    return StreamingResponse(
        _iter_gridfs_chunks(grid_out),
        media_type=content_type,
        headers=headers,
    )
