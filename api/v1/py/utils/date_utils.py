"""Date helpers: one timezone for the whole API and UTC for storage.

Layer: utils (cross-cutting). Timestamps are stored in UTC (naive datetime,
because MySQL DATETIME has no offset) and rendered in APP_TIMEZONE, which is
America/Tijuana by default. Never use datetime.now() directly: it would depend
on the machine clock settings.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from core.Settings import settings

LOCAL_TZ = ZoneInfo(settings.APP_TIMEZONE)


def utc_now():
    """Current UTC time as a naive datetime (what DATETIME columns store)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_now():
    """Current time as an aware datetime in APP_TIMEZONE."""
    return datetime.now(LOCAL_TZ)


def utc_from_timestamp(epoch):
    """Epoch seconds -> naive UTC datetime (for DATETIME columns)."""
    return datetime.fromtimestamp(epoch, timezone.utc).replace(tzinfo=None)


def to_local(value):
    """Naive UTC datetime (from the database) -> aware datetime in APP_TIMEZONE."""
    return value.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)


def isoformat_local(value):
    """ISO 8601 string in APP_TIMEZONE, e.g. 2026-11-14T15:04:05-08:00."""
    return to_local(value).isoformat()


def isoformat_from_timestamp(epoch):
    """Epoch seconds -> ISO 8601 string in APP_TIMEZONE."""
    return datetime.fromtimestamp(epoch, LOCAL_TZ).isoformat()
