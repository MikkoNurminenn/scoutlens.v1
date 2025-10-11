"""Time zone utilities shared across ScoutLens pages."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Tuple

from zoneinfo import ZoneInfo

LATAM_TZS: Tuple[str, ...] = (
    "America/Bogota",
    "America/Lima",
    "America/Caracas",
    "America/La_Paz",
    "America/Santiago",
    "America/Buenos_Aires",
    "America/Sao_Paulo",
    "America/Montevideo",
    "America/Asuncion",
    "America/Mexico_City",
    "America/Guayaquil",
    "America/Quito",
)


def to_tz(dt_iso: str | datetime, tz: str) -> datetime:
    """Parse ISO timestamp and convert to timezone ``tz`` (IANA name)."""

    if isinstance(dt_iso, datetime):
        dt = dt_iso
    else:
        dt = datetime.fromisoformat(str(dt_iso).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo(tz))


def to_utc(date_obj: date, time_obj: time, tz_name: str) -> datetime:
    """Combine date & time in ``tz_name`` and convert to UTC-aware datetime."""

    local_dt = datetime.combine(date_obj, time_obj).replace(tzinfo=ZoneInfo(tz_name))
    return local_dt.astimezone(ZoneInfo("UTC"))


def utc_iso(dt: datetime | None) -> str | None:
    """Return an ISO 8601 string in UTC for ``dt`` (tolerates naive input)."""

    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("UTC")).isoformat()


__all__ = ["LATAM_TZS", "to_tz", "to_utc", "utc_iso"]

