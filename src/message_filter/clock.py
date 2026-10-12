import os

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo(os.environ.get("TIMEZONE", "America/New_York"))


def local_today(now: datetime | None = None) -> date:
    now = now or datetime.now(timezone.utc)
    return now.astimezone(LOCAL_TZ).date()