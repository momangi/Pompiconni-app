"""Business rules for site_settings.

This service composes:
    * The public response shape returned by ``GET /api/site-settings``
      (legal fields, social URLs, brand/hero assets presence flags).
    * The admin GET that includes the ``stripe_configured`` boolean.
    * The PUT helpers used by admin (legal/show toggles) and social links.

The legacy response shape is preserved byte-for-byte. Any future cleanup
of the legal-flag duplication should be done as a dedicated phase.
"""
from core.config import settings as app_settings
from repositories import settings_repo
from repositories.base import stringify_id


# --- Public composition -------------------------------------------------------

async def get_public_payload() -> dict:
    """Compose the dictionary returned by ``GET /api/site-settings``.

    The exact key/value semantics are pulled byte-for-byte from
    ``server.py`` to preserve the contract used by the frontend.
    """
    s = await settings_repo.find_global()
    stripe_enabled = (
        bool(app_settings.stripe_secret_key) if not s
        else s.get("stripe_enabled", False)
    )
    has_hero = bool(s and s.get("heroImageFileId")) if s else False
    show_bundles = s.get("showBundlesSection", True) if s else True
    has_brand_logo = bool(s and s.get("brandLogoFileId")) if s else False

    return {
        "stripe_enabled": stripe_enabled,
        "stripe_publishable_key": app_settings.stripe_publishable_key if stripe_enabled else None,
        "hasHeroImage": has_hero,
        "heroImageUrl": "/api/site/hero-image" if has_hero else None,
        "showBundlesSection": show_bundles,
        "hasBrandLogo": has_brand_logo,
        "brandLogoUrl": "/api/site/brand-logo" if has_brand_logo else None,
        "instagramUrl": s.get("instagramUrl", "") if s else "",
        "tiktokUrl": s.get("tiktokUrl", "") if s else "",
        # Legal contact info with visibility flags
        "legalCompanyName": s.get("legal_company_name", "") if s else "",
        "showLegalCompanyName": s.get("show_legal_company_name", True) if s else True,
        "legalAddress": s.get("legal_address", "") if s else "",
        "showLegalAddress": s.get("show_legal_address", True) if s else True,
        "legalVatNumber": s.get("legal_vat_number", "") if s else "",
        "showLegalVatNumber": s.get("show_legal_vat_number", True) if s else True,
        "legalEmail": s.get("legal_email", "") if s else "",
        "showLegalEmail": s.get("show_legal_email", True) if s else True,
        "legalPecEmail": s.get("legal_pec_email", "") if s else "",
        "showLegalPecEmail": s.get("show_legal_pec_email", True) if s else True,
    }


# --- Admin composition --------------------------------------------------------

async def get_admin_payload() -> dict:
    """Return the admin view of settings.

    Legacy behaviour: if no document exists yet, return a minimal default
    (with ``id="global"`` and ``show_reviews=True``); otherwise return the
    persisted document with ``_id`` stringified. Always include
    ``stripe_configured``.
    """
    s = await settings_repo.find_global()
    if not s:
        s = {
            "id": "global",
            "show_reviews": True,
            "stripe_enabled": bool(app_settings.stripe_secret_key),
        }
    s = stringify_id(s)
    s["stripe_configured"] = bool(app_settings.stripe_secret_key)
    return s


# --- Admin mutations ----------------------------------------------------------

# Allowed PUT fields and their persistence keys. The Pydantic
# ``SiteSettingsUpdate`` model uses identical field names, so the legacy
# behaviour (only update keys explicitly provided) is preserved here.
_UPDATE_FIELDS = (
    "show_reviews",
    "legal_company_name",
    "show_legal_company_name",
    "legal_address",
    "show_legal_address",
    "legal_vat_number",
    "show_legal_vat_number",
    "legal_email",
    "show_legal_email",
    "legal_pec_email",
    "show_legal_pec_email",
)


async def update_admin_settings(update_model) -> None:
    """Apply a partial update from the admin UI.

    Only fields whose value is not ``None`` are written, matching the
    legacy code. ``updatedAt`` is stamped by the repository.
    """
    update_data: dict = {}
    for field in _UPDATE_FIELDS:
        value = getattr(update_model, field, None)
        if value is not None:
            update_data[field] = value
    await settings_repo.update_global(update_data, touch_updated_at=True)


async def update_social_links(instagram_url: str, tiktok_url: str) -> dict:
    """Persist the two social URLs and echo them back to the client.

    Legacy semantics: no ``updatedAt`` stamp on this endpoint.
    """
    await settings_repo.update_global(
        {"instagramUrl": instagram_url, "tiktokUrl": tiktok_url},
        touch_updated_at=False,
    )
    return {"success": True, "instagramUrl": instagram_url, "tiktokUrl": tiktok_url}
