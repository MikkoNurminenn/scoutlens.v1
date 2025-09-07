from datetime import datetime
from zoneinfo import ZoneInfo


def to_tz(dt_iso: str, tz: str) -> datetime:
    """Parse ISO timestamp and convert to timezone tz."""
    dt = datetime.fromisoformat(str(dt_iso).replace("Z", "+00:00"))
    return dt.astimezone(ZoneInfo(tz))

