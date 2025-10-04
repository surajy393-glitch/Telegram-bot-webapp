# handlers/notifications.py
import datetime
import pytz
from telegram.ext import ContextTypes
from utils.display import safe_display_name

# 🔧 Your tester TG IDs (fallback when DB fails)
TESTERS = [8482725798, 647778438, 1437934486]

IST = pytz.timezone("Asia/Kolkata")

# ========= FREE FEATURES ONLY PROGRAM (5 Days Dare Schedule) =========
# Only FREE features get notifications: Confession, WYR, Dare (Mon Wed Fri Sat Sun)
# Premium features (vault, fantasy, afterdark) removed from notifications
# Dare Rest Days: Tuesday & Thursday (to avoid user fatigue)
WEEK_PROGRAM = {
    0: {  # Monday: Free features + DARE
        "confession": True,  "wyr": True,  "vault": False,
        "fantasy": False,    "dare": True, "afterdark": False,
    },
    1: {  # Tuesday: Free features only (NO DARE - Rest Day)
        "confession": True,  "wyr": True,  "vault": False,
        "fantasy": False,    "dare": False, "afterdark": False,
    },
    2: {  # Wednesday: Free features + DARE
        "confession": True,  "wyr": True,  "vault": False,
        "fantasy": False,    "dare": True, "afterdark": False,
    },
    3: {  # Thursday: Free features only (NO DARE - Rest Day)
        "confession": True,  "wyr": True,  "vault": False,
        "fantasy": False,    "dare": False, "afterdark": False,
    },
    4: {  # Friday: Free features + DARE
        "confession": True,  "wyr": True,  "vault": False,
        "fantasy": False,    "dare": True, "afterdark": False,
    },
    5: {  # Saturday: Free features + DARE
        "confession": True,  "wyr": True,  "vault": False,
        "fantasy": False,    "dare": True, "afterdark": False,
    },
    6: {  # Sunday: Free features + DARE
        "confession": True,  "wyr": True,  "vault": False,
        "fantasy": False,    "dare": True, "afterdark": False,
    },
}

def _today_cfg(now_ist: datetime.datetime | None = None) -> dict:
    if now_ist is None:
        now_ist = datetime.datetime.now(IST)
    return WEEK_PROGRAM[now_ist.weekday()]

# ---------- helpers ----------
async def _nudge_users() -> list[int]:
    """Users who should receive reminders (bulletproof with hybrid DB)."""
    try:
        from utils.hybrid_db import get_nudge_users_hybrid
        return get_nudge_users_hybrid()
    except Exception:
        # Fallback to testers if DB fails
        return TESTERS

# ===================== WYR (unchanged timing, gated by plan) =====================
async def job_wyr_push(context: ContextTypes.DEFAULT_TYPE):
    if not _today_cfg().get("wyr", False):
        return
    try:
        # Clean up old group chats first
        await _cleanup_old_wyr_groups()
        
        from handlers.naughty_wyr import push_naughty_wyr_question
        await push_naughty_wyr_question(context)
        print("[wyr-push] Naughty WYR pushed (day-enabled) at 8:15pm with cleanup")
    except Exception as e:
        print(f"[wyr-push] error: {e}")

async def _cleanup_old_wyr_groups():
    """Clean up old WYR group chats and anonymous data"""
    try:
        from registration import _conn
        import datetime
        
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        
        with _conn() as con, con.cursor() as cur:
            # Deactivate old group chats
            cur.execute("""
                UPDATE wyr_group_chats 
                SET is_active = FALSE 
                WHERE vote_date < %s
            """, (yesterday,))
            
            # Clean up old anonymous users (older than 7 days for privacy)
            week_ago = datetime.date.today() - datetime.timedelta(days=7)
            cur.execute("""
                DELETE FROM wyr_anonymous_users 
                WHERE vote_date < %s
            """, (week_ago,))
            
            # Clean up old group messages (older than 7 days)
            cur.execute("""
                DELETE FROM wyr_group_messages 
                WHERE vote_date < %s
            """, (week_ago,))
            
            # Clean up old group chats (older than 7 days)
            cur.execute("""
                DELETE FROM wyr_group_chats 
                WHERE vote_date < %s
            """, (week_ago,))
            
            con.commit()
            print(f"[wyr-cleanup] Cleaned up old groups and anonymous data before {week_ago}")
    except Exception as e:
        print(f"[wyr-cleanup] error: {e}")

# ===================== CONFESSION (NEW 7–8 pm, low-hype) =========================
# 👉 We stop using 8:45 / 9:00 / 9:15 cadence (old), and introduce 7:00 OPEN + 7:30 DELIVERY.
# The old jobs remain in file for backward-compat but won't be scheduled anymore. 
async def job_confession_open_7pm(context: ContextTypes.DEFAULT_TYPE):
    if not _today_cfg().get("confession", False):
        return
    users = await _nudge_users()
    
    # Exciting confession + daily diary messages (rotate based on day)
    day_index = datetime.datetime.now(IST).day % 6  # Expanded to 6 messages
    
    exciting_messages = [
        (
            "🏠 **YOUR ANONYMOUS HOME IS OPEN!** 🏠\n"
            "📖 Share everything - secrets, daily life, feelings!\n\n"
            "🌟 **WHAT YOU CAN SHARE:**\n"
            "• Your deepest secrets & confessions\n"
            "• How was your day? Good things, bad things\n"
            "• Random thoughts floating in your mind\n"
            "• Feelings you need to express\n"
            "• Anything weighing on your heart\n\n"
            "💫 **YOUR SAFE SPACE:**\n"
            "• Complete anonymity guaranteed\n"
            "• No judgment, just understanding\n"
            "• Someone will read & react kindly\n"
            "• Everything stays here, identity stays secret\n\n"
            "🔥 Pour your heart out - secrets, daily life, everything: /confess"
        ),
        (
            "🌙 **EVENING DIARY & CONFESSION TIME** 🌙\n"
            "🎭 Your anonymous sanctuary awaits...\n\n"
            "📝 **SHARE WITH US:**\n"
            "• Hidden secrets you've never told anyone\n"
            "• How your day went from morning to now\n"
            "• Good moments that made you smile\n"
            "• Bad moments that hurt you\n"
            "• People who affected your day\n\n"
            "✨ **THIS IS YOUR HOME:**\n"
            "• Write like nobody's watching\n"
            "• Share confessions & daily experiences\n"
            "• Get reactions from caring strangers\n"
            "• Your identity remains completely secret\n\n"
            "💭 Open your heart - confessions, daily life, everything: /confess"
        ),
        (
            "🔮 **ANONYMOUS TRUTH & DIARY PORTAL** 🔮\n"
            "🏠 This is your secret home - share everything!\n\n"
            "💫 **POUR OUT EVERYTHING:**\n"
            "• Dark secrets you're hiding\n"
            "• Today's victories and failures\n"
            "• Emotions you're processing\n"
            "• Dreams, fears, hopes, worries\n"
            "• Random thoughts about life\n\n"
            "🌟 **SAFE & ANONYMOUS:**\n"
            "• Someone will understand your truth\n"
            "• Daily experiences + deep confessions\n"
            "• No one knows who you are\n"
            "• Everything shared here stays here\n\n"
            "🔥 Share secrets, daily life, feelings - everything: /confess"
        ),
        (
            "💌 **CONFESSION & DIARY HOUR** 💌\n"
            "🌅 How was your day? What secrets do you carry?\n\n"
            "🎯 **TELL US EVERYTHING:**\n"
            "• Confessions you've never shared\n"
            "• What happened in your world today\n"
            "• Best and worst parts of today\n"
            "• Hidden feelings & secret thoughts\n"
            "• Work, love, family - what's going on?\n\n"
            "💭 **YOUR ANONYMOUS DIARY:**\n"
            "• Write confessions & daily experiences\n"
            "• Complete privacy guaranteed\n"
            "• Someone will read & understand\n"
            "• This is your judgment-free home\n\n"
            "✨ Share everything - secrets, daily life, feelings: /confess"
        ),
        (
            "📖 **SECRET DIARY TIME** 📖\n"
            "🏠 Your anonymous home where everything is safe!\n\n"
            "🔥 **SHARE YOUR WHOLE TRUTH:**\n"
            "• Secrets burning inside you\n"
            "• How you're really feeling today\n"
            "• Good news and bad news\n"
            "• Hidden desires & confessions\n"
            "• Daily struggles & victories\n\n"
            "🌙 **COMPLETE FREEDOM:**\n"
            "• Write confessions, daily thoughts, everything\n"
            "• Anonymous but deeply understood\n"
            "• Someone will care about your story\n"
            "• Your identity stays secret forever\n\n"
            "💫 Open up completely - confessions, daily life, all of it: /confess"
        ),
        (
            "🌟 **ANONYMOUS LIFE JOURNAL** 🌟\n"
            "🎭 Share secrets, daily experiences, everything!\n\n"
            "✨ **POUR YOUR HEART OUT:**\n"
            "• Deepest confessions & hidden truths\n"
            "• Today's emotional rollercoaster\n"
            "• Things that made you happy/sad\n"
            "• Secret crushes, fears, dreams\n"
            "• Random thoughts about life & people\n\n"
            "🏠 **THIS IS YOUR HOME:**\n"
            "• Share confessions + daily diary\n"
            "• Complete anonymity & understanding\n"
            "• Someone will connect with your truth\n"
            "• Everything stays between strangers\n\n"
            "🔮 Share it all - secrets, daily life, feelings, everything: /confess"
        )
    ]
    
    # Create inline keyboard with 3 main options
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [
            InlineKeyboardButton("📝 Confess", callback_data="confession_menu:confess"),
            InlineKeyboardButton("📊 My Stats", callback_data="confession_menu:stats")
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="confession_menu:leaderboard")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    txt = exciting_messages[day_index]
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, txt, reply_markup=reply_markup)
            sent += 1
        except Exception:
            pass
    print(f"[conf-open-7pm] sent={sent}/{len(users)}")

async def job_confession_delivery_730pm(context: ContextTypes.DEFAULT_TYPE):
    if not _today_cfg().get("confession", False):
        return
    """Bulletproof confession delivery with hybrid → fallback to original."""
    try:
        from utils.confession_hybrid import deliver_confessions_batch_hybrid
        await deliver_confessions_batch_hybrid(context)
        print("[conf-delivery-7:30] hybrid batch invoked")
    except Exception as e:
        print(f"[conf-delivery-7:30] hybrid batch failed: {e}")
        try:
            from handlers.confession_roulette import deliver_confessions_batch
            await deliver_confessions_batch(context)
            print("[conf-delivery-7:30] fallback to original batch")
        except Exception as e2:
            print(f"[conf-delivery-7:30] all systems failed: {e2}")

# ====== (OLD) Confession jobs kept for backward compatibility (not scheduled) =====
async def job_confession_nudge_15min(context: ContextTypes.DEFAULT_TYPE):
    # legacy: 8:45pm teaser (not used now)
    if not _today_cfg().get("confession", False):
        return
    users = await _nudge_users()
    txt = (
        "🌀 15 minutes to Confession Hour.\n"
        "Drop one secret now — kal yaad rahega, naam nahi.\n"
        "/confess"
    )
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, txt)
            sent += 1
        except Exception:
            pass
    print(f"[conf-nudge-legacy] sent={sent}/{len(users)}")

async def job_confession_reminder(context: ContextTypes.DEFAULT_TYPE):
    # legacy: 9:00 reminder (not used now) - but make it exciting if used
    if not _today_cfg().get("confession", False):
        return
    users = await _nudge_users()
    txt = (
        "🚨 **CONFESSION ALERT! CONFESSION ALERT!** 🚨\n"
        "🔥 Someone couldn't sleep without telling YOU this...\n\n"
        "💀 Their secret is now YOUR secret to carry.\n"
        "🎭 Will you judge them or understand them?\n\n"
        "💥 Drop your truth bomb: /confess\n"
        "⚡ Anonymous but unforgettable..."
    )
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, txt)
            sent += 1
        except Exception:
            pass
    print(f"[conf-reminder-legacy] sent={sent}/{len(users)}")

async def job_confession_delivery(context: ContextTypes.DEFAULT_TYPE):
    # legacy: 9:15 delivery (not used now) — kept as fallback API-compatible
    if not _today_cfg().get("confession", False):
        return
    try:
        from utils.confession_hybrid import deliver_confessions_batch_hybrid
        await deliver_confessions_batch_hybrid(context)
        print("[conf-delivery-legacy] hybrid batch invoked")
    except Exception as e:
        print(f"[conf-delivery-legacy] hybrid batch failed: {e}")
        # Final fallback to original system
        try:
            from handlers.confession_roulette import deliver_confessions_batch
            await deliver_confessions_batch(context)
            print("[conf-delivery-legacy] fallback to original batch")
        except Exception as e2:
            print(f"[conf-delivery-legacy] all systems failed: {e2}")

# ===================== BLUR VAULT =====================
async def job_vault_push(context: ContextTypes.DEFAULT_TYPE):
    if not _today_cfg().get("vault", False):
        return
    try:
        from handlers.blur_vault import push_blur_vault_tease
        await push_blur_vault_tease(context)
        print("[vault-push] Blur-Reveal Vault pushed (day-enabled) at 9:45pm")
    except Exception as e:
        print(f"[vault-push] error: {e}")

# ===================== FANTASY MATCH ==================
async def job_fantasy_push(context: ContextTypes.DEFAULT_TYPE):
    if not _today_cfg().get("fantasy", False):
        return
    try:
        from handlers.fantasy_match import push_fantasy_match
        await push_fantasy_match(context)
        print("[fantasy-push] Fantasy Match pushed (day-enabled) at 10:15pm")
    except Exception as e:
        print(f"[fantasy-push] error: {e}")

# ===================== DARE ===========================
async def job_dare_drop(context: ContextTypes.DEFAULT_TYPE):
    if not _today_cfg().get("dare", False):
        return
    try:
        from handlers.advanced_dare import push_advanced_dare_notification
        await push_advanced_dare_notification(context)
        print("[advanced-dare] Notification sent successfully")
    except Exception as e:
        print(f"[advanced-dare] Error: {e}")
        # Fallback to basic notification
        users = await _nudge_users()
        from utils.daily_prompts import get_daily_dare
        dare = get_daily_dare()
        txt = f"🚨 Advanced Dare System is LIVE!\n👉 Your Dare: {dare}\n(Type /timedare to accept)"

        sent = 0
        for uid in users:
            try:
                await context.bot.send_message(uid, txt)
                sent += 1
            except Exception:
                pass
        print(f"[dare-drop-fallback] sent={sent}/{len(users)}")

# ===================== AFTER DARK =====================
async def job_afterdark_teaser(context: ContextTypes.DEFAULT_TYPE):
    if not _today_cfg().get("afterdark", False):
        return
    users = await _nudge_users()
    txt = "🌙 After Dark opens in 5 minutes!\n⚠️ Premium only. Upgrade to unlock 🔥"
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, txt)
            sent += 1
        except Exception:
            pass
    print(f"[afterdark-teaser] sent={sent}/{len(users)}")

async def job_afterdark_open(context: ContextTypes.DEFAULT_TYPE):
    if not _today_cfg().get("afterdark", False):
        return
    users = await _nudge_users()
    txt = "🌙 After Dark is OPEN!\nEnter now — 30 minutes only 🔥"
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, txt)
            sent += 1
        except Exception:
            pass
    print(f"[afterdark-open] sent={sent}/{len(users)}")

# ===================== DAILY HOROSCOPE (8AM MORNING HABIT) ======================
async def job_daily_horoscope_8am(context: ContextTypes.DEFAULT_TYPE):
    """Daily horoscope notification to start everyone's day - builds morning habit"""
    users = await _nudge_users()  # Use the proper function that gets ALL users
    
    # Motivating morning horoscope messages (rotate daily for variety)
    day_index = datetime.datetime.now(IST).day % 4
    
    messages = [
        (
            "🌅 **GOOD MORNING! START YOUR DAY RIGHT** 🌅\n\n"
            "🔮 **Your Daily Horoscope Awaits...**\n"
            "✨ Discover what the stars have planned for you today!\n\n"
            "⭐ **Why check your horoscope?**\n"
            "• Get daily guidance and inspiration\n"
            "• Know your lucky moments\n"
            "• Start your day with cosmic confidence\n"
            "• Plan your day with celestial wisdom\n\n"
            "🌟 **Tap to see your personalized reading:**\n"
            "/horoscope\n\n"
            "💫 Make it a daily morning ritual!"
        ),
        (
            "☀️ **MORNING COSMIC CHECK-IN** ☀️\n\n"
            "🔮 **What do the stars say about your day?**\n"
            "Your zodiac sign holds today's secrets...\n\n"
            "✨ **Today's cosmic energy could bring:**\n"
            "• New opportunities\n"
            "• Lucky encounters\n"
            "• Positive breakthroughs\n"
            "• Guidance for important decisions\n\n"
            "⭐ **Get your personalized prediction:**\n"
            "/horoscope\n\n"
            "🌟 Start every day with star power!"
        ),
        (
            "🌟 **DAILY STAR GUIDANCE** 🌟\n\n"
            "🔮 **The universe has a message for you today!**\n"
            "Your personal horoscope is ready...\n\n"
            "💫 **Morning horoscope benefits:**\n"
            "• Set positive intentions\n"
            "• Know your best timing\n"
            "• Navigate challenges wisely\n"
            "• Attract good energy all day\n\n"
            "✨ **Discover your cosmic forecast:**\n"
            "/horoscope\n\n"
            "⭐ Your daily dose of celestial wisdom awaits!"
        ),
        (
            "🌅 **COSMIC MORNING BOOST** 🌅\n\n"
            "🔮 **Ready to unlock today's potential?**\n"
            "Your zodiac sign reveals today's path...\n\n"
            "⭐ **Start your day with clarity:**\n"
            "• Know your strengths today\n"
            "• Spot the best opportunities\n"
            "• Avoid potential challenges\n"
            "• Align with cosmic energy\n\n"
            "🌟 **Check your daily reading:**\n"
            "/horoscope\n\n"
            "✨ Make the stars your daily guide!"
        )
    ]
    
    txt = messages[day_index]
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, txt)
            sent += 1
        except Exception:
            pass
    print(f"[daily-horoscope-8am] sent={sent}/{len(users)}")