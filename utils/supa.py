from typing import Any, Dict, Optional, List


def first_row(res) -> Optional[Dict[str, Any]]:
    """Return the first row from a Supabase response or ``None``.

    Works for insert/upsert/update calls that return a list in ``res.data``.
    Any exceptions are swallowed and ``None`` is returned for safety.
    """
    try:
        data: List[Dict[str, Any]] = getattr(res, "data", None) or []
        return data[0] if data else None
    except Exception:
        return None
