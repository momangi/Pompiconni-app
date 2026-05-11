"""Business rules for reviews.

The only domain rule is:
    * Public list returns ``[]`` if the global ``show_reviews`` toggle is
      ``False``; otherwise it returns only approved reviews.
"""
from repositories import review_repo, settings_repo


async def get_public_reviews() -> list[dict]:
    """Return reviews visible on the public site.

    Behaviour identical to the legacy ``GET /api/reviews`` handler:
    * fetch the global site_settings;
    * if ``show_reviews`` is explicitly False, return an empty list;
    * otherwise return approved reviews with stringified ``_id``.
    """
    settings_doc = await settings_repo.find_global()
    if settings_doc and not settings_doc.get("show_reviews", True):
        return []
    return await review_repo.list_approved()


async def get_admin_reviews() -> list[dict]:
    """Return every review for the admin view (includes non-approved)."""
    return await review_repo.list_all()


async def set_review_approval(review_id: str, is_approved: bool) -> bool:
    """Toggle approval. Returns True if a review matched, False otherwise."""
    modified = await review_repo.set_approved(review_id, is_approved)
    return modified > 0


async def delete_review(review_id: str) -> bool:
    """Delete a review. Returns True if a review was removed, False otherwise."""
    deleted = await review_repo.delete(review_id)
    return deleted > 0
