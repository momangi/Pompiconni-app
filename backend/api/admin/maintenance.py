"""Admin maintenance router (mini-batch Auth & Maintenance).

Routes covered:

* ``GET  /api/admin/dashboard``                 – aggregated counters & popular illustrations
* ``GET  /api/admin/download-stats``            – detailed download statistics
* ``POST /api/admin/reset-fake-counters``       – reset legacy seed counters
* ``POST /api/admin/maintenance/fix-brand-name`` – one-off brand-name migration

Behaviour, response shape, status codes and DB queries are preserved
verbatim from the legacy ``server.py`` implementation. The dashboard
respects the R1 fix (no ``_id`` leak in ``popularIllustrations``)
already applied in Fase 4B Batch 3.
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from api.dependencies import verify_admin
from core.config import settings as app_settings
from core.database import db


router = APIRouter()


# --- Dashboard --------------------------------------------------------------

@router.get("/dashboard")
async def admin_dashboard(email: str = Depends(verify_admin)):
    total_illustrations = await db.illustrations.count_documents({})
    total_themes = await db.themes.count_documents({})
    free_count = await db.illustrations.count_documents({"isFree": True})

    # Calculate total downloads ONLY from real download_events (source of truth)
    total_downloads = await db.download_events.count_documents({})

    # Get popular illustrations by REAL download events count
    pipeline = [
        {"$group": {"_id": "$illustrationId", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    popular_ids = await db.download_events.aggregate(pipeline).to_list(5)

    # Fetch illustration details for popular ones
    # R1 fix (Fase 4B Batch 3): _id is no longer leaked.
    popular = []
    for item in popular_ids:
        illust = await db.illustrations.find_one(
            {"id": item["_id"]}, {"_id": 0}
        )
        if illust:
            illust["downloadCount"] = item["count"]  # Real count from events
            popular.append(illust)

    # If no downloads yet, return top 5 illustrations with 0 downloads
    if not popular:
        popular = await db.illustrations.find({}, {"_id": 0}).limit(5).to_list(5)
        for p in popular:
            p["downloadCount"] = 0

    # Get download stats for last 7 days
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_downloads = await db.download_events.count_documents(
        {"downloadedAt": {"$gte": seven_days_ago}}
    )

    site_settings_doc = await db.site_settings.find_one({"id": "global"})

    return {
        "totalIllustrations": total_illustrations,
        "totalThemes": total_themes,
        "totalDownloads": total_downloads,
        "freeCount": free_count,
        "popularIllustrations": popular,
        "recentDownloads": recent_downloads,
        "stripeEnabled": bool(app_settings.stripe_secret_key),
        "showReviews": site_settings_doc.get("show_reviews", True) if site_settings_doc else True,
    }


# --- Download stats ---------------------------------------------------------

@router.get("/download-stats")
async def admin_get_download_stats(email: str = Depends(verify_admin)):
    """Get detailed download statistics"""
    total = await db.download_events.count_documents({})

    # Downloads by day (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    pipeline = [
        {"$match": {"downloadedAt": {"$gte": thirty_days_ago}}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$downloadedAt"}
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    daily_stats = await db.download_events.aggregate(pipeline).to_list(30)

    # Top 10 illustrations by downloads
    illustration_pipeline = [
        {"$group": {"_id": "$illustrationId", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    top_illustrations = await db.download_events.aggregate(
        illustration_pipeline
    ).to_list(10)

    return {
        "total": total,
        "dailyStats": daily_stats,
        "topIllustrations": top_illustrations,
    }


# --- Reset fake counters ----------------------------------------------------

@router.post("/reset-fake-counters")
async def admin_reset_fake_counters(email: str = Depends(verify_admin)):
    """Reset all download counters to 0 (removes fake demo data)"""
    result = await db.illustrations.update_many(
        {}, {"$set": {"downloadCount": 0}}
    )
    return {
        "success": True,
        "message": f"Reset contatori per {result.modified_count} illustrazioni",
        "modified_count": result.modified_count,
    }


# --- One-off brand-name fix -------------------------------------------------

@router.post("/maintenance/fix-brand-name")
async def admin_fix_brand_name(email: str = Depends(verify_admin)):
    """
    One-off maintenance endpoint to fix brand name from 'Pompiconni' to
    'Poppiconni' in all collections (illustrations, themes, reviews,
    bundles, books, book_scenes). Does NOT change technical fields
    (endpoints, variables, credentials).
    """
    results = {
        "illustrations_fixed": 0,
        "themes_fixed": 0,
        "reviews_fixed": 0,
        "bundles_fixed": 0,
        "books_fixed": 0,
        "book_scenes_fixed": 0,
    }

    old_brand = "Pompiconni"
    new_brand = "Poppiconni"

    # Illustrations (title + description)
    illustrations = await db.illustrations.find({}).to_list(1000)
    for illust in illustrations:
        updates = {}
        if old_brand in illust.get("title", ""):
            updates["title"] = illust["title"].replace(old_brand, new_brand)
        if old_brand in illust.get("description", ""):
            updates["description"] = illust["description"].replace(old_brand, new_brand)
        if updates:
            await db.illustrations.update_one({"id": illust["id"]}, {"$set": updates})
            results["illustrations_fixed"] += 1

    # Themes (name + description)
    themes = await db.themes.find({}).to_list(100)
    for theme in themes:
        updates = {}
        if old_brand in theme.get("name", ""):
            updates["name"] = theme["name"].replace(old_brand, new_brand)
        if old_brand in theme.get("description", ""):
            updates["description"] = theme["description"].replace(old_brand, new_brand)
        if updates:
            await db.themes.update_one({"id": theme["id"]}, {"$set": updates})
            results["themes_fixed"] += 1

    # Reviews (text)
    reviews = await db.reviews.find({}).to_list(100)
    for review in reviews:
        if old_brand in review.get("text", ""):
            await db.reviews.update_one(
                {"id": review["id"]},
                {"$set": {"text": review["text"].replace(old_brand, new_brand)}},
            )
            results["reviews_fixed"] += 1

    # Bundles (name + description)
    bundles = await db.bundles.find({}).to_list(100)
    for bundle in bundles:
        updates = {}
        if old_brand in bundle.get("name", ""):
            updates["name"] = bundle["name"].replace(old_brand, new_brand)
        if old_brand in bundle.get("description", ""):
            updates["description"] = bundle["description"].replace(old_brand, new_brand)
        if updates:
            await db.bundles.update_one({"id": bundle["id"]}, {"$set": updates})
            results["bundles_fixed"] += 1

    # Books (title + description)
    books = await db.books.find({}).to_list(100)
    for book in books:
        updates = {}
        if old_brand in book.get("title", ""):
            updates["title"] = book["title"].replace(old_brand, new_brand)
        if old_brand in book.get("description", ""):
            updates["description"] = book["description"].replace(old_brand, new_brand)
        if updates:
            await db.books.update_one({"id": book["id"]}, {"$set": updates})
            results["books_fixed"] += 1

    # Book scenes (text.html)
    scenes = await db.book_scenes.find({}).to_list(1000)
    for scene in scenes:
        html = scene.get("text", {}).get("html", "")
        if old_brand in html:
            await db.book_scenes.update_one(
                {"id": scene["id"]},
                {"$set": {"text.html": html.replace(old_brand, new_brand)}},
            )
            results["book_scenes_fixed"] += 1

    return {
        "success": True,
        "message": f"Brand name fixed from '{old_brand}' to '{new_brand}'",
        "results": results,
    }
