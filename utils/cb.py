# utils/cb.py
import re
from functools import wraps
import logging
log = logging.getLogger("luvbot.cb")

MAX_CB_LEN = 128

class CBError(ValueError):
    pass

def cb_parts(data: str, expected_prefix: str = None, min_parts: int = 2, max_parts: int = 6):
    """Safe split with length guard + optional prefix check."""
    if not data or not isinstance(data, str) or len(data) > MAX_CB_LEN:
        raise CBError("Callback too long/invalid")
    parts = data.split(":")
    if expected_prefix and (not parts or parts[0] != expected_prefix):
        raise CBError("Bad prefix")
    if not (min_parts <= len(parts) <= max_parts):
        raise CBError("Bad arity")
    return parts

def cb_match(data: str, pattern: str):
    """Strict regex match; returns dict of named groups."""
    if not data or not isinstance(data, str) or len(data) > MAX_CB_LEN:
        raise CBError("Callback too long/invalid")
    m = re.fullmatch(pattern, data)
    if not m:
        raise CBError("Pattern mismatch")
    return m.groupdict()

def guard_cb(pattern: str):
    """
    Decorator to validate callback with a regex pattern.
    Handler signature: async def fn(update, context, m: dict)
    """
    def deco(fn):
        @wraps(fn)
        async def wrapper(update, context, *a, **k):
            q = update.callback_query
            try:
                m = cb_match(q.data or "", pattern)
                return await fn(update, context, m, *a, **k)
            except CBError as e:
                log.warning(f"CB guard: {e} data={q.data!r}")
                try: 
                    await q.answer("Invalid or expired action.", show_alert=True)
                except Exception as ee:
                    log.warning(f"CB guard notify failed: {ee}")
            except Exception:
                log.exception(f"CB handler crashed data={getattr(q,'data',None)!r}")
                try: 
                    await q.answer("Something went wrong.", show_alert=True)
                except Exception as ee:
                    log.warning(f"CB crash notify failed: {ee}")
        return wrapper
    return deco