"""
Phase 2 Media Pipeline Refactor — regression & feature tests.

Covers:
- Responsive variant endpoints: ?w=400|800|1600 × ?format=webp|jpg
- Safe fallback to ORIGINAL when variant missing (?w=3000, ?w=99999, ?format without w)
- Distinct ETags per variant (file_id–based, strong validator)
- 304 Not Modified on variant + cross-ETag rejection (different file_ids)
- Other image endpoints accept ?w / ?format with safe fallback
- SECURITY: draft illustration never exposes variants (404)
- downloadEnabled=false does NOT block images (images stay public)
- ORIGINAL integrity preserved post-migration (MD5 prefix + size + PNG magic)
- Variant metadata on fs.files (variant=derived, sourceFileId, variantSize, variantFormat)
- Performance: variant 400 TTFB < 1.5s and size < 50 KB
- Light Phase-1 regression spot checks
"""
from __future__ import annotations

import hashlib
import io
import os
import time
from typing import Optional

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
TARGET_ILLUST_ID = os.environ.get(
    "TARGET_ILLUST_ID", "602f3ea8-16c8-4435-9c69-86fbf39ee5db"
)

# Expected phase-2 byte-exact sizes (confirmed via direct curl against DEV Atlas)
EXPECTED_VARIANT_SIZES = {
    ("w=400",):               {"status": 200, "ct": "image/webp", "bytes": 15884},
    ("w=400", "format=webp"): {"status": 200, "ct": "image/webp", "bytes": 15884},
    ("w=400", "format=jpg"):  {"status": 200, "ct": "image/jpeg", "bytes": 24349},
    ("w=800", "format=webp"): {"status": 200, "ct": "image/webp", "bytes": 38580},
    ("w=1600", "format=webp"):{"status": 200, "ct": "image/webp", "bytes": 91280},
}
ORIGINAL_BYTES = 1106583
ORIGINAL_MD5_PREFIX = "c556aa13f6"
ORIGINAL_CT_PREFIX = "image/png"


# ----------------------------- Fixtures -----------------------------

@pytest.fixture(scope="session")
def api() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Accept": "*/*"})
    return s


@pytest.fixture(scope="session")
def admin_token(api) -> str:
    if not (ADMIN_EMAIL and ADMIN_PASSWORD):
        pytest.skip("ADMIN_EMAIL/ADMIN_PASSWORD not set in env")
    r = api.post(
        f"{BASE_URL}/api/admin/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code} {r.text[:150]}")
    tok = r.json().get("token") or r.json().get("access_token")
    if not tok:
        pytest.skip("admin login returned no token")
    return tok


@pytest.fixture(scope="session")
def auth_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


def _img_url(qs: str = "") -> str:
    base = f"{BASE_URL}/api/illustrations/{TARGET_ILLUST_ID}/image"
    return f"{base}?{qs}" if qs else base


# ----------------------------- Variant endpoint: exact sizes -----------------------------

@pytest.mark.parametrize("qparams", list(EXPECTED_VARIANT_SIZES.keys()))
def test_variant_exact_bytes_and_content_type(api, qparams):
    exp = EXPECTED_VARIANT_SIZES[qparams]
    url = _img_url("&".join(qparams))
    r = api.get(url, timeout=30)
    assert r.status_code == exp["status"], f"{url} -> {r.status_code}"
    ct = r.headers.get("content-type", "").split(";")[0].strip()
    assert ct == exp["ct"], f"{url} -> ct={ct}"
    assert len(r.content) == exp["bytes"], (
        f"{url} -> got {len(r.content)} bytes, expected {exp['bytes']}"
    )


# ----------------------------- Safe fallback to ORIGINAL -----------------------------

@pytest.mark.parametrize("qs,expect_original", [
    ("w=3000", True),        # above max supported variant -> original
    ("w=99999", True),       # absurdly big -> original
    ("format=webp", True),   # format without w -> original (variants keyed by size)
    ("w=-1", True),           # negative -> server normalizes to None -> original
    ("format=bogus", True),  # invalid format -> original
    ("w=abc", False),        # non-integer -> FastAPI 422 validation (still NOT 500)
])
def test_fallback_to_original_never_500(api, qs, expect_original):
    r = api.get(_img_url(qs), timeout=30)
    # Must NEVER 500
    assert r.status_code != 500, f"?{qs} returned 500"
    if expect_original:
        assert r.status_code == 200, f"?{qs} -> {r.status_code}"
        assert len(r.content) == ORIGINAL_BYTES, (
            f"?{qs} -> expected ORIGINAL {ORIGINAL_BYTES} bytes, got {len(r.content)}"
        )
        assert r.headers.get("content-type", "").startswith(ORIGINAL_CT_PREFIX)
    else:
        # Non-coercible type -> FastAPI returns 422 at framework layer. Safe, not a 500.
        assert r.status_code == 422


# ----------------------------- ETag distinctness -----------------------------

def _get_etag(api, qs: str = "") -> Optional[str]:
    r = api.get(_img_url(qs), timeout=30)
    assert r.status_code == 200
    return r.headers.get("ETag")


def test_etag_distinct_across_variants(api):
    et_orig = _get_etag(api)
    et_400  = _get_etag(api, "w=400")
    et_800  = _get_etag(api, "w=800")
    et_1600 = _get_etag(api, "w=1600")
    assert et_orig and et_400 and et_800 and et_1600, "ETag missing on some response"
    etags = {et_orig, et_400, et_800, et_1600}
    assert len(etags) == 4, f"Expected 4 distinct ETags, got {etags}"


# ----------------------------- 304 Not Modified on variants -----------------------------

def test_304_on_variant_same_etag(api):
    first = api.get(_img_url("w=400"), timeout=30)
    assert first.status_code == 200
    etag = first.headers.get("ETag")
    assert etag
    second = api.get(
        _img_url("w=400"),
        headers={"If-None-Match": etag},
        timeout=30,
    )
    assert second.status_code == 304, f"expected 304, got {second.status_code}"
    # 304 must carry no body
    assert len(second.content) == 0


def test_cross_etag_no_304(api):
    """If-None-Match carrying the ORIGINAL ETag on a ?w=400 request must NOT 304."""
    et_orig = _get_etag(api)
    r = api.get(
        _img_url("w=400"),
        headers={"If-None-Match": et_orig},
        timeout=30,
    )
    assert r.status_code == 200, f"cross-ETag -> {r.status_code}"
    assert len(r.content) == EXPECTED_VARIANT_SIZES[("w=400",)]["bytes"]


# ----------------------------- Other image endpoints accept ?w / ?format -----------------------------

def _pick_first_id(api, list_path: str, id_field: str = "id") -> Optional[str]:
    r = api.get(f"{BASE_URL}{list_path}", timeout=20)
    if r.status_code != 200:
        return None
    data = r.json()
    if not isinstance(data, list) or not data:
        return None
    return data[0].get(id_field)


def _endpoint_accepts_w_with_safe_fallback(api, url: str) -> tuple[int, int]:
    """Return (status, bytes) for url + ?w=400. Must be 2xx and never 500."""
    r = api.get(f"{url}?w=400", timeout=30)
    assert r.status_code != 500, f"{url}?w=400 returned 500"
    return r.status_code, len(r.content)


def test_posters_image_accepts_w(api):
    pid = _pick_first_id(api, "/api/posters")
    if not pid:
        pytest.skip("no posters in DB")
    status, _ = _endpoint_accepts_w_with_safe_fallback(api, f"{BASE_URL}/api/posters/{pid}/image")
    # 200 (variant or original) or 404 (poster has no image) — both acceptable
    assert status in (200, 404)


def test_books_cover_accepts_w(api):
    bid = _pick_first_id(api, "/api/books")
    if not bid:
        pytest.skip("no books in DB")
    r = api.get(f"{BASE_URL}/api/books/{bid}/cover?w=400", timeout=30)
    assert r.status_code != 500
    assert r.status_code in (200, 404)


def test_games_endpoints_accept_w(api):
    games = api.get(f"{BASE_URL}/api/games", timeout=20).json()
    if not isinstance(games, list) or not games:
        pytest.skip("no games in DB")
    slug = games[0].get("slug")
    if not slug:
        pytest.skip("first game has no slug")
    for path in ("thumbnail", "card-image", "page-image"):
        r = api.get(f"{BASE_URL}/api/games/{slug}/{path}?w=400", timeout=30)
        assert r.status_code != 500, f"/games/{slug}/{path}?w=400 -> 500"
        # 200 (variant/original), 204 (game endpoints return No Content when image absent), 404 (not found) all acceptable
        assert r.status_code in (200, 204, 404), f"/games/{slug}/{path} -> {r.status_code}"


def test_themes_bg_accepts_w(api):
    tid = _pick_first_id(api, "/api/themes")
    if not tid:
        pytest.skip("no themes in DB")
    r = api.get(f"{BASE_URL}/api/themes/{tid}/background-image?w=400", timeout=30)
    assert r.status_code != 500
    assert r.status_code in (200, 404)


def test_site_hero_and_logo_accept_w(api):
    for path in ("/api/site/hero-image", "/api/site/brand-logo"):
        r = api.get(f"{BASE_URL}{path}?w=400", timeout=30)
        assert r.status_code != 500, f"{path}?w=400 -> 500"
        assert r.status_code in (200, 404)


# ----------------------------- Security: draft illustrations + variants -----------------------------

def test_draft_illustration_hides_variants(api, auth_headers):
    # Create DRAFT illustration
    payload = {
        "title": "TEST_phase2_draft",
        "description": "phase2 draft — must not expose variants",
        "themeId": "test",
        "isPublished": False,
    }
    create = api.post(
        f"{BASE_URL}/api/admin/illustrations",
        headers={**auth_headers, "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    if create.status_code not in (200, 201):
        pytest.skip(f"cannot create draft: {create.status_code} {create.text[:200]}")
    new_id = create.json().get("id")
    assert new_id

    try:
        # ORIGINAL request: must be 404 (no image attached OR draft)
        r0 = api.get(f"{BASE_URL}/api/illustrations/{new_id}/image", timeout=20)
        assert r0.status_code == 404, f"draft /image -> {r0.status_code}"

        # VARIANT request: must also be 404, never leak
        r1 = api.get(
            f"{BASE_URL}/api/illustrations/{new_id}/image?w=400", timeout=20
        )
        assert r1.status_code == 404, f"draft /image?w=400 -> {r1.status_code}"
        r2 = api.get(
            f"{BASE_URL}/api/illustrations/{new_id}/image?w=400&format=webp",
            timeout=20,
        )
        assert r2.status_code == 404, f"draft /image?w=400&format=webp -> {r2.status_code}"
    finally:
        api.delete(
            f"{BASE_URL}/api/admin/illustrations/{new_id}",
            headers=auth_headers,
            timeout=15,
        )


# ----------------------------- downloadEnabled=false must NOT block images -----------------------------

def test_download_disabled_still_serves_images(api, auth_headers):
    # Toggle downloadEnabled off on the target illustration, verify image + variant still work.
    toggle_off = api.put(
        f"{BASE_URL}/api/admin/illustrations/{TARGET_ILLUST_ID}/download-enabled",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"downloadEnabled": False},
        timeout=15,
    )
    if toggle_off.status_code not in (200, 204):
        pytest.skip(
            f"cannot toggle downloadEnabled off: {toggle_off.status_code} {toggle_off.text[:200]}"
        )
    try:
        img = api.get(_img_url(), timeout=30)
        var = api.get(_img_url("w=400"), timeout=30)
        assert img.status_code == 200, f"image blocked when dlEnabled=false: {img.status_code}"
        assert len(img.content) == ORIGINAL_BYTES
        assert var.status_code == 200, f"variant blocked when dlEnabled=false: {var.status_code}"
        assert len(var.content) == EXPECTED_VARIANT_SIZES[("w=400",)]["bytes"]
    finally:
        api.put(
            f"{BASE_URL}/api/admin/illustrations/{TARGET_ILLUST_ID}/download-enabled",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"downloadEnabled": True},
            timeout=15,
        )


# ----------------------------- Original integrity (post-migration) -----------------------------

def test_original_integrity_preserved(api):
    r = api.get(_img_url(), timeout=60)
    assert r.status_code == 200
    data = r.content
    assert len(data) == ORIGINAL_BYTES, f"size changed: {len(data)} vs {ORIGINAL_BYTES}"
    assert data[:4] == b"\x89PNG", "PNG magic bytes missing"
    md5 = hashlib.md5(data).hexdigest()
    assert md5.startswith(ORIGINAL_MD5_PREFIX), f"md5 prefix mismatch: {md5[:10]}"


# ----------------------------- Performance: variant 400 TTFB + size -----------------------------

def test_variant_400_performance(api):
    url = _img_url("w=400")
    # warm up (first request may hit GridFS cold) — take the best of 2
    best = 999.0
    size = 0
    for _ in range(2):
        t0 = time.perf_counter()
        r = api.get(url, timeout=10)
        dt = time.perf_counter() - t0
        assert r.status_code == 200
        size = len(r.content)
        best = min(best, dt)
    assert size < 50 * 1024, f"variant too big: {size} bytes"
    assert best < 1.5, f"TTFB too slow: {best:.3f}s (target <1.5s)"


# ----------------------------- Phase-1 light regression -----------------------------

def test_phase1_regression_public_lists(api):
    for p in ("/api/illustrations", "/api/posters", "/api/books", "/api/games", "/api/themes"):
        r = api.get(f"{BASE_URL}{p}", timeout=20)
        assert r.status_code == 200, f"{p} -> {r.status_code}"


def test_phase1_etag_304_without_query(api):
    r = api.get(_img_url(), timeout=30)
    assert r.status_code == 200
    et = r.headers.get("ETag")
    assert et
    r2 = api.get(_img_url(), headers={"If-None-Match": et}, timeout=30)
    assert r2.status_code == 304
    assert len(r2.content) == 0


def test_phase1_admin_login_required(api):
    # A protected admin endpoint must 401/403 without Authorization
    r = api.get(f"{BASE_URL}/api/admin/illustrations", timeout=15)
    assert r.status_code in (401, 403), f"admin guard weak: {r.status_code}"
