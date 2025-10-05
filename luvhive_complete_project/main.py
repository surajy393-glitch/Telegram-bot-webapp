# main.py
import os
import logging
import asyncio
import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.error import TelegramError, TimedOut, RetryAfter, NetworkError, Forbidden
import re  # Added re import for regex escaping

# Import MS Dhoni Performance System 🏏
from utils.performance_optimizer import dhoni_optimizer, apply_ms_dhoni_mode, get_performance_optimizer
from utils.connection_optimizer import connection_manager, force_connection_cleanup

# Setup centralized logging first
from utils.logging_setup import setup_logging
setup_logging()

from menu import (
    main_menu_kb,
    BTN_FIND_PARTNER,
    BTN_MATCH_GIRLS,
    BTN_MATCH_BOYS,
    BTN_MY_PROFILE,
    BTN_SETTINGS,
    BTN_PREMIUM,
    BTN_FRIENDS,
    BTN_PUBLIC_FEED,
    BTN_FUN_GAMES
)
import registration as reg

# --- Debug commands (module level) ---
async def cmd_debug_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lo, hi = reg.get_age_pref(uid)
    prem = reg.has_active_premium(uid)
    fwd = reg.get_allow_forward(uid)
    await update.message.reply_text(
        f"DEBUG: uid={uid}\nPremium={prem}\nmin_age_pref={lo}\nmax_age_pref={hi}\nallow_forward={fwd}"
    )

async def cmd_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug helper: Show who owns current text/media input"""
    if update.effective_user.id not in [1437934486, 647778438]:  # Admin check
        return await update.message.reply_text("❌ Admin only command!")
    
    from handlers.text_framework import FEATURE_KEY, MODE_KEY
    af = context.user_data.get(FEATURE_KEY)
    am = context.user_data.get(MODE_KEY)
    
    status = f"🔍 TEXT/MEDIA OWNERSHIP STATUS:\n\n"
    status += f"📝 Owner: {af or 'none'}\n"
    status += f"🎯 Mode: {am or 'none'}\n\n"
    
    if af:
        status += f"🛡️ Input is OWNED by '{af}' feature\n"
        status += f"⚡ All legacy handlers will be BLOCKED by firewall\n"
        status += f"🎯 Only '{af}' handlers can process text/media"
    else:
        status += f"🆓 Input is AVAILABLE\n"
        status += f"✅ Legacy handlers can process text/media\n"
        status += f"🔄 Next: First handler to claim will own input"
    
    await update.message.reply_text(status)

# === MS DHONI PERFORMANCE COMMANDS ===
async def cmd_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current performance status (MS Dhoni style)"""
    if update.effective_user.id not in [1437934486, 647778438]:  # Admin check
        return await update.message.reply_text("❌ Admin only command!")

    optimizer = get_performance_optimizer()
    report = optimizer.get_performance_report()
    await update.message.reply_text(report)

async def cmd_cool_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate MS Dhoni Cool Mode immediately"""
    if update.effective_user.id not in [1437934486, 647778438]:  # Admin check
        return await update.message.reply_text("❌ Admin only command!")

    report = apply_ms_dhoni_mode()
    await update.message.reply_text(f"🏏 MS DHONI COOL MODE ACTIVATED!\n\n{report}")

async def cmd_optimize_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force database connection optimization"""
    if update.effective_user.id not in [1437934486, 647778438]:  # Admin check
        return await update.message.reply_text("❌ Admin only command!")

    force_connection_cleanup()
    await update.message.reply_text("🧹 Database connections optimized! Idle connections cleared.")

async def cmd_system_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system resource usage"""
    if update.effective_user.id not in [1437934486, 647778438]:  # Admin check
        return await update.message.reply_text("❌ Admin only command!")

    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        info = f"""🖥️ SYSTEM RESOURCE STATUS

🔥 CPU Usage: {cpu_percent:.1f}%
💾 Memory: {memory.percent:.1f}% used
📊 Memory: {memory.used / (1024**3):.1f}GB / {memory.total / (1024**3):.1f}GB

🏏 MS Dhoni Status: {"ACTIVE" if dhoni_optimizer.cool_mode_active else "STANDBY"}
⚡ Current Mode: {"COOL MODE" if dhoni_optimizer.cool_mode_active else "NORMAL"}"""

        await update.message.reply_text(info)
    except Exception as e:
        await update.message.reply_text(f"❌ Could not get system info: {e}")

async def cmd_which_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            db, user = cur.fetchone()
        await update.message.reply_text(f"Connected DB: {db}\nUser: {user}")
    except Exception as e:
        await update.message.reply_text(f"DB check failed: {e}")


import chat
import profile as prof

# Import bulletproof protection systems
from utils.monitoring import metrics
from utils.db_integrity import apply_missing_constraints
from utils.maintenance import maintenance_system
from utils.privacy_compliance import privacy_manager
from admin_commands import bulletproof_handlers
from profile_metrics import ensure_metric_columns
from handlers.settings_handlers import register as register_settings_handlers
from handlers.profile_handlers import register as register_profile_handlers
from handlers.premium_handlers import register as register_premium_handlers
from handlers.admin_handlers import register as register_admin_handlers
from handlers.left_menu import register as register_left_menu
from handlers.left_menu_handlers import register as register_left_menu_handlers
from handlers.chat_handlers import register as register_chat_handlers
from handlers import posts_handlers

# Import QA handlers
from handlers import qa_handlers

# Import poll handlers
from handlers import poll_handlers

# Import sensual stories handlers
from handlers import sensual_stories

# Import text framework handlers
from handlers import verification, text_firewall

# Import new Fun & Games feature handlers
from handlers import funhub, notifications
from handlers import confession_roulette
from handlers import naughty_wyr
# dare_60s consolidated into advanced_dare
# Removed after_dark handlers - feature replaced with story building system
from handlers import fantasy_match
# Text Framework imports
from handlers import fantasy_chat, vault_text, text_router, fantasy_relay, fantasy_prompts, admin_fantasy_toggle
from handlers import blur_vault
from handlers import text_firewall, verification

import handlers.menu_handlers # Added import for menu_handlers

# Import friends handlers if exists
try:
    from handlers import friends_handlers
except ImportError:
    friends_handlers = None

# ==== Confession test (2 rounds in ~6 min) + auto-restore ====
def clear_jobs(app):
    for j in app.job_queue.jobs():
        j.schedule_removal()
    print("🧹 Cleared all scheduled jobs")



async def _restore_daily_jobs(context):
    app = context.application
    clear_jobs(app)

    # Use the same unified scheduler function from main()
    def register_daily_jobs_restore(app):
        if app.job_queue is None:
            return
        IST = pytz.timezone("Asia/Kolkata")

        # New alternative day scheduling system
        app.job_queue.run_daily(notifications.job_confession_open_7pm,  time=datetime.time(19, 0, tzinfo=IST))
        app.job_queue.run_daily(notifications.job_confession_delivery_730pm, time=datetime.time(19, 30, tzinfo=IST))
        app.job_queue.run_daily(notifications.job_wyr_push, time=datetime.time(20, 15, tzinfo=IST))
        # app.job_queue.run_daily(notifications.job_vault_push,  time=datetime.time(21, 45, tzinfo=IST))  # PREMIUM
        # app.job_queue.run_daily(notifications.job_fantasy_push,time=datetime.time(22, 15, tzinfo=IST))  # PREMIUM
        app.job_queue.run_daily(notifications.job_dare_drop,        time=datetime.time(23, 0,  tzinfo=IST))
        # app.job_queue.run_daily(notifications.job_afterdark_teaser, time=datetime.time(23, 55, tzinfo=IST))  # PREMIUM
        # app.job_queue.run_daily(notifications.job_afterdark_open,   time=datetime.time(0, 0, tzinfo=IST))   # PREMIUM

    register_daily_jobs_restore(app)
    try:
        await context.bot.send_message(context.job.chat_id, "🔁 Back to daily schedule (IST).")
    except Exception:
        pass
    print("🔁 Restored to daily IST schedule")

def register_jobs_confession_test_2x(app, notify_chat_id=None):
    """
    Single test round:
      t+2:00 reminder, t+3:00 delivery,
      t+5:00 reminder, t+6:00 delivery,
      t+6:05 auto-restore daily schedule.
    """
    app.job_queue.run_once(notifications.job_confession_open_7pm, when=2*60)  # Use enhanced diary prompts
    app.job_queue.run_once(notifications.job_confession_delivery_730pm, when=3*60)
    app.job_queue.run_once(notifications.job_wyr_push,            when=9999999)  # disabled in this test
    app.job_queue.run_once(notifications.job_afterdark_teaser,    when=9999999)  # disabled in this test
    app.job_queue.run_once(notifications.job_afterdark_open,      when=9999999)  # disabled in this test
    app.job_queue.run_once(notifications.job_confession_open_7pm, when=5*60)  # Use enhanced diary prompts
    app.job_queue.run_once(notifications.job_confession_delivery, when=6*60)
    # auto-restore after 6m05s
    app.job_queue.run_once(_restore_daily_jobs, when=6*60+5, chat_id=notify_chat_id)
    print("🚀 Confession-only test scheduled: 2m→rem1, 3m→del1, 5m→rem2, 6m→del2, 6m05s→restore")

async def cmd_test_confession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to test confession flow."""
    from admin import ADMIN_IDS
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admins only.")
        return

    clear_jobs(context.application)
    register_jobs_confession_test_2x(context.application, notify_chat_id=update.effective_chat.id)
    await update.message.reply_text("🧪 Confession test started! Check logs for schedule.")

async def cmd_restore_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to restore daily schedule."""
    from admin import ADMIN_IDS
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admins only.")
        return

    clear_jobs(context.application)
    register_daily_jobs_ist(context.application)
    await update.message.reply_text("🔁 Daily schedule restored.")

async def cmd_clear_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to clear all scheduled jobs."""
    from admin import ADMIN_IDS
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admins only.")
        return

    clear_jobs(context.application)
    await update.message.reply_text("🧹 All scheduled jobs cleared.")

log = logging.getLogger("luvbot")

BOT_TOKEN = os.environ["BOT_TOKEN"]

# Safe send wrapper for network reliability
async def safe_send(bot, chat_id, text, **kwargs):
    """Send message with retry logic for network issues"""
    for attempt in range(3):
        try:
            return await bot.send_message(chat_id, text, **kwargs)
        except RetryAfter as e:
            wait_time = int(getattr(e, "retry_after", 2)) + 1
            log.info(f"Rate limited, waiting {wait_time}s...")
            await asyncio.sleep(wait_time)
        except (TimedOut, NetworkError) as e:
            wait_time = 2 * (attempt + 1)
            log.warning(f"Network timeout (attempt {attempt+1}/3), retrying in {wait_time}s: {e}")
            await asyncio.sleep(wait_time)
        except Forbidden:
            log.info(f"User {chat_id} blocked the bot")
            return None
        except Exception as e:
            log.error(f"[safe_send] Unexpected error: {e}")
            return None
    log.error(f"[safe_send] Failed to send after 3 attempts to {chat_id}")
    return None

# ---- Stories cleanup loop (if you enabled Stories) ----
async def _stories_cleanup(app):
    import registration as reg
    from utils.db_locks import advisory_lock, STORY_CLEANUP_LOCK

    while True:
        try:
            with reg._conn() as con:
                with advisory_lock(con, STORY_CLEANUP_LOCK) as acquired:
                    if acquired:
                        with con.cursor() as cur:
                            # delete expired stories (24h)
                            cur.execute("DELETE FROM stories WHERE expires_at <= NOW()")
                            deleted_count = cur.rowcount
                            con.commit()
                            if deleted_count > 0:
                                print(f"[stories cleanup] deleted {deleted_count} expired stories")
                    else:
                        print("[stories cleanup] skipped - another instance running")
        except Exception as e:
            print("[stories cleanup] warn:", e)
        await asyncio.sleep(600)   # every 10 minutes

# keep a reference to the background task
_stories_task = None

async def _on_startup(app: Application):
    """PTB post-init hook: schedule background tasks AFTER loop is running."""
    global _stories_task

    # Initialize bulletproof protection systems
    try:
        print("[startup] Initializing bulletproof protection systems...")

        # Initialize database integrity constraints
        apply_missing_constraints()

        # Initialize Midnight University Chronicles database schema
        from muc_schema import ensure_muc_tables
        ensure_muc_tables()

        # Initialize maintenance system
        maintenance_system.setup_automated_maintenance()

        # Execute initial privacy data cleanup
        privacy_manager.execute_pending_deletions()

        print("[startup] ✅ Bulletproof protection systems initialized")

    except Exception as e:
        print(f"[startup] ⚠️ Warning: Bulletproof system initialization failed: {e}")

    # schedule the cleanup; PTB loop is active now
    _stories_task = app.create_task(_stories_cleanup(app))
    print("[startup] stories cleanup task started")

async def _on_shutdown(app: Application):
    """PTB post-shutdown hook: cancel background tasks cleanly."""
    global _stories_task
    if _stories_task:
        _stories_task.cancel()
        try:
            await _stories_task
        except Exception:
            pass
        _stories_task = None
    print("[shutdown] stories cleanup task stopped")

# ---------- Ban gate helper ----------
async def _ban_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is banned and show message if so. Return True if banned."""
    uid = update.effective_user.id
    try:
        if reg.is_banned(uid):
            until, reason, _ = reg.get_ban_info(uid)
            msg = "🚫 You are banned."
            if until:
                try:
                    pretty = "lifetime" if until.year >= 9999 else until.strftime("%Y-%m-%d %H:%M UTC")
                    msg += f" Until: {pretty}"
                except Exception:
                    msg += f" Until: {until}"
            if reason:
                msg += f"\nReason: {reason}"
            try:
                await update.effective_message.reply_text(msg)
            except Exception:
                pass
            return True
    except Exception as e:
        # DB connection drop or other issues - soft-pass to prevent bot crash
        try:
            log.warning(f"ban check failed (ignored): {e}")
        except Exception:
            pass
        return False
    return False

# ---------- Referral helper ----------
def _parse_ref(text: str) -> int | None:
    try:
        parts = text.strip().split()
        if len(parts) >= 2 and parts[1].startswith("ref_"):
            return int(parts[1][4:])
    except Exception:
        pass
    return None

# ---------- /start ----------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _ban_gate(update, context):
        return

    uid = update.effective_user.id

    # Update last_seen for WYR eligibility tracking
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("UPDATE users SET last_seen=NOW() WHERE tg_user_id=%s", (uid,))
            con.commit()
    except Exception:
        pass

    # capture referral if present
    if update.message and update.message.text and update.message.text.startswith("/start"):
        inviter = _parse_ref(update.message.text)
        if inviter and inviter != uid:
            try:
                reg.add_referral(inviter, uid)
            except Exception:
                pass

    # If already chatting, do NOT show any menus
    if chat.in_chat(uid):
        await update.message.reply_text("You're in a chat. Use /next or /stop first.")
        return

    # Not registered? kick off registration
    try:
        if not reg.is_registered(uid):
            await reg.start_registration(update, context)
            return
    except Exception:
        # Soft-degrade: show the menu instead of crashing the update
        pass

    # already registered (or DB hiccup) → show main menu
    welcome_message = (
        "✨💕 Welcome back to LuvHive 💕✨\n\n"
        "🌹 Where hearts connect anonymously 🌹\n"
        "💫 Your romantic journey awaits... 💫\n\n"
        "🔮 What magical moment will you create today? 🔮"
    )
    await update.message.reply_text(
        welcome_message,
        reply_markup=main_menu_kb()
    )

# ---------- bottom-menu taps ----------
async def on_btn_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '⚡ Find a Partner' button."""
    if await _ban_gate(update, context):
        return
    uid = update.effective_user.id
    if not reg.is_registered(uid):
        await update.message.reply_text("ℹ️ Please complete your profile first: open /settings and set gender, age and interests.")
        return
    reg.set_search_pref(uid, "any")   # reset to random
    await chat.start_search(update, context, mode="random")

async def on_btn_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '👤 My Profile' button."""
    if await _ban_gate(update, context):
        return
    from profile import profile_text, profile_keyboard
    uid = update.effective_user.id
    uname = update.effective_user.username
    await update.message.reply_text(
        profile_text(uid, uname),
        reply_markup=profile_keyboard(),
        parse_mode="HTML"
    )

async def on_btn_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '⚙️ Settings' button."""
    if await _ban_gate(update, context):
        return
    from settings import settings_text, settings_keyboard
    uid = update.effective_user.id
    profile = reg.get_profile(uid)
    context.user_data["interests"] = profile.get("interests", set())
    context.user_data["is_verified"] = bool(profile.get("is_verified", False))
    context.user_data.setdefault("show_media", False)
    context.user_data.setdefault("age_pref", (18, 99))
    context.user_data.setdefault("allow_forward", False)
    # CRITICAL: let settings.py read from DB
    context.user_data["user_id"] = uid

    await update.message.reply_text(
        settings_text(context.user_data),
        reply_markup=settings_keyboard(context.user_data),
        parse_mode="Markdown",
    )

async def on_btn_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle '💎 Premium' button."""
    if await _ban_gate(update, context):
        return
    from premium import premium_text, premium_kb
    await update.message.reply_text(
        premium_text(),
        reply_markup=premium_kb(),
        parse_mode="Markdown"
    )

async def on_btn_match_girls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _ban_gate(update, context):
        return
    uid = update.effective_user.id
    if not reg.has_active_premium(uid):
        await update.message.reply_text("⚡⭐ To use this feature you must have a premium subscription.")
        return
    if not reg.is_registered(uid):
        await update.message.reply_text("ℹ️ Please complete your profile first: open /settings and set gender, age and interests.")
        return
    reg.set_search_pref(uid, "f")
    await chat.start_search(update, context, mode="girls")

async def on_btn_match_boys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _ban_gate(update, context):
        return
    uid = update.effective_user.id
    if not reg.has_active_premium(uid):
        await update.message.reply_text("⚡⭐ To use this feature you must have a premium subscription.")
        return
    if not reg.is_registered(uid):
        await update.message.reply_text("ℹ️ Please complete your profile first: open /settings and set gender, age and interests.")
        return
    reg.set_search_pref(uid, "m")
    await chat.start_search(update, context, mode="boys")

async def cmd_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    me = await context.bot.get_me()
    uid = update.effective_user.id
    link = f"https://t.me/{me.username}?start=ref_{uid}"
    await update.message.reply_text(
        "🎁 Invite friends & earn 50 coins for each friend who joins!\n"
        "Share this link:\n" + link,
        disable_web_page_preview=True
    )

async def on_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.error import TimedOut, NetworkError, RetryAfter, BadRequest

    err = context.error
    # harmless / expected cases:
    if isinstance(err, (TimedOut, NetworkError, RetryAfter)):
        # light log only
        log.info(f"Transient network issue: {err}")
        return
    # common spammy case from edits:
    if isinstance(err, BadRequest) and "message is not modified" in str(err).lower():
        return
    # otherwise keep full stack
    log.exception("Handler error", exc_info=err)

# ---------- Block/Unblock Handlers ----------
async def blk_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = update.callback_query.data
    from utils.cb import cb_match
    try:
        m = cb_match(data, r"^blk:add:(?P<uid>\d+)$")
        tid = int(m["uid"])
    except:
        return
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("INSERT INTO blocked_users(user_id,blocked_uid) VALUES (%s,%s) ON CONFLICT DO NOTHING",(uid,tid))
        con.commit()
    await update.callback_query.answer("Blocked.")
    return await prof.view_profile(update, context)

async def blk_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = update.callback_query.data
    from utils.cb import cb_match
    try:
        m = cb_match(data, r"^blk:del:(?P<uid>\d+)$")
        tid = int(m["uid"])
    except:
        return
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM blocked_users WHERE user_id=%s AND blocked_uid=%s",(uid,tid))
        con.commit()
    await update.callback_query.answer("Unblocked.")
    return await prof.view_profile(update, context)

# ---------- Block helper ----------
def _is_blocked(viewer: int, author: int) -> bool:
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT 1 FROM blocked_users WHERE user_id=%s AND blocked_uid=%s",(viewer,author))
        return cur.fetchone() is not None

def main():
    # Initialize all DB tables
    reg.init_db()
    reg.ensure_verification_columns()
    reg.ensure_reports_table()
    reg.ensure_ban_columns()
    reg.ensure_feature_columns()
    reg.ensure_questions_table()
    reg.ensure_friend_requests_table()
    reg.ensure_leaderboard_columns()
    reg.ensure_profile_upgrade_columns()
    reg.ensure_public_feed_columns()
    reg.ensure_social_tables()
    reg.ensure_secret_crush_table()
    reg.ensure_leaderboard_columns()
    reg.ensure_profile_upgrade_columns()
    reg.ensure_public_feed_columns()
    reg.ensure_blocked_users_table()
    reg.ensure_age_pref_columns()
    reg.ensure_forward_column()

    # Initialize feed posts tables
    try:
        from handlers.posts_handlers import ensure_feed_posts_table
        ensure_feed_posts_table()
    except Exception as e:
        log.warning(f"Feed posts table init failed: {e}")

    # Initialize story tables
    try:
        reg.ensure_story_tables()
    except Exception as e:
        log.warning(f"Story tables init failed: {e}")

    # Initialize confessions table
    try:
        reg.ensure_confessions_table()
    except Exception as e:
        log.warning(f"Confessions table init failed: {e}")

    # Initialize QA tables
    try:
        qa_handlers.ensure_qa_tables()
    except Exception as e:
        print("[startup] QA ensure warn:", e)

    # Initialize Poll tables
    try:
        poll_handlers.ensure_poll_tables()
    except Exception as e:
        print("[startup] Poll ensure warn:", e)

    chat.init_db()
    prof.init_profile_db()
    ensure_metric_columns()

    # >>> PATCH START: stronger network timeouts for Replit/slow networks
    from telegram.ext import JobQueue, PicklePersistence
    from telegram.request import HTTPXRequest
    
    # Enable persistence for relay state survival across restarts
    persistence = PicklePersistence(filepath="bot_state.pkl")
    
    # Stronger network timeouts for Replit/slow networks with retry logic
    request = HTTPXRequest(
        connect_timeout=45.0,   # Increased for slow Replit connections
        read_timeout=60.0,      # Long timeout for getUpdates
        write_timeout=45.0,
        pool_timeout=45.0,
        socket_options=None,    # Let system handle socket options
    )
    
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .job_queue(JobQueue())
        .persistence(persistence)        # ✅ Fix: Add persistence for relay state
        .concurrent_updates(True)
        .post_init(_on_startup)     # ✅ schedule inside loop
        .post_shutdown(_on_shutdown)
        .build()
    )
    # >>> PATCH END

    # Add error handler for cleaner logs
    app.add_error_handler(on_error)

    # Registration handlers MUST be first
    from handlers.registration_handlers import register as register_registration_handlers
    register_registration_handlers(app)

    # --- Register posts handlers FIRST for highest priority ---
    posts_handlers.register(app)

    # TEXT FRAMEWORK - Register text handlers with proper priority order
    # Priority: verification (-16) > fantasy_relay (-15) > afterdark_relay (-14) > fantasy_chat (-12) > vault_text (-11) > confession (-8) > qa (-6) > polls (-5) > stories (-4) > WYR (-3) > firewall (0) > text_router (9)
    verification.register(app)      # Group -16: High priority verification (prevents collision)
    fantasy_relay.register(app)     # Group -15: Anonymous chat relay (highest priority)
    fantasy_chat.register(app)      # Group -12: Fantasy text input
    vault_text.register(app)        # Group -11: Vault text input
    confession_roulette.register(app) # Group -8: Confession text input
    qa_handlers.register(app)         # Group -6: QA answer input
    
    # Create public polls handler import
    from handlers import public_polls
    public_polls.register(app)        # Group -5: Poll creation input
    
    sensual_stories.register(app)     # Group -4: Story submission input
    naughty_wyr.register(app)         # Group -3: WYR comments
    text_firewall.register(app)       # Group 0: Global ownership firewall
    text_router.register(app)         # Group 9: Fallback for unclaimed text

    # Register Poll handlers (existing)
    poll_handlers.register(app)

    # Register Fun & Games feature handlers
    funhub.register(app)
    # dare_60s consolidated into advanced_dare - no separate registration needed

    # Register Midnight University Chronicles handlers
    from handlers import midnight_university
    midnight_university.register(app)

    # Register advanced dare system
    from handlers import advanced_dare
    advanced_dare.register_advanced_dare_handlers(app)

    # After Dark feature removed - replaced with story building system
    
    # Ensure fantasy tables before registering handlers
    from handlers import fantasy_match
    fantasy_match.ensure_fantasy_tables()
    
    # Register ONLY the /fantasy command from fantasy_match (avoid conflicts)
    app.add_handler(CommandHandler("fantasy", fantasy_match.cmd_fantasy), group=-1)
    
    # Register Fantasy callback handlers for button interactions
    app.add_handler(CallbackQueryHandler(fantasy_match.handle_fantasy_callback, pattern=r"^fant:"), group=-1)
    
    # Register Fantasy Board system - NEW!
    from handlers.fantasy_integration import setup_fantasy_system
    setup_fantasy_system(app)
    
    blur_vault.register(app)
    
    # Register fantasy prompt mode admin command
    fantasy_prompts.register_prompt_mode_command(app)
    
    # Register fantasy prompt admin toggle panel
    admin_fantasy_toggle.register(app)

    # Register premium open handler for lock screens
    from handlers import premium_open
    premium_open.register(app)

    # /start must be early so it isn't eaten by generic handlers
    app.add_handler(CommandHandler("start", cmd_start), group=0)

    # Referral command
    app.add_handler(CommandHandler("ref", cmd_ref), group=0)

    # DB health check for admins
    from admin import cmd_dbhealth
    app.add_handler(CommandHandler("dbhealth", cmd_dbhealth), group=0)

    # Chat handlers (search/next/stop + rating/report + relay + spin/leaderboard)
    register_chat_handlers(app)        # hooks chat.register_handlers + /spin + /leaderboard

    # Add crush leaderboard command
    app.add_handler(CommandHandler("crushleaderboard", chat.cmd_crushleaderboard), group=0)

    # Add horoscope and fun fact commands
    app.add_handler(CommandHandler("horoscope", chat.cmd_horoscope), group=0)
    app.add_handler(CommandHandler("setbirthday", chat.cmd_setbirthday), group=0)
    app.add_handler(CommandHandler("funfact", chat.cmd_funfact), group=0)

    # Add badges command
    app.add_handler(CommandHandler("badges", chat.cmd_badges), group=0)

    # Add admin shadow ban commands
    app.add_handler(CommandHandler("shadowban", chat.cmd_shadowban), group=0)
    app.add_handler(CommandHandler("unshadowban", chat.cmd_unshadowban), group=0)

    # Settings handlers (interests, media, age, forwarding)
    register_settings_handlers(app)

    # Profile handlers (view profile, edit gender/age/language)
    register_profile_handlers(app)

    # Premium handlers (benefits page, payment plans, referrals)
    register_premium_handlers(app)

    # Admin handlers (admin panel, stats, user management)
    register_admin_handlers(app)
    
    # Mini App handlers (Instagram-style social feed)
    from handlers import miniapp_commands
    miniapp_commands.register_miniapp_handlers(app)

    # Register all daily jobs with final IST timings (ALT-DAY rotation handled inside jobs)
    def register_daily_jobs(app):
        if app.job_queue is None:
            print("⚠️ JobQueue not available - daily notifications disabled")
            return

        IST = pytz.timezone("Asia/Kolkata")

        # ✅ Confession Roulette → LOW HYPE, 7–8 pm window
        app.job_queue.run_daily(notifications.job_confession_open_7pm,  time=datetime.time(19, 0, tzinfo=IST))   # 7:00 pm
        app.job_queue.run_daily(notifications.job_confession_delivery_730pm, time=datetime.time(19, 30, tzinfo=IST)) # 7:30 pm

        # 🔥 Naughty WYR
        app.job_queue.run_daily(notifications.job_wyr_push, time=datetime.time(20, 15, tzinfo=IST))              # 8:15 pm

        # 🔮 Daily Horoscope (Morning Habit Builder)
        app.job_queue.run_daily(notifications.job_daily_horoscope_8am, time=datetime.time(8, 0, tzinfo=IST))     # 8:00 am

        # 🎲 Dare
        app.job_queue.run_daily(notifications.job_dare_drop, time=datetime.time(23, 0, tzinfo=IST))              # 11:00 pm

        print("✅ Daily jobs registered - FREE FEATURES ONLY (Horoscope 8:00am, Confession 7:00/7:30pm, WYR 8:15pm, Dare 11:00pm) - Premium features accessible via menu")

    register_daily_jobs(app)
    
    # Fantasy Match background jobs (matching every 3 minutes) - DISABLED
    # jq = getattr(app, "job_queue", None)
    # if jq:
    #     # 180 seconds = 3 minutes
    #     jq.run_repeating(fantasy_match.job_fantasy_match_pairs, interval=300, first=90)  # Every 5 minutes (reduced from 3 min)

    # MANUAL MENU BUTTON HANDLERS - Only for buttons NOT handled by register() functions
    # Apply the fix here: register early with strong regex
    def _btn(s):   # exact, but tolerant to stray spaces
        return filters.Regex(fr"^\s*{re.escape(s)}\s*$")

    # CRITICAL FIX: Menu buttons MUST have HIGHEST PRIORITY to work before text framework handlers
    app.add_handler(MessageHandler(_btn(BTN_FIND_PARTNER), on_btn_find), group=-25)
    app.add_handler(MessageHandler(_btn(BTN_PREMIUM), on_btn_premium), group=-25)
    app.add_handler(MessageHandler(_btn(BTN_MATCH_GIRLS), on_btn_match_girls), group=-25)
    app.add_handler(MessageHandler(_btn(BTN_MATCH_BOYS), on_btn_match_boys), group=-25)
    app.add_handler(MessageHandler(_btn(BTN_MY_PROFILE), on_btn_profile), group=-25)
    app.add_handler(MessageHandler(_btn(BTN_SETTINGS), on_btn_settings), group=-25)
    app.add_handler(MessageHandler(_btn(BTN_FRIENDS), handlers.menu_handlers.on_home_friends), group=-25)
    app.add_handler(MessageHandler(_btn(BTN_PUBLIC_FEED), posts_handlers.cmd_public), group=-25)
    # Fun & Games: already wired inside funhub.register(app)

    # Bulletproof protection commands
    for handler in bulletproof_handlers:
        app.add_handler(handler, group=0)

    # === TEXT FRAMEWORK CENTRAL HANDLERS (group -20) ===
    from handlers.text_framework import handle_text_cancel
    app.add_handler(CallbackQueryHandler(handle_text_cancel, pattern=r"^textfw:cancel$"), group=-20)
    
    # Block/Unblock callbacks
    app.add_handler(CallbackQueryHandler(blk_add, pattern="^blk:add:"), group=1)
    app.add_handler(CallbackQueryHandler(blk_del, pattern="^blk:del:"), group=1)
    # Fun & Games button - handled by funhub.register(app) at group=-10 (high priority)

    # Left menu handlers (/quit routing) - after handlers are registered
    register_left_menu_handlers(app)     # adds /game, /truth, /dare, etc., and left-menu refresh

    # Settings command (use the proper one from settings_handlers)
    from handlers.settings_handlers import show_settings
    app.add_handler(CommandHandler("settings", show_settings), group=0)

    # Admin WYR comment deletion command
    app.add_handler(CommandHandler("deletewyrcomment", naughty_wyr.cmd_delete_wyr_comment), group=0)

    # Health check commands for monitoring
    async def cmd_healthz(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Basic health check endpoint."""
        from health import healthz
        try:
            health_data = healthz()
            status = health_data["status"]
            emoji = "✅" if status == "healthy" else "❌"
            await update.message.reply_text(f"{emoji} Service: {status}")
        except Exception as e:
            await update.message.reply_text(f"❌ Health check failed: {e}")

    async def cmd_readyz(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Readiness check with dependency verification."""
        from health import readyz
        try:
            ready_data = readyz()
            status = ready_data["status"]
            emoji = "✅" if status == "ready" else "❌"
            checks = ready_data.get("checks", {})

            msg = f"{emoji} Status: {status}\n"
            for name, check in checks.items():
                check_emoji = "✅" if check["status"] == "healthy" else "❌"
                msg += f"{check_emoji} {name}: {check['status']}\n"

            await update.message.reply_text(msg)
        except Exception as e:
            await update.message.reply_text(f"❌ Readiness check failed: {e}")

    app.add_handler(CommandHandler("healthz", cmd_healthz), group=0)
    app.add_handler(CommandHandler("readyz", cmd_readyz), group=0)

    # Privacy and Data Management Commands
    async def cmd_cancel_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel_deletion command"""
        uid = update.effective_user.id
        result = privacy_manager.cancel_data_deletion(uid)

        if result["success"]:
            await update.message.reply_text(f"✅ {result['message']}")
        else:
            await update.message.reply_text(f"❌ {result['error']}")

    app.add_handler(CommandHandler("cancel_deletion", cmd_cancel_deletion), group=0)

    # Debug commands
    app.add_handler(CommandHandler("debug_age", cmd_debug_age), group=0)
    app.add_handler(CommandHandler("owner", cmd_owner), group=0)
    app.add_handler(CommandHandler("which_db", cmd_which_db), group=0)

    # MS Dhoni Performance Commands 🏏
    app.add_handler(CommandHandler("performance", cmd_performance), group=0)
    app.add_handler(CommandHandler("cool_mode", cmd_cool_mode), group=0)
    app.add_handler(CommandHandler("optimize_db", cmd_optimize_db), group=0)
    app.add_handler(CommandHandler("system_info", cmd_system_info), group=0)

    # ==================== TEST RUNNERS (one-shot) ====================
    def clear_jobs_all(app):
        for j in app.job_queue.jobs():
            j.schedule_removal()
        print("🧹 Cleared all scheduled jobs")

    def register_confession_daily_jobs_ist(app):
        IST = pytz.timezone("Asia/Kolkata")
        app.job_queue.run_daily(notifications.job_confession_open_7pm,  time=datetime.time(19, 0, tzinfo=IST))
        app.job_queue.run_daily(notifications.job_confession_delivery_730pm, time=datetime.time(19, 30, tzinfo=IST))
        print("✅ Confession daily jobs registered (IST)")

    async def _restore_daily_all(context):
        app = context.application
        clear_jobs_all(app)

        # Use unified scheduler for all jobs
        def register_daily_jobs_test_restore(app):
            if app.job_queue is None:
                return
            IST = pytz.timezone("Asia/Kolkata")
            # Updated to new alternative day scheduling system
            app.job_queue.run_daily(notifications.job_confession_open_7pm,  time=datetime.time(19, 0, tzinfo=IST))
            app.job_queue.run_daily(notifications.job_confession_delivery_730pm, time=datetime.time(19, 30, tzinfo=IST))
            app.job_queue.run_daily(notifications.job_wyr_push, time=datetime.time(20, 15, tzinfo=IST))
            # app.job_queue.run_daily(notifications.job_vault_push,  time=datetime.time(21, 45, tzinfo=IST))   # PREMIUM
            # app.job_queue.run_daily(notifications.job_fantasy_push,time=datetime.time(22, 15, tzinfo=IST))  # PREMIUM
            app.job_queue.run_daily(notifications.job_dare_drop,        time=datetime.time(23, 0,  tzinfo=IST))
            # app.job_queue.run_daily(notifications.job_afterdark_teaser, time=datetime.time(23, 55, tzinfo=IST)) # PREMIUM
            # app.job_queue.run_daily(notifications.job_afterdark_open,   time=datetime.time(0, 0, tzinfo=IST))  # PREMIUM

        register_daily_jobs_test_restore(app)
        try:
            await context.bot.send_message(context.job.chat_id, "🔁 Back to daily schedule (IST).")
        except Exception:
            pass
        print("🔁 Restored to daily IST schedule")

    # ------------------ /test_confession (already used) ------------------
    def register_test_confession_2x(app, notify_chat_id=None):
        app.job_queue.run_once(notifications.job_confession_open_7pm, when=2*60)  # Use enhanced diary prompts
        app.job_queue.run_once(notifications.job_confession_delivery_730pm, when=3*60)
        app.job_queue.run_once(notifications.job_confession_open_7pm, when=5*60)  # Use enhanced diary prompts
        app.job_queue.run_once(notifications.job_confession_delivery_730pm, when=6*60)
        app.job_queue.run_once(_restore_daily_all, when=6*60+5, chat_id=notify_chat_id)
        print("🚀 TEST: Confession (2 rounds / ~6min) scheduled")

    async def cmd_test_confession_new(update, context):
        clear_jobs_all(context.application)
        await update.message.reply_text("🧪 Confession test started! Check logs for schedule.")
        register_test_confession_2x(context.application, notify_chat_id=update.effective_user.id)

    # ------------------ /test_wyr (push only) ------------------
    def register_test_wyr(app, notify_chat_id=None):
        app.job_queue.run_once(notifications.job_wyr_push, when=2*60)      # push once
        app.job_queue.run_once(_restore_daily_all,         when=4*60, chat_id=notify_chat_id)
        print("🚀 TEST: WYR push scheduled (one-shot)")

    async def cmd_test_wyr(update, context):
        clear_jobs_all(context.application)
        await update.message.reply_text("🧪 WYR test started! You will get a spicy poll in ~2min.")
        register_test_wyr(context.application, notify_chat_id=update.effective_user.id)

    # ------------------ /test_dare (drop only) ------------------
    def register_test_dare(app, notify_chat_id=None):
        app.job_queue.run_once(notifications.job_dare_drop, when=2*60)     # drop once
        app.job_queue.run_once(_restore_daily_all,          when=4*60, chat_id=notify_chat_id)
        print("🚀 TEST: Dare drop scheduled (one-shot)")

    async def cmd_test_dare(update, context):
        clear_jobs_all(context.application)
        await update.message.reply_text("🧪 Dare test started! You will get a dare in ~2min.")
        register_test_dare(context.application, notify_chat_id=update.effective_user.id)

    # After Dark test commands removed - feature replaced with story building system

    # ------------------ /test_vault (preview broadcast once) ------------------
    def register_test_vault(app, notify_chat_id=None):
        try:
            app.job_queue.run_once(notifications.job_vault_teaser, when=2*60)
        except Exception:
            # Fallback: just restore after 2 min if job not present
            pass
        app.job_queue.run_once(_restore_daily_all, when=4*60, chat_id=notify_chat_id)
        print("🚀 TEST: Vault teaser scheduled (one-shot)")

    async def cmd_test_vault(update, context):
        clear_jobs_all(context.application)
        await update.message.reply_text("🧪 Vault test started! Teaser in ~2min.")
        register_test_vault(context.application, notify_chat_id=update.effective_user.id)

    # ------------------ /test_fantasy (premium setup ping once) ------------------
    def register_test_fantasy(app, notify_chat_id=None):
        try:
            app.job_queue.run_once(notifications.job_fantasy_ping, when=2*60)
        except Exception:
            pass
        app.job_queue.run_once(_restore_daily_all, when=4*60, chat_id=notify_chat_id)
        print("🚀 TEST: Fantasy ping scheduled (one-shot)")

    async def cmd_test_fantasy(update, context):
        clear_jobs_all(context.application)
        await update.message.reply_text("🧪 Fantasy test started! Premium tag-setup ping in ~2min.")
        register_test_fantasy(context.application, notify_chat_id=update.effective_user.id)

    # All test commands
    app.add_handler(CommandHandler("test_confession", cmd_test_confession_new), group=0)
    app.add_handler(CommandHandler("test_wyr",        cmd_test_wyr),        group=0)
    app.add_handler(CommandHandler("test_dare",       cmd_test_dare),       group=0)
    # After Dark test handler removed
    app.add_handler(CommandHandler("test_vault",      cmd_test_vault),      group=0)
    app.add_handler(CommandHandler("test_fantasy",    cmd_test_fantasy),    group=0)

    # === ADMIN CONFESSION APPROVAL SYSTEM ===
    from handlers.confession_roulette import register_admin_confession_handlers
    register_admin_confession_handlers(app)

    # Vault system commands (vault command already registered in blur_vault.register)
    from handlers.blur_vault import cmd_balance
    app.add_handler(CommandHandler("balance", cmd_balance), group=0)

    # Legacy commands
    app.add_handler(CommandHandler("restore_daily", cmd_restore_daily), group=0)
    app.add_handler(CommandHandler("clear_jobs", cmd_clear_jobs), group=0)

    # Generic text from users during registration, etc.  <-- put this LAST
    # so it doesn't swallow commands or menu buttons above.
    # Registration text handler removed - already registered in registration_handlers.py at group=5

    # Apply left menu configuration (SINGLE REGISTRATION)
    register_left_menu(app)              # sets default emoji list at startup

    # --- Register menu handlers REMOVED - handled by left_menu_handlers ---
    handlers.menu_handlers.register(app) # Re-enabled: Let menu_handlers handle Friends button

    # Register friends handlers
    if friends_handlers:
        friends_handlers.register(app)

    # --- MS Dhoni Performance System Setup 🏏 ---
    try:
        apply_ms_dhoni_mode()
        print("🏏 Initial MS Dhoni optimizations applied - Captain Cool activated!")

        # Start background monitoring
        import asyncio
        def start_monitoring():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(dhoni_optimizer.monitor_and_optimize())
            except Exception as e:
                print(f"⚠️ MS Dhoni monitoring error: {e}")

        import threading
        monitoring_thread = threading.Thread(target=start_monitoring, daemon=True)
        monitoring_thread.start()
        print("🏏 MS Dhoni background monitoring started")

    except Exception as e:
        print(f"⚠️ Could not apply initial optimizations: {e}")

    # --- Bot Instance Protection System ---
    # Prevent multiple bot instances from running simultaneously
    import sys
    
    # Global variable to hold the advisory lock connection
    global _bot_lock_connection
    _bot_lock_connection = None
    
    try:
        # Acquire database advisory lock to prevent concurrent bot instances
        with reg._conn() as con, con.cursor() as cur:
            
            # Try to acquire advisory lock 900001 (bot instance lock)
            cur.execute("SELECT pg_try_advisory_lock(900001)")
            lock_acquired = cur.fetchone()[0]
            
            if not lock_acquired:
                log.error("🚨 CRITICAL: Another bot instance is already running!")
                log.error("🚨 Cannot start multiple bot instances with the same token.")
                log.error("🚨 Please check for other running instances or wait for them to stop.")
                sys.exit(1)
            
            log.info("🔒 Bot instance lock acquired successfully")
            con.commit()
        
        # Note: Advisory locks are session-based, so they will be released when process ends
        # No need for explicit cleanup hook since the lock is held for process lifetime
        
    except Exception as e:
        log.error(f"🚨 Failed to acquire bot instance lock: {e}")
        log.error("🚨 This might indicate database connectivity issues or another instance running.")
        sys.exit(1)

    # Note: Webhook cleanup removed for simplicity - polling mode is ensured by drop_pending_updates=True in run_polling()
    log.info("✅ Bot instance protection system activated")

    # Start FastAPI server in background thread
    from threading import Thread
    from api_server import run_api
    Thread(target=run_api, daemon=True).start()
    print("🌐 API server started on /api ...")

    # --- run mode switch ---
    MODE = os.environ.get("RUN_MODE", "polling").lower()

    if MODE == "webhook":
        PORT = int(os.environ.get("PORT", "8443"))  # Replit sets PORT for you
        EXTERNAL_URL = os.environ["EXTERNAL_URL"].rstrip("/")  # https://<project>.<user>.repl.co
        WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "hook")
        SECRET_TOKEN = os.environ.get("SECRET_TOKEN")  # optional

        log.info("🚀 Bot starting in WEBHOOK mode")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH,
            webhook_url=f"{EXTERNAL_URL}/{WEBHOOK_PATH}",
            secret_token=SECRET_TOKEN,
            drop_pending_updates=True,
            allowed_updates=["message","edited_message","callback_query","pre_checkout_query"],
            stop_signals=None,
        )
    else:
        log.info("🚀 Bot starting in POLLING mode")

        # MS Dhoni system will handle optimizations during runtime
        try:
            app.run_polling(
                allowed_updates=["message","edited_message","callback_query","pre_checkout_query"],
                drop_pending_updates=True,
                stop_signals=None,
                close_loop=False  # Don't close asyncio loop on network errors
            )
        except Exception as e:
            log.error(f"Polling failed: {e}")
            # Let run_forever.sh restart the bot
            raise
    # --- end run mode switch ---

if __name__ == "__main__":
    main()