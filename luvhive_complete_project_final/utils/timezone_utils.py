# utils/timezone_utils.py - UTC timezone consistency (ChatGPT Final Polish)
import datetime as dt
from typing import Optional
import logging

log = logging.getLogger(__name__)

def now_utc() -> dt.datetime:
    """Get current UTC datetime - use this instead of datetime.now()"""
    return dt.datetime.now(dt.timezone.utc)

def utc_from_timestamp(timestamp: float) -> dt.datetime:
    """Convert Unix timestamp to UTC datetime"""
    return dt.datetime.fromtimestamp(timestamp, dt.timezone.utc)

def to_utc(local_dt: dt.datetime, timezone: Optional[dt.timezone] = None) -> dt.datetime:
    """Convert local datetime to UTC"""
    if local_dt.tzinfo is None:
        # Assume local timezone if not specified
        if timezone:
            local_dt = local_dt.replace(tzinfo=timezone)
        else:
            local_dt = local_dt.replace(tzinfo=dt.timezone.utc)
    
    return local_dt.astimezone(dt.timezone.utc)

def format_for_display(utc_dt: dt.datetime, user_timezone: str = "UTC") -> str:
    """Format UTC datetime for user display (convert to their timezone)"""
    try:
        import zoneinfo
        user_tz = zoneinfo.ZoneInfo(user_timezone)
        local_dt = utc_dt.astimezone(user_tz)
        return local_dt.strftime("%Y-%m-%d %H:%M %Z")
    except:
        # Fallback to UTC if timezone conversion fails
        return utc_dt.strftime("%Y-%m-%d %H:%M UTC")

# Replace common datetime usages with UTC versions
def safe_datetime_now() -> dt.datetime:
    """Safe replacement for datetime.now() - always returns UTC"""
    return now_utc()

def safe_timestamp() -> float:
    """Get current UTC timestamp"""
    return now_utc().timestamp()