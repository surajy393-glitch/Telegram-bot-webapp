
# handlers/fantasy_common.py
from __future__ import annotations
from typing import Any, Iterable, Optional, Literal
from telegram import Update, Message
from telegram.ext import ContextTypes
import registration as reg

# ---- Database (one executor, stable returns) ----
Fetch = Literal["none", "one", "all", "val"]

def db_exec(sql: str, params: Iterable[Any] = (), fetch: Fetch = "none"):
    """
    - fetch='none' -> int rowcount
    - fetch='one'  -> tuple | None
    - fetch='all'  -> list[tuple]
    - fetch='val'  -> first column or None
    """
    with reg._conn() as con, con.cursor() as cur:
        cur.execute(sql, params)
        if fetch == "one":
            row = cur.fetchone(); con.commit(); return row
        if fetch == "all":
            rows = cur.fetchall(); con.commit(); return rows
        if fetch == "val":
            row = cur.fetchone(); con.commit(); return None if row is None else row[0]
        con.commit(); return cur.rowcount

# Back-compat shims (so legacy code that imports _exec/_exec_legacy keeps working)
_exec = db_exec
_exec_legacy = db_exec

# ---- Safe Telegram access (kills 90% of None crashes) ----
def get_chat_id(update: Update) -> Optional[int]:
    chat = getattr(update, "effective_chat", None)
    return getattr(chat, "id", None)

def get_message(update: Update) -> Optional[Message]:
    if getattr(update, "message", None):
        return update.message
    q = getattr(update, "callback_query", None)
    if q and getattr(q, "message", None):
        return q.message
    return None

def effective_uid(update: Update) -> Optional[int]:
    u = getattr(update, "effective_user", None)
    return getattr(u, "id", None) if u else None

async def reply_any(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kw):
    msg = get_message(update)
    if msg:
        return await msg.reply_text(text, **kw)
    chat_id = get_chat_id(update)
    if chat_id:
        return await context.bot.send_message(chat_id, text, **kw)
    return None

async def edit_or_send(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kw):
    q = getattr(update, "callback_query", None)
    if q and getattr(q, "message", None):
        try:
            return await q.edit_message_text(text, **kw)
        except Exception:
            pass
    return await reply_any(update, context, text, **kw)

# ---- User display name (define once, import everywhere) ----
def get_display_name(uid: int) -> str:
    try:
        name = db_exec(
            "SELECT COALESCE(display_name, username) FROM users WHERE tg_user_id=%s",
            (uid,), fetch="val"
        )
        return name or f"User {uid}"
    except Exception:
        return f"User {uid}"

# Back-compat alias for legacy code that calls _get_display_name
_get_display_name = get_display_name

# explicit export list (helps some analyzers)
__all__ = [
    "db_exec", "_exec", "_exec_legacy",
    "get_chat_id", "get_message", "reply_any", "edit_or_send",
    "effective_uid", "get_display_name", "_get_display_name",
]
