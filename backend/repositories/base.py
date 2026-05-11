"""Generic helpers shared by domain repositories.

These helpers are intentionally minimal — the goal is to centralize the
"do not leak ``_id``" rule and provide a single place to evolve the data
access conventions in future phases.
"""
from typing import Any, Iterable

# Default Mongo projection that excludes the BSON _id from results.
# Use it for endpoints that historically did NOT leak _id. Endpoints that
# *do* currently expose _id (illustrations, books, reviews list, admin
# settings) must be preserved verbatim until a dedicated fix phase.
EXCLUDE_ID_PROJECTION = {"_id": 0}


def stringify_id(doc: dict | None) -> dict | None:
    """Stringify the BSON ``_id`` field in place and return the doc.

    Behavioural twin of the inline ``r['_id'] = str(r.get('_id', ''))`` that
    appears across the legacy ``server.py``. Used by the few legacy
    endpoints that historically expose ``_id`` to the client.
    """
    if doc is None:
        return None
    if "_id" in doc and doc["_id"] is not None and not isinstance(doc["_id"], str):
        doc["_id"] = str(doc["_id"])
    return doc


def stringify_ids(docs: Iterable[dict]) -> list[dict]:
    """Apply :func:`stringify_id` to each document in the iterable."""
    return [stringify_id(d) for d in docs]


def pop_id(doc: dict | None) -> dict | None:
    """Remove ``_id`` from a doc in place (for inserts where Mongo mutates
    the input). Returns the same dict for chaining.
    """
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


# Sentinel exported so call sites read explicitly:
#   await collection.find({}, EXCLUDE_ID)
EXCLUDE_ID: dict[str, Any] = EXCLUDE_ID_PROJECTION
