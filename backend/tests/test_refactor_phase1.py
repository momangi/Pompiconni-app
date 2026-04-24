"""
Phase 1 performance refactor regression tests.

Covers:
- Public JSON endpoints (200 + correct shape)
- GridFS-backed image endpoints (bytes, ETag, Cache-Control)
- ETag / 304 Not Modified conditional GET
- PDF download rules (published + downloadEnabled)
- Admin auth + protected endpoints (401 without token)
- Security regression: draft resources return 404 on all read paths
- True-streaming integrity: MD5 of 1.1 MB PNG (no corruption)
- MongoDB indexes created (20 expected)
"""
from __future__ import annotations

import hashlib
import os
import sys
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://draft-security-check.preview.emergentagent.com").rstrip("/")
# Backend direct (bypass ingress) to verify Cache-Control actually set by app.
# The preview ingress/Cloudflare strips app Cache-Control to no-store, no-cache, must-revalidate.
BACKEND_DIRECT = os.environ.get("BACKEND_DIRECT_URL", "http://localhost:8001").rstrip("/")
ADMIN_EMAIL = "admin@pompiconni.it"
ADMIN_PASSWORD = "admin123"
TARGET_ILLUST_ID = "602f3ea8-16c8-4435-9c69-86fbf39ee5db"
EXPECTED_CONTENT_LENGTH = 1106583
EXPECTED_MD5_PREFIX = "c556aa13f6"

# ----------------------------- Fixtures -----------------------------

@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(api):
    r = api.post(f"{BASE_URL}/api/admin/login",
                 json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed status={r.status_code} body={r.text[:200]}")
    tok = r.json().get("token") or r.json().get("access_token")
    if not tok:
        pytest.skip("Admin login returned no token field")
    return tok


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ----------------------------- Public JSON -----------------------------

@pytest.mark.parametrize("path", [
    "/api/illustrations",
    "/api/posters",
    "/api/bundles",
    "/api/books",
    "/api/games",
    "/api/themes",
    "/api/site-settings",
    "/api/brand-kit",
    "/api/reviews",
])
def test_public_json_endpoints_return_200(api, path):
    r = api.get(f"{BASE_URL}{path}", timeout=20)
    assert r.status_code == 200, f"{path} -> {r.status_code} body={r.text[:200]}"
    # must be JSON parseable
    data = r.json()
    assert data is not None
    # list endpoints should be list; the other two are objects
    if path in ("/api/site-settings", "/api/brand-kit"):
        assert isinstance(data, dict)
    else:
        assert isinstance(data, list), f"{path} expected list got {type(data)}"


def test_illustrations_has_target_and_is_published(api):
    r = api.get(f"{BASE_URL}/api/illustrations", timeout=20)
    assert r.status_code == 200
    items = r.json()
    ids = [i.get("id") for i in items]
    assert TARGET_ILLUST_ID in ids, "Target illustration missing from public listing"


# ----------------------------- GridFS image endpoints -----------------------------

def _pick_published_id(api, path_list, id_key="id"):
    r = api.get(f"{BASE_URL}{path_list}", timeout=20)
    assert r.status_code == 200
    arr = r.json()
    if not arr:
        return None
    return arr[0].get(id_key) or arr[0].get("slug")


def test_illustration_image_serves_bytes_with_etag_and_cache(api):
    url = f"{BASE_URL}/api/illustrations/{TARGET_ILLUST_ID}/image"
    r = api.get(url, timeout=30)
    assert r.status_code == 200, f"{url} -> {r.status_code}"
    assert r.content[:4] == b"\x89PNG", f"First bytes wrong: {r.content[:8]!r}"
    assert r.headers.get("ETag"), "ETag header missing"
    cl = r.headers.get("Content-Length")
    assert cl == str(EXPECTED_CONTENT_LENGTH), f"Content-Length={cl} expected={EXPECTED_CONTENT_LENGTH}"
    md5 = hashlib.md5(r.content).hexdigest()
    assert md5.startswith(EXPECTED_MD5_PREFIX), f"MD5={md5} does not start with {EXPECTED_MD5_PREFIX}"
    # Cache-Control is validated against the backend directly because preview
    # ingress rewrites Cache-Control on all responses.
    r_direct = requests.get(f"{BACKEND_DIRECT}/api/illustrations/{TARGET_ILLUST_ID}/image",
                            timeout=30, stream=True)
    try:
        assert r_direct.status_code == 200
        cc = r_direct.headers.get("Cache-Control", "")
        assert "max-age=31536000" in cc and "immutable" in cc, f"Backend Cache-Control weak: {cc}"
    finally:
        r_direct.close()


def test_etag_304_not_modified_on_illustration_image(api):
    url = f"{BASE_URL}/api/illustrations/{TARGET_ILLUST_ID}/image"
    r1 = api.get(url, timeout=30)
    assert r1.status_code == 200
    etag = r1.headers.get("ETag")
    assert etag, "ETag missing on first request"
    r2 = api.get(url, headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304, f"Expected 304 got {r2.status_code}"
    # 304 should have no body
    assert r2.content in (b"", None), f"304 returned body: {r2.content[:40]!r}"
    assert r2.headers.get("ETag") == etag


def test_etag_304_on_second_image_endpoint(api):
    # pick any book with a cover, otherwise skip
    books = api.get(f"{BASE_URL}/api/books", timeout=20).json()
    target = None
    for b in books:
        bid = b.get("id")
        if not bid:
            continue
        r = api.get(f"{BASE_URL}/api/books/{bid}/cover", timeout=30)
        if r.status_code == 200 and r.headers.get("ETag"):
            target = (bid, r.headers["ETag"])
            break
    if not target:
        pytest.skip("No book with cover image available to validate ETag")
    bid, etag = target
    r2 = api.get(f"{BASE_URL}/api/books/{bid}/cover",
                 headers={"If-None-Match": etag}, timeout=30)
    assert r2.status_code == 304
    assert r2.headers.get("ETag") == etag


def test_site_hero_and_brand_logo_headers(api):
    for path in ("/api/site/hero-image", "/api/site/brand-logo"):
        r = api.get(f"{BASE_URL}{path}", timeout=30)
        if r.status_code == 404:
            continue  # not configured: acceptable
        assert r.status_code == 200, f"{path} -> {r.status_code}"
        assert r.headers.get("ETag"), f"{path} missing ETag"
        # Validate Cache-Control on backend directly (ingress strips it on public URL)
        r2 = requests.get(f"{BACKEND_DIRECT}{path}", timeout=30, stream=True)
        try:
            if r2.status_code == 200:
                cc = r2.headers.get("Cache-Control", "")
                assert "max-age" in cc, f"{path} backend cache-control weak: {cc}"
        finally:
            r2.close()


def test_theme_background_image(api):
    themes = api.get(f"{BASE_URL}/api/themes", timeout=20).json()
    hit = False
    for t in themes:
        tid = t.get("id")
        r = api.get(f"{BASE_URL}/api/themes/{tid}/background-image", timeout=20)
        if r.status_code == 200:
            assert r.headers.get("ETag")
            hit = True
            break
    if not hit:
        pytest.skip("No theme with background image")


# ----------------------------- PDF download rules -----------------------------

def test_download_pdf_target_illustration(api):
    # target illustration is published; may or may not have pdfFileId -> both outcomes are acceptable per spec
    url = f"{BASE_URL}/api/illustrations/{TARGET_ILLUST_ID}/download"
    r = api.post(url, timeout=60)
    assert r.status_code in (200, 403, 404), f"Unexpected status {r.status_code}"
    if r.status_code == 200:
        cd = r.headers.get("Content-Disposition", "")
        assert "attachment" in cd.lower()
        assert r.content.startswith(b"%PDF"), "Body is not a PDF"


def test_download_nonexistent_illustration_returns_404(api):
    r = api.post(f"{BASE_URL}/api/illustrations/nonexistent-id-xyz/download", timeout=20)
    assert r.status_code == 404


# ----------------------------- Admin auth -----------------------------

def test_admin_login_valid():
    r = requests.post(f"{BASE_URL}/api/admin/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"status={r.status_code} body={r.text[:200]}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    assert tok and isinstance(tok, str) and len(tok) > 20


def test_admin_login_invalid():
    r = requests.post(f"{BASE_URL}/api/admin/login",
                      json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=15)
    assert r.status_code in (400, 401, 403), f"got {r.status_code}"


@pytest.mark.parametrize("path", [
    "/api/admin/illustrations",
    "/api/admin/posters",
    "/api/admin/games",
    "/api/admin/books",
])
def test_admin_endpoints_require_auth(api, path):
    r = api.get(f"{BASE_URL}{path}", timeout=15)
    assert r.status_code in (401, 403), f"{path} without token returned {r.status_code}"


@pytest.mark.parametrize("path", [
    "/api/admin/illustrations",
    "/api/admin/posters",
    "/api/admin/games",
    "/api/admin/books",
])
def test_admin_endpoints_with_token(api, auth_headers, path):
    r = api.get(f"{BASE_URL}{path}", headers=auth_headers, timeout=20)
    assert r.status_code == 200, f"{path} with token -> {r.status_code} body={r.text[:200]}"
    data = r.json()
    assert isinstance(data, list) or isinstance(data, dict)


# ----------------------------- Security regression: drafts return 404 -----------------------------

def _get_any_theme_id(api):
    r = api.get(f"{BASE_URL}/api/themes", timeout=20)
    if r.status_code != 200:
        return None
    arr = r.json()
    return arr[0].get("id") if arr else None


def test_draft_illustration_returns_404_on_all_paths(api, auth_headers):
    """Create a draft via admin API, assert public endpoints return 404, then cleanup."""
    theme_id = _get_any_theme_id(api)
    if not theme_id:
        pytest.skip("No themes available to create a test illustration")
    payload = {
        "title": "TEST_draft_reg",
        "description": "regression test draft",
        "themeId": theme_id,
        "isFree": True,
        "price": 0.99,
    }
    r = requests.post(f"{BASE_URL}/api/admin/illustrations",
                      headers={**auth_headers, "Content-Type": "application/json"},
                      json=payload, timeout=20)
    if r.status_code not in (200, 201):
        pytest.skip(f"Cannot create draft illustration (status {r.status_code}): {r.text[:200]}")
    draft = r.json()
    draft_id = draft.get("id")
    assert draft_id
    assert draft.get("isPublished") is False, "Newly created illustration should be draft"
    try:
        # Public GET returns 404
        r1 = api.get(f"{BASE_URL}/api/illustrations/{draft_id}", timeout=15)
        assert r1.status_code == 404, f"Draft visible via GET: {r1.status_code}"
        # Public image returns 404
        r2 = api.get(f"{BASE_URL}/api/illustrations/{draft_id}/image", timeout=15)
        assert r2.status_code == 404, f"Draft image visible: {r2.status_code}"
        # Public download returns 404
        r3 = api.post(f"{BASE_URL}/api/illustrations/{draft_id}/download", timeout=15)
        assert r3.status_code == 404, f"Draft download returned: {r3.status_code}"
        # Listing must not contain it
        listing = api.get(f"{BASE_URL}/api/illustrations", timeout=20).json()
        assert draft_id not in [i.get("id") for i in listing], "Draft appears in public listing"
    finally:
        requests.delete(f"{BASE_URL}/api/admin/illustrations/{draft_id}",
                        headers=auth_headers, timeout=15)


def test_download_disabled_returns_403(api, auth_headers):
    """Create illustration, publish it, disable download, assert 403 on POST /download."""
    theme_id = _get_any_theme_id(api)
    if not theme_id:
        pytest.skip("No themes available")
    payload = {
        "title": "TEST_download_disabled",
        "description": "regression",
        "themeId": theme_id,
        "isFree": True,
        "price": 0.99,
    }
    r = requests.post(f"{BASE_URL}/api/admin/illustrations",
                      headers={**auth_headers, "Content-Type": "application/json"},
                      json=payload, timeout=20)
    if r.status_code not in (200, 201):
        pytest.skip(f"Cannot create illustration: {r.status_code} {r.text[:200]}")
    obj = r.json()
    oid = obj.get("id")
    try:
        # Publish first (toggle)
        pub = requests.put(f"{BASE_URL}/api/admin/illustrations/{oid}/publish",
                           headers=auth_headers, timeout=15)
        if pub.status_code not in (200, 204):
            pytest.skip(f"Could not publish illustration for test: {pub.status_code} {pub.text[:200]}")
        # Disable download via dedicated toggle endpoint (toggles current state)
        upd = requests.put(f"{BASE_URL}/api/admin/illustrations/{oid}/download-enabled",
                           headers=auth_headers, timeout=15)
        if upd.status_code not in (200, 204):
            pytest.skip(f"Could not toggle downloadEnabled: {upd.status_code} {upd.text[:200]}")
        new_state = upd.json().get("downloadEnabled")
        # Default is True, toggle → should now be False
        assert new_state is False, f"Expected downloadEnabled=False after toggle, got {new_state}"
        # Now public download should be 403
        r1 = api.post(f"{BASE_URL}/api/illustrations/{oid}/download", timeout=15)
        assert r1.status_code == 403, f"Expected 403 got {r1.status_code} body={r1.text[:200]}"
    finally:
        requests.delete(f"{BASE_URL}/api/admin/illustrations/{oid}",
                        headers=auth_headers, timeout=15)


# ----------------------------- MongoDB indexes -----------------------------

def test_mongodb_indexes_present():
    """Connect directly to Mongo and verify each expected index exists."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient  # noqa
        import asyncio
    except Exception as e:
        pytest.skip(f"motor not available: {e}")

    mongo_url = os.environ.get("MONGO_URL") or _read_env("/app/backend/.env", "MONGO_URL")
    db_name = os.environ.get("DB_NAME") or _read_env("/app/backend/.env", "DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("MONGO_URL/DB_NAME not available in test env")

    # Expected from create_indexes.PERF_INDEXES
    expected = [
        ("illustrations", "ix_id_isPublished"),
        ("illustrations", "ix_isPublished"),
        ("posters", "ix_id_status"),
        ("posters", "ix_status"),
        ("books", "ix_id"),
        ("books", "ix_slug"),
        ("book_scenes", "ix_bookId_sceneNumber"),
        ("book_scenes", "ix_id_bookId"),
        ("bundles", "ix_id"),
        ("games", "ix_id"),
        ("games", "ix_slug"),
        ("themes", "ix_id"),
        ("game_level_backgrounds", "ix_id"),
        ("generation_styles", "ix_id_userId"),
        ("character_images", "ix_trait"),
        ("reviews", "ix_is_approved"),
        ("reading_progress", "ix_bookId_visitorId"),
        ("download_limits", "ix_key"),
        ("admins", "ix_email"),
        ("site_settings", "ix_id"),
    ]

    async def run():
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=15000)
        db = client[db_name]
        missing = []
        for coll, name in expected:
            idxs = await db[coll].list_indexes().to_list(1000)
            names = {i.get("name") for i in idxs}
            if name not in names:
                missing.append(f"{coll}.{name}")
        client.close()
        return missing

    missing = asyncio.get_event_loop().run_until_complete(run()) \
        if sys.version_info < (3, 10) else asyncio.run(run())
    assert not missing, f"Missing indexes: {missing}"


def _read_env(path, key):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return val
    except Exception:
        return None
    return None
