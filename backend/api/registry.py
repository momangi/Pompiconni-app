"""Central router registry (Fase 5/M4).

Single place where every domain router (public, admin, and their media
sub-packages) is wired onto the two top-level API routers. ``server.py``
calls :func:`register_routers` once during bootstrap, keeping the entry
file free of import noise.

Mounting order matches the legacy ``server.py`` verbatim to preserve
FastAPI route matching priority.
"""
from fastapi import APIRouter


def register_routers(api_router: APIRouter, admin_router: APIRouter) -> None:
    """Wire all public/admin/media routers onto the two top-level routers."""
    # Domain-specific public routers (Fase 4C router split)
    from api.public import (
        themes as public_themes,
        reviews as public_reviews,
        site_settings as public_site_settings,
        bundles as public_bundles,
        illustrations as public_illustrations,
        posters as public_posters,
        games as public_games,
        level_backgrounds as public_level_backgrounds,
        books as public_books,
        search as public_search,
    )
    from api.public.media import (
        themes as public_media_themes,
        illustrations as public_media_illustrations,
        bundles as public_media_bundles,
        books as public_media_books,
        posters as public_media_posters,
        games as public_media_games,
        level_backgrounds as public_media_level_backgrounds,
        site_assets as public_media_site_assets,
        character_images as public_media_character_images,
    )

    # Domain-specific admin routers (Fase 4C + 5/M1-M3)
    from api.admin import (
        auth as admin_auth,
        maintenance as admin_maintenance,
        themes as admin_themes,
        reviews as admin_reviews,
        site_settings as admin_site_settings,
        illustrations as admin_illustrations,
        bundles as admin_bundles,
        posters as admin_posters,
        games as admin_games,
        level_backgrounds as admin_level_backgrounds,
        books as admin_books,
    )
    from api.admin.media import (
        themes as admin_media_themes,
        illustrations as admin_media_illustrations,
        bundles as admin_media_bundles,
        books as admin_media_books,
        posters as admin_media_posters,
        games as admin_media_games,
        level_backgrounds as admin_media_level_backgrounds,
        site_assets as admin_media_site_assets,
        character_images as admin_media_character_images,
        styles as admin_media_styles,
        ai_generation as admin_media_ai_generation,
    )
    from api.admin import uploads as admin_uploads

    # --- Public ---
    api_router.include_router(public_themes.router)
    api_router.include_router(public_reviews.router)
    api_router.include_router(public_site_settings.router)
    api_router.include_router(public_bundles.router)
    api_router.include_router(public_illustrations.router)
    api_router.include_router(public_posters.router)
    api_router.include_router(public_games.router)
    api_router.include_router(public_level_backgrounds.router)
    api_router.include_router(public_books.router)
    api_router.include_router(public_search.router)
    api_router.include_router(public_media_themes.router)
    api_router.include_router(public_media_illustrations.router)
    api_router.include_router(public_media_bundles.router)
    api_router.include_router(public_media_books.router)
    api_router.include_router(public_media_posters.router)
    api_router.include_router(public_media_games.router)
    api_router.include_router(public_media_level_backgrounds.router)
    api_router.include_router(public_media_site_assets.router)
    api_router.include_router(public_media_character_images.router)

    # --- Admin ---
    admin_router.include_router(admin_auth.router)
    admin_router.include_router(admin_maintenance.router)
    admin_router.include_router(admin_themes.router)
    admin_router.include_router(admin_reviews.router)
    admin_router.include_router(admin_site_settings.router)
    admin_router.include_router(admin_illustrations.router)
    admin_router.include_router(admin_bundles.router)
    admin_router.include_router(admin_posters.router)
    admin_router.include_router(admin_books.router)
    admin_router.include_router(admin_media_themes.router)
    admin_router.include_router(admin_media_illustrations.router)
    admin_router.include_router(admin_media_bundles.router)
    admin_router.include_router(admin_media_books.router)
    admin_router.include_router(admin_media_posters.router)
    admin_router.include_router(admin_media_site_assets.router)
    admin_router.include_router(admin_media_character_images.router)
    admin_router.include_router(admin_media_styles.router)
    admin_router.include_router(admin_media_ai_generation.router)
    admin_router.include_router(admin_uploads.router)

    # ``admin/games`` and ``admin/games/bolle-magiche/level-backgrounds``
    # were originally registered on the public ``api_router`` with an
    # explicit ``/admin/...`` path. They are mounted on ``admin_router``
    # (which already has the ``/api/admin`` prefix) to keep the final
    # paths identical.
    admin_router.include_router(admin_games.router)
    admin_router.include_router(admin_level_backgrounds.router)
    admin_router.include_router(admin_media_games.router)
    admin_router.include_router(admin_media_level_backgrounds.router)
