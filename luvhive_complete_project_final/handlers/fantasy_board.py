
# handlers/fantasy_board.py
import logging
from typing import List, Tuple
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import registration as reg
from handlers.fantasy_common import (
    db_exec, _exec, _exec_legacy,         # use db_exec for new code; _exec for legacy
    get_message, reply_any, edit_or_send, # safe Telegram wrappers
    effective_uid, get_display_name, _get_display_name
)
from handlers.fantasy_common import (
    db_exec, reply_any, edit_or_send, effective_uid
)

# Compatibility alias for legacy code
_exec_legacy = db_exec

log = logging.getLogger("fantasy_board")

PAGE_SIZE = 10
PREVIEW_MAX = 90

VIBE_EMOJI = {
    "romantic": "💕",
    "roleplay": "🎭",
    "wild": "🔥",
    "adventure": "⭐",
    "travel": "✈️",
    "intimate": "🌙",
}

# Using unified db_exec from fantasy_common instead

def ensure_fantasy_board_tables():
    # Kept for compatibility with request/consent flow (safe if already exists)
    _exec_legacy("""
        CREATE TABLE IF NOT EXISTS fantasy_match_requests (
          id BIGSERIAL PRIMARY KEY,
          requester_id BIGINT NOT NULL,
          fantasy_id   BIGINT NOT NULL,
          fantasy_owner_id BIGINT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          expires_at TIMESTAMPTZ NOT NULL
        )
    """)

def _short(s: str) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= PREVIEW_MAX else s[:PREVIEW_MAX - 1] + "…"

# -------- Entry points --------
async def cmd_fantasy_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = effective_uid(update)  # Use user ID instead of chat ID for private chats
    if chat_id is None:
        return await reply_any(update, context, "Could not identify user.")
    await _show_page(chat_id, context, page=0)

async def on_board_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.message or not q.message.chat:
        return
        
    data = q.data or ""
    await q.answer()

    if data == "board:open":
        return await _show_page(q.message.chat.id, context, page=0)

    # board:page:<n>
    if data.startswith("board:page:"):
        _, _, p = data.split(":", 2)
        return await _show_page(q.message.chat.id, context, page=int(p))

    # board:chat:<fantasy_id>
    if data.startswith("board:chat:"):
        fid = int(data.split(":")[2])
        from .fantasy_requests import start_connect_flow
        return await start_connect_flow(update, context, fid)

    if data == "board:refresh":
        # refresh current message by sending the first page again
        return await _show_page(q.message.chat.id, context, page=0)

    if data == "board:create":
        from . import fantasy_match
        return await fantasy_match.cmd_fantasy(update, context)

    # ignore unknowns

# -------- UI builder --------
async def _show_page(chat_id: int, context: ContextTypes.DEFAULT_TYPE, page: int):
    offset = page * PAGE_SIZE
    viewer_id = chat_id  # private chat => user_id == chat_id

    # ✅ SELF-FILTER: apni fantasies exclude
    rows = db_exec(
        """
        SELECT id, user_id, fantasy_text, vibe, gender
        FROM fantasy_submissions
        WHERE active=TRUE AND user_id <> %s
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """,
        (viewer_id, PAGE_SIZE, offset), fetch="all"
    ) or []

    header = "🔮 *FANTASY BOARD* 🔮\n\nBrowse and choose who to chat with:\n\n"
    if not rows:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="board:refresh")],
            [InlineKeyboardButton("🌟 Create Fantasy", callback_data="board:create")]
        ])
        return await reply_any({"effective_chat": {"id": chat_id}}, context, header + "_No fantasies yet._",
                              parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

    # Build numbered list
    lines = []
    for idx, (fid, _uid, text, vibe, g) in enumerate(rows, start=1):
        g_emoji = "👩" if (g or "").lower().startswith("f") else "👨" if (g or "").lower().startswith("m") else "🧑"
        v_emoji = VIBE_EMOJI.get((vibe or "").lower(), "✨")
        lines.append(f"{idx}. {v_emoji} {g_emoji} \"{_short(text)}\"")
    body = header + "\n".join(lines)

    # Buttons: one Chat button per item
    btn_rows: List[List[InlineKeyboardButton]] = []
    for idx, (fid, *_rest) in enumerate(rows, start=1):
        btn_rows.append([InlineKeyboardButton(f"💬 Chat #{idx}", callback_data=f"board:chat:{fid}")])

    # Footer: Prev/Next + Refresh + Create
    footer_rows: List[List[InlineKeyboardButton]] = []
    # Nav
    nav_row = [
        InlineKeyboardButton("◀️ Prev", callback_data=f"board:page:{max(page-1, 0)}"),
        InlineKeyboardButton("Next ▶️", callback_data=f"board:page:{page+1}" if len(rows) == PAGE_SIZE else "board:nop"),
    ]
    footer_rows.append(nav_row)
    # Refresh / Create
    footer_rows.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"board:page:{page}")])
    footer_rows.append([InlineKeyboardButton("⏳ Pending Matches", callback_data="request:pending:0")])
    footer_rows.append([InlineKeyboardButton("🌟 Create Fantasy", callback_data="board:create")])

    kb = InlineKeyboardMarkup(btn_rows + footer_rows)

    # Send message directly using bot
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=body,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
    except Exception as e:
        # Fallback without markdown
        await context.bot.send_message(
            chat_id=chat_id,
            text=body.replace('*', ''),
            reply_markup=kb
        )
