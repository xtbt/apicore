"""Date helpers: one timezone for the whole API and UTC for storage.

Layer: utils (cross-cutting). Timestamps are stored in UTC (naive datetime,
because MySQL DATETIME has no offset) and rendered in APP_TIMEZONE, which is
America/Tijuana by default. Never use datetime.now() directly: it would depend
on the machine clock settings.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from core.settings import settings

LOCAL_TZ = ZoneInfo(settings.APP_TIMEZONE)


def utc_now():
    """Current UTC time as a naive datetime (what DATETIME columns store)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_from_timestamp(epoch):
    """Epoch seconds -> naive UTC datetime (for DATETIME columns)."""
    return datetime.fromtimestamp(epoch, timezone.utc).replace(tzinfo=None)


def isoformat_from_timestamp(epoch):
    """Epoch seconds -> ISO 8601 string in APP_TIMEZONE."""
    return datetime.fromtimestamp(epoch, LOCAL_TZ).isoformat()
