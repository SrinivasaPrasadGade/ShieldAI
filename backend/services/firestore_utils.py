"""Small Firestore helpers shared by service modules."""

from logging_config import get_logger

logger = get_logger("shield_ai.firestore_utils")


def count_query(query) -> int | None:
    """
    Return a Firestore server-side count when the SDK supports it.
    Falls back to None so callers can choose a bounded local fallback.
    """
    try:
        aggregate_query = query.count()
        result = aggregate_query.get()
        if result and len(result) > 0:
            first = result[0]
            if hasattr(first, "value"):
                return int(first.value)
            if isinstance(first, tuple) and len(first) >= 2:
                return int(first[1])
    except Exception as exc:
        logger.debug("firestore_count_unavailable", error=str(exc))
    return None
