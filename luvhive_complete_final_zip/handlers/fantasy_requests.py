# handlers/fantasy_requests.py
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import registration as reg
# Unified imports from fantasy_common with fallback for legacy analyzers
try:
    from handlers.fantasy_common import (
        db_exec, _exec, _exec_legacy,
        get_message, reply_any, edit_or_send,
        effective_uid, get_display_name, _get_display_name, get_chat_id
    )
except Exception:
    from handlers.fantasy_common import (
        db_exec, get_message, reply_any, edit_or_send,
        effective_uid, get_display_name, _get_display_name, get_chat_id
    )
    _exec = db_exec
    _exec_legacy = db_exec

log = logging.getLogger("fantasy_requests")

# Using _get_display_name from fantasy_common

def _q(update):
    return getattr(update, "callback_query", None)

def _qd(update):
    q = _q(update)
    return getattr(q, "data", "") if q else ""

def _qmsg(update):
    q = _q(update)
    return getattr(q, "message", None) if q else None

INVITE_TTL_MIN = 60
CHAT_MINUTES   = 30
PENDING_PAGE_SIZE = 10

# Using unified db_exec from fantasy_common instead

def _exec_tx(sql, params=()):
    """Execute SQL in transaction with FOR UPDATE locking"""
    with reg._conn() as con:
        con.autocommit = False
        try:
            with con.cursor() as cur:
                cur.execute(sql, params)
                if cur.description:
                    result = cur.fetchall()
                    con.commit()
                    return result
                con.commit()
                return []
        except Exception:
            con.rollback()
            raise

def _g_of(uid: int) -> str:  # m|f|u
    prof = reg.get_profile(uid) or {}
    g = str(prof.get("gender", "")).lower()
    if g.startswith("m"): return "m"
    if g.startswith("f"): return "f"
    return "u"

def _gender_label(user_id: int) -> str:
    g = (_g_of(user_id) or "").lower()
    if g.startswith("f"):
        return "A Girl"
    if g.startswith("m"):
        return "A Boy"
    return "Someone"

def _male_needs_premium(uid: int) -> bool:
    return _g_of(uid) == "m" and not reg.has_active_premium(uid)

async def cancel_match_request_atomic(user_id: int, request_id: int, reason: str = None) -> dict:
    """
    Atomically cancel a match request with proper locking and notifications.

    Returns:
        {"success": bool, "error": str, "cancelled_by_name": str, "other_user_id": int}
    """
    try:
        with reg._conn() as con:
            con.autocommit = False
            try:
                with con.cursor() as cur:
                    # Step 1: Lock and fetch the request
                    cur.execute("""
                        SELECT requester_id, fantasy_owner_id, status, version
                        FROM fantasy_match_requests 
                        WHERE id = %s 
                        FOR UPDATE
                    """, (request_id,))

                    row = cur.fetchone()
                    if not row:
                        return {"success": False, "error": "Request not found"}

                    requester_id, fantasy_owner_id, status, version = row

                    # Step 2: Check authorization (only sender or recipient can cancel)
                    if user_id not in [requester_id, fantasy_owner_id]:
                        return {"success": False, "error": "Not authorized to cancel this request"}

                    # Step 3: Check if already processed (idempotent check)
                    if status == 'cancelled':
                        # Already cancelled - return success (idempotent)
                        cur.execute("""
                            SELECT cancelled_by_user_id FROM fantasy_match_requests 
                            WHERE id = %s
                        """, (request_id,))
                        row = cur.fetchone()
                        cancelled_by = (row[0] if row and row[0] is not None else user_id)
                        other_user = fantasy_owner_id if user_id == requester_id else requester_id
                        return {
                            "success": True, 
                            "error": None,
                            "cancelled_by_name": _get_display_name(cancelled_by),
                            "other_user_id": other_user
                        }

                    if status != 'pending':
                        return {"success": False, "error": f"Request already {status}"}

                    # Step 4: Atomically update the request
                    cur.execute("""
                        UPDATE fantasy_match_requests 
                        SET status = 'cancelled',
                            cancelled_by_user_id = %s,
                            cancelled_at = NOW(),
                            cancel_reason = %s,
                            version = version + 1
                        WHERE id = %s AND version = %s
                    """, (user_id, reason, request_id, version))

                    if cur.rowcount == 0:
                        # Concurrent update occurred
                        return {"success": False, "error": "Request was modified by another operation"}

                    # Step 5: Determine other user for notification
                    other_user_id = fantasy_owner_id if user_id == requester_id else requester_id
                    cancelled_by_name = _get_display_name(user_id)

                    con.commit()

                    log.info(f"[fantasy_requests] Request {request_id} cancelled by user {user_id}")

                    return {
                        "success": True,
                        "error": None,
                        "cancelled_by_name": cancelled_by_name,
                        "other_user_id": other_user_id
                    }

            except Exception as e:
                con.rollback()
                log.error(f"[fantasy_requests] Cancel transaction failed: {e}")
                raise

    except Exception as e:
        log.error(f"[fantasy_requests] Cancel request failed for user {user_id}, request {request_id}: {e}")
        return {"success": False, "error": "Database error occurred"}

# Using _get_display_name from fantasy_common

async def notify_request_cancelled(context: ContextTypes.DEFAULT_TYPE, cancelled_by_name: str, other_user_id: int, request_id: int):
    """Send cancellation notification to the other user"""
    try:
        # Send push notification
        notification_text = f"🚫 **Match Request Cancelled**\n\n{cancelled_by_name} cancelled the fantasy match request.\n\n*You can send a new request anytime.*"

        await context.bot.send_message(
            other_user_id,
            notification_text,
            parse_mode=ParseMode.MARKDOWN
        )

        log.info(f"[fantasy_requests] Sent cancellation notification to user {other_user_id}")

    except Exception as e:
        log.warning(f"[fantasy_requests] Failed to notify user {other_user_id} about cancellation: {e}")


async def _auto_delete(context: ContextTypes.DEFAULT_TYPE):
    # JobQueue callback: expects data=(chat_id, message_id). Safe no-op if missing.
    job = getattr(context, "job", None)
    if not job:
        return

    data = getattr(job, "data", None)
    if not (isinstance(data, (tuple, list)) and len(data) == 2):
        return

    chat_id, msg_id = data
    try:
        await context.bot.delete_message(chat_id, msg_id)
    except Exception:
        # Message may already be gone; ignore
        pass

def ensure_match_request_table():
    with reg._conn() as con, con.cursor() as cur:
        # main table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS fantasy_match_requests(
            id              BIGSERIAL PRIMARY KEY,
            requester_id    BIGINT NOT NULL,
            fantasy_id      BIGINT,
            fantasy_owner_id BIGINT NOT NULL,
            status          TEXT   NOT NULL DEFAULT 'pending',  -- pending/accepted/declined/cancelled/expired
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at      TIMESTAMPTZ,
            cancelled_by_user_id BIGINT,
            cancelled_at    TIMESTAMPTZ,
            cancel_reason   TEXT,
            version         INTEGER DEFAULT 1
        )""")

        # add expires_at if a very old DB is missing it
        cur.execute("ALTER TABLE fantasy_match_requests ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ")
        cur.execute("ALTER TABLE fantasy_match_requests ADD COLUMN IF NOT EXISTS cancelled_by_user_id BIGINT")
        cur.execute("ALTER TABLE fantasy_match_requests ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ")
        cur.execute("ALTER TABLE fantasy_match_requests ADD COLUMN IF NOT EXISTS cancel_reason TEXT")
        cur.execute("ALTER TABLE fantasy_match_requests ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1")

        # safety: fill expires_at for existing rows that are NULL (60 min TTL default)
        cur.execute("""
            UPDATE fantasy_match_requests
               SET expires_at = created_at + INTERVAL '60 minutes'
             WHERE expires_at IS NULL
        """)
        
        # Set defaults for existing rows
        cur.execute("UPDATE fantasy_match_requests SET status='pending' WHERE status IS NULL")
        cur.execute("UPDATE fantasy_match_requests SET created_at=NOW() WHERE created_at IS NULL")
        cur.execute("UPDATE fantasy_match_requests SET version=1 WHERE version IS NULL")

        # indexes (wrap each in try to avoid race on parallel startups)
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS fmr_owner_status ON fantasy_match_requests(fantasy_owner_id, status)")
        except Exception:
            pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS fmr_exp ON fantasy_match_requests(expires_at)")
        except Exception:
            pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS fmr_requester_status ON fantasy_match_requests(requester_id, status)")
        except Exception:
            pass
        con.commit()

# ---------- 1) Requester taps "Chat #n" from Board ----------
async def start_connect_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, fantasy_id: int):
    """
    If requester is male w/o premium -> show neutral premium upsell (no request is sent).
    Otherwise -> send consent request to owner. Also show an ephemeral 'Request sent!' that auto-deletes.
    """
    ensure_match_request_table()

    uid = effective_uid(update)
    if uid is None:
        return await reply_any(update, context, "❌ Invalid request.")

    # Premium gate for male requesters (neutral copy)
    if _male_needs_premium(uid):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ Get Premium", callback_data="fant:open_premium")],
            [InlineKeyboardButton("⬅️ Back",        callback_data="fant:back")],
        ])
        # edit message if this came from a callback; otherwise send
        return await edit_or_send(
            update, context,
            "⭐ *Premium needed*\n\nTo request a chat as a male user, please upgrade to Premium.",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb
        )

    # Fetch target fantasy (owner + details) using reliable database connection
    try:
        from handlers.fantasy_match import get_db
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, fantasy_text, vibe, gender
                FROM fantasy_submissions
                WHERE id = %s AND active = TRUE
            """, (fantasy_id,))
            result = cur.fetchone()
            
            if not result:
                return await edit_or_send(update, context, "❌ This fantasy is no longer available.")
            
            owner, fantasy_text, vibe, owner_g = result
            log.info(f"[fantasy_requests] Successfully fetched fantasy {fantasy_id}: owner={owner}, vibe={vibe}")
            
    except Exception as e:
        log.error(f"[fantasy_requests] Database error fetching fantasy {fantasy_id}: {e}")
        return await edit_or_send(update, context, "❌ Error accessing fantasy data.")
    if owner == uid:
        return await edit_or_send(update, context, "That's yours 😄 Pick someone else!")

    # Get requester's gender for anonymous display
    try:
        from handlers.fantasy_match import get_db
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT gender FROM users WHERE tg_user_id = %s", (uid,))
            requester_result = cur.fetchone()
            requester_gender = requester_result[0] if requester_result else 'unknown'
    except Exception as e:
        log.error(f"[fantasy_requests] Error getting requester gender: {e}")
        requester_gender = 'unknown'
    
    # Determine anonymous display text
    if requester_gender and requester_gender.lower() in ['m', 'male', 'boy']:
        gender_display = "A boy"
    elif requester_gender and requester_gender.lower() in ['f', 'female', 'girl']:
        gender_display = "A girl"
    else:
        gender_display = "Someone"

    # Record pending request (60 min TTL)
    exp = datetime.utcnow() + timedelta(minutes=INVITE_TTL_MIN)
    _exec("""
        INSERT INTO fantasy_match_requests(requester_id, fantasy_id, fantasy_owner_id, status, created_at, expires_at)
        VALUES (%s,%s,%s,'pending',NOW(),%s)
    """, (uid, fantasy_id, owner, exp))

    # Notify the owner with Accept/Reject buttons (anonymous format)
    msg_owner = (
        f"🤝 **FANTASY MATCH REQUEST** 🤝\n\n"
        f"🔥 {gender_display} wants to make your fantasy reality:\n\n"
        f"💭 \"{fantasy_text}\"\n\n"
        f"Would you like to start a {CHAT_MINUTES}-minute anonymous chat?"
    )
    kb_owner = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Let's Chat!", callback_data=f"request:accept:{fantasy_id}:{uid}")],
        [InlineKeyboardButton("❌ No Thanks",        callback_data=f"request:reject:{fantasy_id}:{uid}")],
    ])
    try:
        await context.bot.send_message(owner, msg_owner, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_owner)
    except Exception as e:
        log.warning(f"notify owner failed: {e}")

    # Ephemeral ack to the requester (auto-delete after 10s), with full null-safety
    chat_id = get_chat_id(update)
    if chat_id:
        try:
            m: Message = await context.bot.send_message(chat_id, "✅ Request sent! They have 60 minutes to accept.")
            jq = getattr(context, "job_queue", None)
            if jq:
                jq.run_once(_auto_delete, when=10, data=(m.chat.id, m.message_id))
        except Exception:
            pass
    else:
        await reply_any(update, context, "✅ Request sent! They have 60 minutes to accept.")

# ---------- 2) Pending list (viewer side) ----------
def _fmt_preview(fid):
    """Format fantasy preview with reliable database connection"""
    try:
        from handlers.fantasy_match import get_db
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT vibe, gender, fantasy_text FROM fantasy_submissions WHERE id = %s", (fid,))
            result = cur.fetchone()
            
            if not result:
                return "(deleted)", "🧑"
            
            vibe, g, txt = result
            vibe = (vibe or "").capitalize()
            g_emoji = "👩" if (g or "").lower().startswith("f") else "👨" if (g or "").lower().startswith("m") else "🧑"
            preview = (txt or "").strip().replace("\n", " ")
            if len(preview) > 40:
                preview = preview[:39] + "…"
            return f"*{vibe}* — \"{preview}\"", g_emoji
    except Exception as e:
        log.error(f"[fantasy_requests] Database error in _fmt_preview: {e}")
        return "(error)", "🧑"

async def _show_pending(update, context, tab="out", page=0):
    """tab: 'out' => requests I sent; 'in' => requests for me"""
    q = getattr(update, "callback_query", None)
    if not q or not getattr(q, "from_user", None):
        return await reply_any(update, context, "❌ Invalid request.")
    uid = q.from_user.id
    offset = page * PENDING_PAGE_SIZE
    now = datetime.utcnow().replace(tzinfo=timezone.utc)

    # Fetch pending requests using reliable database connection
    try:
        from handlers.fantasy_match import get_db
        with get_db() as conn:
            cur = conn.cursor()
            
            if tab == "out":
                cur.execute("""
                    SELECT id, fantasy_id, expires_at
                      FROM fantasy_match_requests
                     WHERE requester_id = %s AND status = 'pending'
                  ORDER BY expires_at ASC
                     LIMIT %s OFFSET %s
                """, (uid, PENDING_PAGE_SIZE, offset))
            else:
                cur.execute("""
                    SELECT id, fantasy_id, expires_at, requester_id
                      FROM fantasy_match_requests
                     WHERE fantasy_owner_id = %s AND status = 'pending'
                  ORDER BY expires_at ASC
                     LIMIT %s OFFSET %s
                """, (uid, PENDING_PAGE_SIZE, offset))
            
            rows = cur.fetchall() or []
    except Exception as e:
        log.error(f"[fantasy_requests] Database error in _show_pending: {e}")
        rows = []

    # Header + tab row
    tab_row = [
        InlineKeyboardButton(("🟦 Sent" if tab=="out" else "Sent"), callback_data=f"request:pending:out:0"),
        InlineKeyboardButton(("🟦 For You" if tab=="in" else "For You"), callback_data=f"request:pending:in:0"),
    ]

    if not rows:
        kb = InlineKeyboardMarkup([
            tab_row,
            [InlineKeyboardButton("🔁 Refresh", callback_data=f"request:pending:{tab}:{page}")],
            [InlineKeyboardButton("⬅️ Back",    callback_data="fant:back")],
        ])
        return await q.edit_message_text(
            "⏳ *No pending requests here.*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )

    lines = [f"⏳ *Pending Matches — {'Sent' if tab=='out' else 'For You'}*"]
    btn_rows = []

    for idx, row in enumerate(rows, start=1):
        if tab == "out":
            rid, fid, exp = row
            requester = uid
        else:
            rid, fid, exp, requester = row

        exp = exp if (hasattr(exp, "tzinfo") and exp.tzinfo) else exp.replace(tzinfo=timezone.utc)
        mins = max(0, int((exp - now).total_seconds() // 60))
        preview, g_emoji = _fmt_preview(fid)
        lines.append(f"{idx}. {g_emoji} {preview} · *{mins} min left*")

        if tab == "out":
            btn_rows.append([InlineKeyboardButton(f"❌ Cancel #{idx}", callback_data=f"request:cancel:{rid}:{tab}:{page}")])
        else:
            # owner can accept/decline from the list
            btn_rows.append([
                InlineKeyboardButton(f"✅ Accept #{idx}", callback_data=f"request:accept:{fid}:{requester}:{tab}:{page}"),
                InlineKeyboardButton(f"❌ Decline #{idx}", callback_data=f"request:reject:{fid}:{requester}:{tab}:{page}"),
            ])

    nav = [
        InlineKeyboardButton("◀️ Prev", callback_data=f"request:pending:{tab}:{max(page-1,0)}"),
        InlineKeyboardButton("Next ▶️", callback_data=f"request:pending:{tab}:{page+1}")
    ]
    footer = [
        tab_row,
        nav,
        [InlineKeyboardButton("🔁 Refresh", callback_data=f"request:pending:{tab}:{page}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="fant:back")],
    ]
    await q.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(btn_rows + footer)
    )

async def cleanup_expired_requests():
    """Background job to mark expired requests and notify users"""
    try:
        # Mark expired requests
        expired_requests = _exec("""
            UPDATE fantasy_match_requests 
            SET status = 'expired'
            WHERE status = 'pending' 
            AND expires_at <= NOW()
            RETURNING id, requester_id, fantasy_owner_id
        """)

        if expired_requests:
            log.info(f"[fantasy_requests] Marked {len(expired_requests)} requests as expired")

            # Optional: Send expiry notifications
            for req_id, requester_id, owner_id in expired_requests:
                # Notify both parties that request expired
                pass  # Implement if needed

    except Exception as e:
        log.error(f"[fantasy_requests] Cleanup expired requests failed: {e}")

async def on_request_callback(update, context):
    q = _q(update)
    if not q:
        return
    msg = _qmsg(update)
    if not msg:
        return
    data = _qd(update)
    if not data:
        await q.answer()
        return
    await q.answer()

    # tabs + paging
    if data.startswith("request:pending"):
        parts = data.split(":")
        # formats supported:
        # request:pending:0              (legacy -> sent/out)
        # request:pending:out:0
        # request:pending:in:0
        if len(parts) == 3:      # legacy
            return await _show_pending(update, context, tab="out", page=int(parts[2]))
        tab = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 0
        return await _show_pending(update, context, tab=tab, page=page)

    if data.startswith("request:cancel:"):
        # formats: request:cancel:<req_id>:<tab>:<page>
        _, _, rid, tab, page = data.split(":")
        rid = int(rid)
        uid = q.from_user.id

        # fetch BEFORE updating so we know who to notify
        row = _exec("""
            SELECT requester_id, fantasy_owner_id, status
            FROM fantasy_match_requests
            WHERE id=%s
        """, (rid,), fetch="one")
        if not row:
            await q.answer("Already gone.")
            return await _show_pending(update, context, tab=tab, page=int(page))

        requester_id, owner_id, status = row
        if requester_id != uid or status != "pending":
            await q.answer("Already handled.")
            return await _show_pending(update, context, tab=tab, page=int(page))

        # mark cancelled
        _exec("""UPDATE fantasy_match_requests
                    SET status='cancelled'
                  WHERE id=%s AND requester_id=%s AND status='pending'""",
              (rid, uid))

        # tell the other side
        try:
            label = _gender_label(uid)
            await context.bot.send_message(
                owner_id,
                f"❌ {label} cancelled the fantasy chat request."
            )
        except Exception:
            pass

        await q.answer("Cancelled.")
        return await _show_pending(update, context, tab=tab, page=int(page))

    if data.startswith("request:reject:"):
        # supports ...:fid:requester or ...:fid:requester:tab:page
        parts = data.split(":")
        fid = int(parts[2]); requester = int(parts[3])
        _exec("""UPDATE fantasy_match_requests
                    SET status='rejected'
                  WHERE fantasy_id=%s AND requester_id=%s AND status='pending'""",
              (fid, requester))
        try: await q.edit_message_text("✅ Declined.")
        except: pass
        try: await context.bot.send_message(requester, "❌ Your fantasy chat request was declined.")
        except: pass
        if len(parts) >= 6:   # came from pending list (in-tab)
            return await _show_pending(update, context, tab=parts[4], page=int(parts[5]))
        return

    if data.startswith("request:accept:"):
        # supports ...:fid:requester or ...:fid:requester:tab:page
        parts = data.split(":")
        fid = int(parts[2]); requester = int(parts[3])

        # Fetch fantasy details using reliable database connection
        try:
            from handlers.fantasy_match import get_db
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT user_id, vibe FROM fantasy_submissions WHERE id = %s AND active = TRUE", (fid,))
                result = cur.fetchone()
                
                if not result:
                    try: await q.edit_message_text("❌ No longer available.")
                    except: pass
                    return
                
                owner, vibe = result
        except Exception as e:
            log.error(f"[fantasy_requests] Database error in accept: {e}")
            try: await q.edit_message_text("❌ Error processing request.")
            except: pass
            return

        # premium gating (neutral copy)
        if _male_needs_premium(owner):
            return await q.edit_message_text(
                "💎 *Premium required to start Fantasy Match.*\nUpgrade to continue.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")]])
            )
        if _male_needs_premium(requester):
            try:
                await context.bot.send_message(
                    requester,
                    "💎 *Premium required to start Fantasy Match.*\nUpgrade to continue.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")]])
                )
            except Exception:
                pass
            try: await q.edit_message_text("⏳ Waiting for them to upgrade.")
            except Exception: pass
            return

        # mark accepted
        _exec("""UPDATE fantasy_match_requests
                    SET status='accepted'
                  WHERE fantasy_id=%s AND requester_id=%s AND status='pending'""",
              (fid, requester))

        # notify first (so order is correct), then start chat
        try: await q.edit_message_text("🎉 Connected! Opening chat…")
        except Exception: pass
        try: await context.bot.send_message(requester, "🎉 Your request was accepted. Opening chat…")
        except Exception: pass

        from . import fantasy_relay
        match_id = int(datetime.utcnow().timestamp())
        await fantasy_relay.start_fantasy_chat(
            context=context,
            match_id=match_id,
            boy_id=requester,
            girl_id=owner,
            duration_minutes=30,
            vibe=vibe
        )

        if len(parts) >= 6:   # came from pending list (in-tab)
            # Best-effort refresh (will be replaced by chat messages anyway)
            try:
                await _show_pending(update, context, tab=parts[4], page=int(parts[5]))
            except Exception:
                pass
        return