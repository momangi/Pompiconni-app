"""Public illustrations search router (Fase 5/M1).

Token-based relevance scoring over title/description/theme/keywords with
no external search engine. Logic preserved verbatim from the legacy
``server.py``.
"""
import re

from fastapi import APIRouter

from core.database import db


router = APIRouter()


@router.get("/search/illustrations")
async def search_illustrations(q: str = "", limit: int = 48):
    """Public search endpoint for illustrations.

    Returns both free and premium illustrations sorted by relevance score.
    """
    if not q or not q.strip():
        return {"q": "", "results": []}

    query_normalized = q.lower().strip()
    query_normalized = re.sub(r"[^\w\s]", "", query_normalized)

    if not query_normalized:
        return {"q": q, "results": []}

    tokens = [t for t in query_normalized.split() if len(t) >= 2]
    if not tokens:
        return {"q": q, "results": []}

    illustrations = await db.illustrations.find(
        {"isPublished": True}, {"_id": 0}
    ).to_list(1000)

    themes = await db.themes.find({}, {"_id": 0}).to_list(100)
    theme_map = {t["id"]: t.get("name", "") for t in themes}

    results = []
    for illust in illustrations:
        score = 0
        title = (illust.get("title", "") or "").lower()
        description = (illust.get("description", "") or "").lower()
        theme_name = theme_map.get(illust.get("themeId", ""), "").lower()
        keywords = (illust.get("keywords", "") or "").lower()

        # +20 if title contains entire query
        if query_normalized in title:
            score += 20

        # Per-token scoring
        for token in tokens:
            if token in title:
                score += 10
            if token in description:
                score += 6
            if token in theme_name:
                score += 4
            if token in keywords:
                score += 3

        if score > 0:
            results.append({
                "id": illust.get("id"),
                "title": illust.get("title", ""),
                "description": illust.get("description", ""),
                "isFree": illust.get("isFree", True),
                "price": illust.get("price", 0),
                "imageFileId": illust.get("imageFileId"),
                "themeName": theme_map.get(illust.get("themeId", ""), ""),
                "themeId": illust.get("themeId"),
                "score": score,
            })

    # Sort by score desc, then title asc for tie-break
    results.sort(key=lambda x: (-x["score"], x["title"].lower()))
    results = results[:limit]

    return {"q": q, "results": results}
