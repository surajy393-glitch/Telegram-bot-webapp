# utils/val.py
MAX_BIO = 200
MAX_POST = 1000
MAX_COMMENT = 300
MAX_CONFESSION = 500
MAX_CAPTION = 1000

def clip(s: str, limit: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= limit else s[:limit]

def safe_int(s, default=None, min_v=None, max_v=None):
    try:
        v = int(s)
        if min_v is not None and v < min_v: return default
        if max_v is not None and v > max_v: return default
        return v
    except Exception:
        return default

def allow_url(url: str) -> bool:
    return isinstance(url, str) and (url.startswith("http://") or url.startswith("https://"))