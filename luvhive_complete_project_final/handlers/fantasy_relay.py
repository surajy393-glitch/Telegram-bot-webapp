# handlers/fantasy_relay.py
from telegram.ext import MessageHandler, CallbackQueryHandler, CommandHandler, ContextTypes, filters
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import logging
import registration as reg
from utils.cb import cb_match
from handlers.fantasy_common import (
    db_exec, _exec, _exec_legacy,         # use db_exec for new code; _exec for legacy
    get_message, reply_any, edit_or_send, # safe Telegram wrappers
    effective_uid, get_display_name, _get_display_name
)
from handlers.fantasy_common import (
    reply_any, edit_or_send, effective_uid
)

log = logging.getLogger("fantasy_relay")

def _ensure_relay_table():
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS fantasy_chat_sessions(
            id          BIGSERIAL PRIMARY KEY,
            a_id        BIGINT NOT NULL,
            b_id        BIGINT NOT NULL,
            started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at    TIMESTAMPTZ,
            status      TEXT NOT NULL DEFAULT 'active' -- active/ended
        )""")
        cur.execute("CREATE INDEX IF NOT EXISTS fcs_a ON fantasy_chat_sessions(a_id) WHERE status='active'")
        cur.execute("CREATE INDEX IF NOT EXISTS fcs_b ON fantasy_chat_sessions(b_id) WHERE status='active'")
        con.commit()

def relay_open(a_id: int, b_id: int) -> int:
    _ensure_relay_table()
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("INSERT INTO fantasy_chat_sessions(a_id,b_id) VALUES(%s,%s) RETURNING id",(a_id,b_id))
        sid = cur.fetchone()[0]
        con.commit()
        return sid

def relay_end(a_id: int, b_id: int):
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            UPDATE fantasy_chat_sessions
               SET status='ended', ended_at=NOW()
             WHERE status='active' AND
                   ((a_id=%s AND b_id=%s) OR (a_id=%s AND b_id=%s))
        """,(a_id,b_id,b_id,a_id))
        con.commit()

# Master toggle for auto-prompts during chat
AUTO_PROMPTS = False  # << keep prompts OFF during chat

# Persistent storage keys (stored in PTB bot_data - survives restarts)
RELAY_MAP   = "fantasy_relays"   # { user_id: {"peer": peer_id, "match_id": int, "ends": datetime} }
RELAY_JOBS  = "fantasy_relay_jobs"  # { match_id: job }
RECENT_PARTNERS = "fantasy_recent_partners"  # { user_id: {"partner": peer_id, "until": datetime} }
SESSION_KEY = "fantasy_relay_session"  # user_data key for persistent sessions

# ------------- helpers -------------
def _bd(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.application.bot_data

def _relays(context: ContextTypes.DEFAULT_TYPE) -> dict:
    bd = _bd(context)
    if RELAY_MAP not in bd:
        bd[RELAY_MAP] = {}
    return bd[RELAY_MAP]

def _jobs(context: ContextTypes.DEFAULT_TYPE) -> dict:
    bd = _bd(context)
    if RELAY_JOBS not in bd:
        bd[RELAY_JOBS] = {}
    return bd[RELAY_JOBS]

def _in_relay(context: ContextTypes.DEFAULT_TYPE, uid: int) -> bool:
    return uid in _relays(context)

def _peer_of(context: ContextTypes.DEFAULT_TYPE, uid: int) -> int | None:
    rel = _relays(context).get(uid)
    return rel["peer"] if rel else None

def _recent_partners(context: ContextTypes.DEFAULT_TYPE) -> dict:
    bd = _bd(context)
    if RECENT_PARTNERS not in bd:
        bd[RECENT_PARTNERS] = {}
    return bd[RECENT_PARTNERS]

def _get_recent_partner(context: ContextTypes.DEFAULT_TYPE, uid: int) -> int | None:
    """Get recent partner within 15 minutes for post-chat reporting"""
    recent = _recent_partners(context)
    entry = recent.get(uid)
    if not entry:
        return None
    
    # Check if still within 15-minute window
    if datetime.utcnow() >= entry["until"]:
        # Expired, clean up
        recent.pop(uid, None)
        return None
    
    return entry["partner"]

def _inline_end_kb(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ End Chat", callback_data=f"fre:leave:{match_id}")]
    ])

# ------------- public API (call from fantasy_match when both ready) -------------
async def start_fantasy_chat(context: ContextTypes.DEFAULT_TYPE, match_id: int, boy_id: int, girl_id: int, duration_minutes: int = 15, vibe: str = "romantic"):
    """Create an anonymous DM relay between boy_id and girl_id for duration."""
    ends_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
    rel  = _relays(context); jobs = _jobs(context)

    # map both sides
    rel[boy_id]  = {"peer": girl_id, "match_id": match_id, "ends": ends_at}
    rel[girl_id] = {"peer": boy_id,  "match_id": match_id, "ends": ends_at}

    # greet both
    try:
        safety_message = (
            "🔥 **FANTASY CHAT STARTED!** 🔥\n\n"
            "Your anonymous fantasy chat partner is here!\n"
            f"⏰ {duration_minutes} minutes to connect and explore!\n"
            "💬 All messages are completely anonymous\n"
            "🔥 Be yourself and enjoy the conversation!\n\n"
            "**🛡️ Safety Commands (Available Anytime):**\n"
            "• `/end_fantasy` - Exit chat voluntarily\n"
            "• `/report` - Report inappropriate behavior\n\n"
            "Start chatting now! 💕"
        )
        # Record active session for persistence
        sid = relay_open(boy_id, girl_id)
        
        await context.bot.send_message(
            boy_id, 
            safety_message,
            reply_markup=_inline_end_kb(match_id), parse_mode="Markdown"
        )
        await context.bot.send_message(
            girl_id, 
            safety_message,
            reply_markup=_inline_end_kb(match_id), parse_mode="Markdown"
        )
        # Auto-prompts disabled - users can chat naturally without prompts
    except Exception as e:
        log.error(f"[relay] greet fail: {e}")

    # Auto-prompts disabled for natural conversation flow

    # schedule end
    jq = getattr(context, "job_queue", None)
    if jq:
        jobs[match_id] = jq.run_once(_end_chat_job, when=duration_minutes * 60,
                                     data={"match_id": match_id, "u1": boy_id, "u2": girl_id})

async def _end_chat_job(context: ContextTypes.DEFAULT_TYPE):
    job = getattr(context, "job", None)
    if not job or not getattr(job, "data", None):
        log.debug("[fantasy_relay] _end_chat_job: missing job or job data, skipping")
        return
    data = getattr(job, "data", {})
    if not isinstance(data, dict):
        log.debug("[fantasy_relay] _end_chat_job: invalid job data type, skipping")
        return
    mid, u1, u2 = data.get("match_id"), data.get("u1"), data.get("u2")
    if mid and u1 and u2:
        await end_fantasy_chat(context, match_id=mid, user_ids=[u1, u2], reason="⏳ Chat time over. See you tomorrow!")

async def end_fantasy_chat(context: ContextTypes.DEFAULT_TYPE, match_id: int, user_ids: list[int], reason: str = "Chat ended."):
    """End relay explicitly (time over or leave)."""
    # Stop prompt injector for this session
    from . import fantasy_prompts
    fantasy_prompts.stop_prompts_for(context, match_id)
    
    # CRITICAL FIX: Clear database match state so users can submit fantasies again
    try:
        import registration as reg
        with reg._conn() as con, con.cursor() as cur:
            # Mark the match as completed in database to clear the 2-hour period
            cur.execute("UPDATE fantasy_matches SET status = 'ended' WHERE id = %s", (match_id,))
            con.commit()
        log.info(f"[relay] Match {match_id} marked as ended in database")
    except Exception as e:
        log.error(f"[relay] Failed to mark match {match_id} as ended: {e}")
    
    rel = _relays(context); jobs = _jobs(context)
    recent = _recent_partners(context)
    
    # Store recent partners for post-chat reporting (15-minute window)
    report_until = datetime.utcnow() + timedelta(minutes=15)
    
    # End relay persistence
    if len(user_ids or []) == 2:
        relay_end(user_ids[0], user_ids[1])
    
    for uid in user_ids or []:
        try:
            if uid in rel:
                peer_info = rel.get(uid)
                if peer_info and peer_info.get("peer"):
                    # Store partner for 15-minute post-chat reporting
                    recent[uid] = {"partner": peer_info["peer"], "until": report_until}
                
                rel.pop(uid, None)
                await context.bot.send_message(uid, reason)
        except Exception as e:
            log.warning(f"[relay] end notify fail for {uid}: {e}")
    
    # clear peer entries as well
    # Ensure both sides removed (in case only one side passed)
    for uid, info in list(rel.items()):
        if info.get("match_id") == match_id:
            peer_id = info.get("peer")
            if peer_id and uid not in recent:
                # Store partner for post-chat reporting if not already stored
                recent[uid] = {"partner": peer_id, "until": report_until}
            rel.pop(uid, None)
    
    # cancel job if present
    try:
        j = jobs.pop(match_id, None)
        if j: j.schedule_removal()
    except Exception:
        pass

# ------------- message relay (high priority) -------------
async def on_relay_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    uid = effective_uid(update)
    if not msg or uid is None:
        return
    text = getattr(msg, 'text', None) or getattr(msg, 'caption', None) or ""

    # CRITICAL: Check if user is in text framework state (poll creation, etc.)
    # If so, don't relay - let the appropriate handler process it
    from handlers.text_framework import FEATURE_KEY
    if context.user_data and context.user_data.get(FEATURE_KEY):
        return  # User is in text framework flow, don't intercept

    if not _in_relay(context, uid):
        return  # not in active anonymous session

    info = _relays(context).get(uid, {})
    peer = info.get("peer")
    ends = info.get("ends")
    match_id = info.get("match_id")

    # check expiry
    if ends and datetime.utcnow() >= ends:
        await end_fantasy_chat(context, match_id=match_id, user_ids=[uid, peer], reason="⏳ Chat expired.")
        return

    # Check if user has premium for media sharing
    try:
        import registration as reg
        user_is_premium = reg.has_active_premium(uid)
        peer_is_premium = reg.has_active_premium(peer)
    except Exception:
        user_is_premium = False
        peer_is_premium = False

    # Handle different message types - CHECK MEDIA FIRST to prevent caption-only sending
    if getattr(msg, 'photo', None):
        # Photo sharing - premium only (sender needs premium)
        if user_is_premium:
            try:
                photo = msg.photo[-1] if msg.photo else None  # Get highest resolution
                if photo and hasattr(photo, 'file_id'):
                    caption = getattr(msg, 'caption', None) or ""
                    await context.bot.send_photo(peer, photo.file_id, caption=caption)
                    log.info(f"[relay] Photo shared from premium user {uid} -> {peer}")
            except Exception as e:
                log.error(f"[relay] photo forward fail: {e}")
        else:
            # Non-premium user trying to send photo
            upgrade_msg = "📸 **Photo sharing is premium only!**\n\n💎 *Upgrade to Premium* to share photos, voice messages, and more with your fantasy match.\n\n🔥 *Make your conversation more intimate and real!*"
            upgrade_kb = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")]])
            await context.bot.send_message(uid, upgrade_msg, reply_markup=upgrade_kb, parse_mode="Markdown")
            
    elif getattr(msg, 'voice', None):
        # Voice message sharing - premium only (sender needs premium)
        if user_is_premium:
            try:
                voice = getattr(msg, 'voice', None)
                if voice and hasattr(voice, 'file_id'):
                    await context.bot.send_voice(peer, voice.file_id, caption=getattr(msg, 'caption', None))
                    log.info(f"[relay] Voice message shared from premium user {uid} -> {peer}")
            except Exception as e:
                log.error(f"[relay] voice forward fail: {e}")
        else:
            upgrade_msg = "🎙️ **Voice messages are premium only!**\n\n💎 *Upgrade to Premium* to share voice messages and create deeper connections.\n\n🔥 *Let them hear your voice!*"
            upgrade_kb = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")]])
            await context.bot.send_message(uid, upgrade_msg, reply_markup=upgrade_kb, parse_mode="Markdown")
            
    elif getattr(msg, 'video', None) or getattr(msg, 'video_note', None):
        # Video sharing - premium only (sender needs premium)
        if user_is_premium:
            try:
                video = getattr(msg, 'video', None)
                video_note = getattr(msg, 'video_note', None)
                if video and hasattr(video, 'file_id'):
                    await context.bot.send_video(peer, video.file_id, caption=getattr(msg, 'caption', None))
                elif video_note and hasattr(video_note, 'file_id'):
                    await context.bot.send_video_note(peer, video_note.file_id)
                log.info(f"[relay] Video shared from premium user {uid} -> {peer}")
            except Exception as e:
                log.error(f"[relay] video forward fail: {e}")
        else:
            upgrade_msg = "🎥 **Video sharing is premium only!**\n\n💎 *Upgrade to Premium* to share videos and make your fantasy chat more exciting!\n\n🔥 *Show, don't just tell!*"
            upgrade_kb = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")]])
            await context.bot.send_message(uid, upgrade_msg, reply_markup=upgrade_kb, parse_mode="Markdown")
            
    elif getattr(msg, 'document', None):
        # Document sharing - premium only (sender needs premium)
        if user_is_premium:
            try:
                document = getattr(msg, 'document', None)
                if document and hasattr(document, 'file_id'):
                    await context.bot.send_document(peer, document.file_id, caption=getattr(msg, 'caption', None))
                    log.info(f"[relay] Document shared from premium user {uid} -> {peer}")
            except Exception as e:
                log.error(f"[relay] document forward fail: {e}")
        else:
            upgrade_msg = "📄 **File sharing is premium only!**\n\n💎 *Upgrade to Premium* to share documents and files with your match!\n\n⚡ *Premium makes everything possible!*"
            upgrade_kb = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")]])
            await context.bot.send_message(uid, upgrade_msg, reply_markup=upgrade_kb, parse_mode="Markdown")
            
    elif text and not text.startswith("/"):
        # Text-only messages (always relay, no premium required) 
        # Commands are handled by separate CommandHandlers, not here
        try:
            await context.bot.send_message(peer, text)
        except Exception as e:
            log.error(f"[relay] text forward fail: {e}")

# ------------- safety commands -------------
async def cmd_end_fantasy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /end_fantasy command - voluntary exit from fantasy chat"""
    uid = effective_uid(update)
    if uid is None:
        return await reply_any(update, context, "Could not identify user.")
    
    if not _in_relay(context, uid):
        await reply_any(update, context, "ℹ️ You're not in a fantasy chat.")
        return
    
    info = _relays(context).get(uid, {})
    match_id = info.get("match_id")
    peer = info.get("peer")
    
    if match_id and peer:
        await end_fantasy_chat(context, match_id=match_id, user_ids=[uid, peer], reason="🚪 Fantasy chat ended voluntarily.")
        await reply_any(update, context, "✅ You've safely exited the fantasy chat.")

async def cmd_report_fantasy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command for fantasy chats - works during active chat or 15 minutes after"""
    uid = effective_uid(update)
    if uid is None:
        return await reply_any(update, context, "Could not identify user.")
    
    # Check if user is in active fantasy chat
    partner = None
    match_id = None
    
    if _in_relay(context, uid):
        # Active fantasy chat
        info = _relays(context).get(uid, {})
        partner = info.get("peer")
        match_id = info.get("match_id")
    else:
        # Check for recent partner (within 15 minutes)
        partner = _get_recent_partner(context, uid)
    
    if not partner:
        await reply_any(update, context,
            "ℹ️ You can report during an active fantasy chat or within 15 minutes after it ends.\n\n"
            "💡 *Tip: Use /report immediately during or right after a fantasy chat.*"
        )
        return
    
    # Use the text framework to claim input state for 2 minutes (same as normal reports)  
    from handlers.text_framework import set_state
    set_state(context, "fantasy_report", "text", ttl_minutes=2)
    
    # Set up report state with deadline
    deadline = datetime.utcnow() + timedelta(minutes=2)
    user_data = getattr(context, "user_data", {})
    if user_data is not None:
        user_data["fantasy_report"] = {
            "partner": partner, 
            "in_secret": True,  # Fantasy chats are always anonymous/secret
            "awaiting": True,
            "match_id": match_id,
            "deadline": deadline
        }
    
    await reply_any(update, context,
        "🛡️ **Fantasy Chat Report**\n\n"
        "Please type your reason and (optional) attach ONE screenshot/photo.\n\n"
        "📝 Send within 2 minutes or type /cancel to abort.\n"
        "🔒 All reports are completely confidential."
    )

async def on_fantasy_report_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle fantasy report input (text/media) - similar to normal chat reports"""
    user_data = getattr(context, "user_data", {})
    if not user_data:
        return
    r = user_data.get("fantasy_report")
    if not r or not r.get("awaiting"):
        return  # Not in fantasy report mode
    
    # Check deadline (2-minute timeout)
    deadline = r.get("deadline")
    if deadline and datetime.utcnow() >= deadline:
        # Expired - clean up and inform user
        if user_data:
            user_data.pop("fantasy_report", None)
        from handlers.text_framework import clear_state
        clear_state(context)
        
        await reply_any(update, context, "⏰ Report timeout - please use /report again.")
        return
    
    uid = effective_uid(update)
    if uid is None:
        return
    partner = r["partner"]
    in_secret = r["in_secret"]
    
    # Validate and sanitize report text (same as normal reports)
    message = getattr(update, 'message', None)
    raw_text = ""
    if message:
        raw_text = getattr(message, 'caption', None) or getattr(message, 'text', None) or ""
    
    # Import the validation function from chat.py
    from chat import validate_and_sanitize_input
    is_valid, error_msg, text = validate_and_sanitize_input(raw_text, 'comment')
    if not is_valid:
        await reply_any(update, context, f"❌ {error_msg}")
        return
    
    media_file_id, media_type = None, None
    
    # Handle media attachments (same as normal reports)
    if message and getattr(message, 'photo', None):
        photo = message.photo[-1] if message.photo else None
        if photo and hasattr(photo, 'file_id'):
            media_file_id = photo.file_id
            media_type = "photo"
    elif message and getattr(message, 'document', None):
        document = getattr(message, 'document', None)
        if document and hasattr(document, 'file_id'):
            media_file_id = document.file_id
            media_type = "document"
    
    # Save to database (same table as normal reports)
    try:
        import registration as reg
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_reports (reporter_tg_id, reported_tg_id, in_secret, text, media_file_id, media_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (uid, partner, in_secret, text, media_file_id, media_type))
            row = cur.fetchone()
            con.commit()
        report_id, created_at = row[0], row[1]
        log.info(f"[fantasy_relay] Fantasy chat report #{report_id} saved from {uid} against {partner}")
    except Exception as e:
        if user_data:
            user_data["fantasy_report"] = None
        await reply_any(update, context, f"❗ Could not save report: {e}")
        return
    
    # Clean up report state
    if user_data:
        user_data.pop("fantasy_report", None)
    from handlers.text_framework import clear_state
    clear_state(context)
    
    # Acknowledge to reporter
    await reply_any(update, context, "✅ **Report Submitted**\n\nThanks for helping keep our fantasy community safe. Your report has been sent to our moderation team.")
    
    # Notify admins (same as normal reports)
    from chat import safe_display_name, ADMIN_IDS
    from_name = safe_display_name(uid)
    to_name = safe_display_name(partner)
    
    summary = (
        f"🔮 **Fantasy Chat Report** #{report_id}\n"
        f"From: {uid} ({from_name})\n"
        f"Against: {partner} ({to_name})\n"
        f"Anonymous: Yes\n"
        f"Text: {text[:400] or '—'}"
    )
    
    # Import admin notification code
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, summary)
            if media_file_id and media_type:
                if media_type == "photo":
                    await context.bot.send_photo(admin_id, media_file_id, caption="📸 Report attachment")
                elif media_type == "document":
                    await context.bot.send_document(admin_id, media_file_id, caption="📄 Report attachment")
        except Exception as e:
            log.warning(f"[fantasy_relay] Failed to notify admin {admin_id} about fantasy report: {e}")
    
    # CRITICAL: Stop handler chain to prevent report text from being relayed to reported person  
    from telegram.ext import ApplicationHandlerStop
    raise ApplicationHandlerStop

# ------------- leave via button -------------
async def on_leave_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = getattr(update, "callback_query", None)
    if not q or not q.from_user or not q.data:
        return await reply_any(update, context, "This action is no longer valid.")
    try:
        await q.answer()
    except Exception:
        pass  # Safe ignore if answer fails
    uid = effective_uid(update)
    if uid is None:
        return await reply_any(update, context, "Could not identify user.")
    try:
        mid = int(q.data.split(":")[2])
    except Exception:
        return

    # find both users belonging to this match
    rel = _relays(context)
    peers = []
    for u, info in list(rel.items()):
        if info.get("match_id") == mid:
            peers.append(u)
    await end_fantasy_chat(context, match_id=mid, user_ids=peers, reason="🚪 Chat ended by user.")

# ------------- register -------------
def register(app):
    # CRITICAL: Safety command handlers - highest priority for user safety
    app.add_handler(CommandHandler("end_fantasy", cmd_end_fantasy), group=-20)
    app.add_handler(CommandHandler("report", cmd_report_fantasy), group=-20)
    
    # Fantasy report input handler - very high priority to catch report inputs
    app.add_handler(
        MessageHandler(
            ~filters.COMMAND & (
                filters.TEXT | filters.PHOTO | filters.Document.ALL
            ),
            on_fantasy_report_input
        ),
        group=-18  # Higher than relay (-15) to catch report inputs first
    )
    
    # High priority so chat relay never fights with other text handlers
    # Handle text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_relay_message), group=-15)
    # Handle media messages (photos, voice, video, documents)
    app.add_handler(MessageHandler(filters.PHOTO, on_relay_message), group=-15)
    app.add_handler(MessageHandler(filters.VOICE, on_relay_message), group=-15)
    app.add_handler(MessageHandler(filters.VIDEO, on_relay_message), group=-15)
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, on_relay_message), group=-15)
    app.add_handler(MessageHandler(filters.Document.ALL, on_relay_message), group=-15)
    # Handle leave button
    app.add_handler(CallbackQueryHandler(on_leave_pressed, pattern=r"^fre:leave:\d+$"), group=-15)
    log.info("[fantasy_relay] Handlers registered successfully")