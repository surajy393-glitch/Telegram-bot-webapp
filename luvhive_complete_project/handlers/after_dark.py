# handlers/after_dark.py
import logging, random, json
from typing import List, Tuple
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (ContextTypes, CommandHandler, CallbackQueryHandler,
                          MessageHandler, filters)

import registration as reg
from handlers.text_framework import (
    claim_or_reject, clear_state, FEATURE_KEY, MODE_KEY, make_cancel_kb
)

log = logging.getLogger("afterdark")

# =================== CONFIG ===================
AD_DEFAULT_DURATION_MIN = 30            # 30m lounge (change to 15 if you want)
AD_PROMPT_INTERVAL_SEC  = 180           # periodic prompt every 3 min
AD_MEDIA_TTL_SEC        = 15            # self-destruct TTL for media (sec)
AD_GROUP_RELAY_PRIORITY = -14           # after fantasy_relay(-15)
AD_GROUP_LOBBY_PRIORITY = -10

ANON_PREFIX = "User"

# =================== DB HELPERS ===================
def _exec(query: str, params: tuple = ()):
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                return cur.fetchall()
            con.commit()
            return True
    except Exception as e:
        log.error(f"[AD][DB] {e} :: {query} :: {params}")
        return None

def _exec_returning(query: str, params: tuple = ()):
    """Run a statement that returns ONE row (e.g., INSERT ... RETURNING id)."""
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            con.commit()
            return row
    except Exception as e:
        log.error(f"[AD][DB returning] {e} :: {query} :: {params}")
        return None

def ensure_ad_tables():
    _exec("""
      CREATE TABLE IF NOT EXISTS ad_sessions (
        id BIGSERIAL PRIMARY KEY,
        started_at TIMESTAMPTZ DEFAULT NOW(),
        ends_at    TIMESTAMPTZ NOT NULL,
        vibe       TEXT,
        status     TEXT DEFAULT 'live'  -- live|expired|cancelled
      );
    """)
    _exec("""
      CREATE TABLE IF NOT EXISTS ad_participants (
        id BIGSERIAL PRIMARY KEY,
        session_id BIGINT REFERENCES ad_sessions(id) ON DELETE CASCADE,
        user_id    BIGINT NOT NULL,
        anon_name  TEXT NOT NULL,
        joined_at  TIMESTAMPTZ DEFAULT NOW(),
        left_at    TIMESTAMPTZ
      );
    """)
    _exec("""
      CREATE TABLE IF NOT EXISTS ad_prompts (
        id BIGSERIAL PRIMARY KEY,
        session_id BIGINT REFERENCES ad_sessions(id) ON DELETE CASCADE,
        kind  TEXT NOT NULL,   -- poll|truth|dare|drop
        payload JSONB NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
      );
    """)
    _exec("""
      CREATE TABLE IF NOT EXISTS ad_messages (
        id BIGSERIAL PRIMARY KEY,
        session_id BIGINT REFERENCES ad_sessions(id) ON DELETE CASCADE,
        user_id BIGINT,
        anon_name TEXT,
        msg_type TEXT NOT NULL,      -- text|reaction|vote|media|truth|dare_done
        content  TEXT,
        meta     JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
      );
    """)
    log.info("[AD] ensured tables")

def ensure(app):
    """Main entry point called by main.py"""
    ensure_ad_tables()
    register(app)

# =================== TIME/SESSION HELPERS ===================
def _create_session(duration_min: int) -> int:
    row = _exec_returning("""
        INSERT INTO ad_sessions(ends_at, status)
        VALUES (NOW() + INTERVAL %s, 'live')
        RETURNING id
    """, (f"{duration_min} minutes",))
    return int(row[0]) if row else None

def _get_live_session():
    r = _exec("""SELECT id, started_at, ends_at, vibe, status
                   FROM ad_sessions
                  WHERE status='live' AND ends_at>NOW()
               ORDER BY started_at DESC LIMIT 1""")
    return r[0] if r else None

def _ends_in_minutes(session_id: int) -> int:
    row = _exec("""
        SELECT COALESCE(
                 GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (ends_at - NOW())) / 60)),
                 0
               )::int AS left_min
          FROM ad_sessions
         WHERE id=%s
    """, (session_id,))
    try:
        return int(row[0][0]) if row else 0
    except Exception:
        return 0

def _random_anon_name(session_id:int) -> str:
    used = {r[0] for r in (_exec("SELECT anon_name FROM ad_participants WHERE session_id=%s",(session_id,)) or [])}
    for i in range(1, 10000):
        n = f"{ANON_PREFIX}{i}"
        if n not in used: return n
    return f"{ANON_PREFIX}{random.randint(10000,99999)}"

def _join_session(session_id:int, user_id:int) -> str:
    row = _exec("""SELECT anon_name FROM ad_participants
                   WHERE session_id=%s AND user_id=%s AND left_at IS NULL""",(session_id,user_id))
    if row: return row[0][0]
    anon = _random_anon_name(session_id)
    ok = _exec("""INSERT INTO ad_participants(session_id,user_id,anon_name)
                  VALUES(%s,%s,%s)""",(session_id,user_id,anon))
    return anon if ok else None

def _list_participants(session_id:int) -> List[Tuple[int,int,str]]:
    """Return active participants for a session."""
    rows = _exec("""
        SELECT user_id, id, anon_name
          FROM ad_participants
         WHERE session_id=%s AND left_at IS NULL
    """, (session_id,))
    # force into 3-tuple structure
    return [(r[0], r[1], r[2]) for r in (rows or [])]

def _set_vibe(session_id:int, vibe:str):
    _exec("UPDATE ad_sessions SET vibe=%s WHERE id=%s",(vibe,session_id))

def _extend_session(session_id:int, minutes:int):
    _exec("UPDATE ad_sessions SET ends_at=ends_at+INTERVAL %s",(f"{minutes} minutes",))

async def _broadcast(context: ContextTypes.DEFAULT_TYPE, session_id:int, text:str,
                     kb:InlineKeyboardMarkup=None):
    participants = _list_participants(session_id)
    user_ids = [u for (u,_,_) in participants]
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, text,
                                           reply_markup=kb,
                                           parse_mode="Markdown")
        except Exception as e:
            log.debug(f"[AD] broadcast fail {uid}: {e}")

def _log_ad_event(session_id:int, user_id:int, anon:str, msg_type:str, content:str=None, meta:dict=None):
    try:
        _exec("""INSERT INTO ad_messages(session_id,user_id,anon_name,msg_type,content,meta)
                 VALUES(%s,%s,%s,%s,%s,%s)""",
              (session_id, user_id, anon, msg_type, content, json.dumps(meta or {})))
    except Exception as e:
        log.debug(f"[AD] log event fail: {e}")

# =================== BANKS ===================

# --- 50 Dirty TRUTHS (premium quality) ---
TRUTH_BANK = [
    "What's the dirtiest thought you've ever had about a total stranger?",
    "Do you prefer sex at night, in the morning, mid-afternoon, or NOW?",
    "What's your favorite way to be seduced?",
    "What's the dirtiest fantasy you've had at work?",
    "How would you dominate your boss sexually if given the chance?",
    "What do you do when you get horny in public?",
    "Have you ever masturbated in a public bathroom?",
    "What's the weirdest thing you've thought about while touching yourself?",
    "What's the strangest prop you've used to get yourself off?",
    "Do you remember the first time you felt aroused?",
    "Who gave you your first orgasm?",
    "Do you remember what that first orgasm felt like?",
    "Have you ever had sex with someone whose name you never knew?",
    "What's your favorite thing about a quickie?",
    "What's the most sexually daring thing you've ever done?",
    "Have you ever fantasized about fucking one of your teachers?",
    "Do you ever mentally strip strangers just for kicks?",
    "And then imagine, in dirty detail, what it would be like to fuck them?",
    "Have you ever kissed someone of the same sex?",
    "What inspires you to make the first move?",
    "In your opinion, what does it mean to be good in bed?",
    "Have you ever cheated on a boyfriend or girlfriend because you just couldn't help yourself?",
    "Have you ever pushed the boundaries of fidelity to the brink and then retreated just for the rush?",
    "Do you have a go-to masturbation fantasy?",
    "What kind of porn turns you on?",
    "Have you ever had sex with your eyes closed?",
    "Have you ever blindfolded or handcuffed your partner?",
    "Does naughty talk get you aroused?",
    "Are you sure about that, my dirty little forest nymph of a sex goddess?",
    "What's the dirtiest thing someone's ever said to you during sex?",
    "Have you ever watched another couple get it on without them knowing?",
    "Have you ever watched another couple have sex with their permission?",
    "How would you respond if a couple approached you to be their 'third'?",
    "What's the most flattering thing someone's said about your naked body?",
    "When's the last time you had a vivid sex dream?",
    "What do you think an orgy would be like?",
    "Have you ever propositioned a total stranger?",
    "What does your ideal one-night stand look like?",
    "How long does it take you to get yourself off, on average?",
    "What's the weirdest thing that turns you on?",
    "Have you ever had a naughty dream about a close friend or family member?",
    "Have you ever woken up humping your pillow?",
    "When's the last time you orgasmed in your sleep?",
    "What's the most embarrassing thing that's happened to you while hooking up?",
    "Do you like touching yourself in front of the people you sleep with?",
    "What's the dirtiest text you've ever sent or received?",
    "Do you prefer professional or amateur porn?",
    "What's your favorite blowjob technique?",
    "If you had to pick, would you be a dominatrix or a submissive?",
    "Is there anything you won't do in bed?"
]

# --- 50 Dirty DARES (premium quality) ---
DARE_BANK = [
    "Describe your last naughty dream in vivid detail (one paragraph).",
    "Share the dirtiest thing you've ever whispered to someone.",
    "Confess your wildest sexual fantasy that you've never told anyone.",
    "Describe what you'd do if you had someone naked in your bed right now.",
    "Share your most shameful turn-on that would shock people.",
    "Write exactly what you'd text someone to make them rush over to you.",
    "Describe how you'd seduce your neighbor if they knocked on your door.",
    "Text what you'd say to turn an innocent conversation dirty.",
    "Write what you'd whisper in someone's ear in a crowded elevator.",
    "Compose the sexiest voice message script (in text).",
    "Share your most embarrassing masturbation story.",
    "Describe your perfect one-night stand scenario step by step.",
    "Confess the weirdest place you've gotten yourself off.",
    "Share what goes through your mind during your alone time.",
    "Describe your most intense orgasm experience.",
    "Write what you'd do in a hotel room with a stranger for one hour.",
    "Describe your ideal friends-with-benefits arrangement.",
    "Share how you'd corrupt an innocent person.",
    "Write your perfect 'caught in the act' fantasy.",
    "Describe what you'd do if you walked in on your roommate.",
    "Share your secret kink that you're too embarrassed to try.",
    "Describe the roughest thing you want done to you.",
    "Confess your taboo fantasy that you think about daily.",
    "Share what you'd let someone do for money.",
    "Describe your wildest public sex fantasy.",
    "Write the dirtiest pickup line that actually works.",
    "Describe how you'd make someone beg for you.",
    "Share your most effective seduction technique in detail.",
    "Write what you'd do to drive someone completely wild.",
    "Describe your signature move that never fails.",
    "Confess who you fantasize about that you shouldn't.",
    "Share your dirtiest thought about someone you know.",
    "Describe what you'd do if you could read minds during sex.",
    "Confess your most inappropriate workplace fantasy.",
    "Share what you think about your friend's partner.",
    "Describe your most depraved fantasy in graphic detail.",
    "Share what you'd do if you could fuck anyone for one night.",
    "Confess your darkest sexual desire that scares you.",
    "Describe how you'd use someone for your pleasure.",
    "Share what you'd do if consequences didn't exist.",
    "Describe your sluttiest moment in full detail.",
    "Share your most intense hookup story.",
    "Confess the most people you've been with in one day/week.",
    "Describe your best revenge sex experience.",
    "Share your wildest drunk hookup story.",
    "Write what you'd do to someone tied up and helpless.",
    "Describe your perfect dominant/submissive scenario.",
    "Share how you'd break someone's innocence.",
    "Write what you'd do if you could control someone's body.",
    "Describe the nastiest thing you want someone to do to you."
]

# --- 50 Exclusive POLLS (premium quality) ---
# Each poll = {"question": "...", "wild": "option text", "sweet": "option text"}
POLL_BANK = [
    {"question":"Would you rather...", "wild":"Fuck in a public bathroom", "sweet":"Get fucked on a rooftop under stars"},
    {"question":"Choose your poison...", "wild":"Be dominated roughly for an hour", "sweet":"Dominate someone completely"},
    {"question":"Pick your fantasy...", "wild":"Threesome with strangers", "sweet":"Intense one-on-one all night"},
    {"question":"What gets you wetter/harder...", "wild":"Dirty talk in your ear", "sweet":"Being teased until you beg"},
    {"question":"Choose your kink...", "wild":"Blindfolded and tied up", "sweet":"Role playing as strangers"},
    {"question":"Where would you rather cum...", "wild":"In someone's mouth", "sweet":"While being watched"},
    {"question":"Pick your pleasure...", "wild":"Quickie in a risky place", "sweet":"Marathon session in bed"},
    {"question":"What turns you on more...", "wild":"Someone begging for you", "sweet":"You begging for them"},
    {"question":"Choose your temptation...", "wild":"Fuck your friend's ex", "sweet":"Seduce your crush's friend"},
    {"question":"Pick your poison...", "wild":"Be used as a fuck toy", "sweet":"Use someone as your toy"},
    {"question":"What makes you cum harder...", "wild":"Being called dirty names", "sweet":"Eye contact during orgasm"},
    {"question":"Choose your addiction...", "wild":"Getting head every day", "sweet":"Giving head every day"},
    {"question":"Pick your guilty pleasure...", "wild":"Masturbating to your ex", "sweet":"Masturbating to your friend"},
    {"question":"What's hotter...", "wild":"Fucking in your parents' house", "sweet":"Fucking at your workplace"},
    {"question":"Choose your taboo...", "wild":"Teacher-student roleplay", "sweet":"Boss-employee roleplay"},
    {"question":"Pick your rush...", "wild":"Almost getting caught", "sweet":"Actually getting caught"},
    {"question":"What's your weakness...", "wild":"Someone's moans", "sweet":"Someone's dirty texts"},
    {"question":"Choose your shame...", "wild":"Having loud sex with neighbors hearing", "sweet":"Sexting during a family dinner"},
    {"question":"Pick your corruption...", "wild":"Making an innocent person dirty", "sweet":"Being corrupted by someone experienced"},
    {"question":"What gets you off more...", "wild":"Multiple orgasms in one session", "sweet":"One earth-shattering orgasm"},
    {"question":"Choose your nasty...", "wild":"Anal on the first date", "sweet":"Oral on the first meet"},
    {"question":"Pick your perversion...", "wild":"Watch someone masturbate", "sweet":"Be watched while masturbating"},
    {"question":"What's more tempting...", "wild":"Revenge sex with your ex", "sweet":"Hate sex with your enemy"},
    {"question":"Choose your sin...", "wild":"Cheat with someone hotter", "sweet":"Make someone cheat on their partner"},
    {"question":"Pick your fetish...", "wild":"Being spanked until you cry", "sweet":"Spanking someone until they beg"},
    {"question":"What drives you wild...", "wild":"Being choked during sex", "sweet":"Choking someone during sex"},
    {"question":"Choose your obsession...", "wild":"Someone's used underwear", "sweet":"Someone's sex toys"},
    {"question":"Pick your fantasy...", "wild":"Gangbang with multiple people", "sweet":"Being the center of an orgy"},
    {"question":"What's more satisfying...", "wild":"Making someone squirt", "sweet":"Squirting on someone"},
    {"question":"Choose your thrill...", "wild":"Sex while others sleep nearby", "sweet":"Sex while on a video call"},
    {"question":"Pick your degradation...", "wild":"Being called a slut/whore", "sweet":"Calling someone your slut/whore"},
    {"question":"Choose your submission...", "wild":"Crawling naked to someone", "sweet":"Making someone crawl to you"},
    {"question":"What's more addictive...", "wild":"The taste of cum", "sweet":"The sound of someone cumming"},
    {"question":"Pick your punishment...", "wild":"Being edged for hours", "sweet":"Edging someone for hours"},
    {"question":"Choose your humiliation...", "wild":"Being naked in front of strangers", "sweet":"Making someone strip for you"},
    {"question":"What makes you dirtier...", "wild":"Swallowing every drop", "sweet":"Making someone lick you clean"},
    {"question":"Pick your deviance...", "wild":"Fucking someone's partner while they watch", "sweet":"Watching your partner fuck someone else"},
    {"question":"Choose your control...", "wild":"Remote control vibrator in public", "sweet":"Controlling someone's orgasms"},
    {"question":"What's more shameful...", "wild":"Getting off to someone's social media", "sweet":"Getting off while video calling someone"},
    {"question":"Pick your desperation...", "wild":"Begging someone to fuck you", "sweet":"Making someone beg to fuck you"},
    {"question":"Choose your nasty secret...", "wild":"Masturbating at work", "sweet":"Having sex at work"},
    {"question":"Pick your shame...", "wild":"Getting caught by your parents", "sweet":"Catching your parents"},
    {"question":"What's more intense...", "wild":"Cumming so hard you blackout", "sweet":"Making someone cum so hard they blackout"},
    {"question":"Choose your addiction...", "wild":"Can't go a day without masturbating", "sweet":"Can't go a day without sex"},
    {"question":"Pick your perversion...", "wild":"Smell someone's dirty clothes", "sweet":"Taste someone after they've been with someone else"},
    {"question":"What's more forbidden...", "wild":"Fucking your best friend's crush", "sweet":"Fucking your crush's best friend"},
    {"question":"Choose your ultimate...", "wild":"Have the best sex of your life once", "sweet":"Have mediocre sex every day forever"},
    {"question":"Pick your poison...", "wild":"Be someone's dirty secret", "sweet":"Have someone as your dirty secret"},
    {"question":"What's more satisfying...", "wild":"Making your ex jealous with better sex", "sweet":"Having your ex beg to come back"},
    {"question":"Final choice...", "wild":"Know everyone's sexual thoughts about you", "sweet":"Read everyone's mind during sex"}
]

# =================== WHEEL HELPERS ===================
WHEEL = ["poll","truth","dare","drop"]

def _pick_wheel() -> str:
    return random.choice(WHEEL)

def _prompt_text_for(kind: str, payload: dict | None = None) -> str:
    if kind == "poll":
        q  = (payload or {}).get("question") or "Exclusive Poll — choose one"
        w  = (payload or {}).get("wild") or "Wild"
        s  = (payload or {}).get("sweet") or "Sweet"
        return f"🗳 *Exclusive Poll*: {q}\n\n🔥 *Wild*: {w}\n❤️ *Sweet*: {s}"
    if kind == "truth":
        t = (payload or {}).get("text") or "Share one truth in one line."
        return f"💬 *Dark Truth*: {t}"
    if kind == "dare":
        d = (payload or {}).get("text") or "Do a tiny dare right here."
        return f"😈 *Community Dare*: {d}"
    if kind == "drop":
        return "🎁 *Dark Drop*: Free blurred reveal / spicy confession"
    return "🎯 Surprise"

def _build_wheel_kb(kind: str, payload: dict | None = None) -> InlineKeyboardMarkup:
    if kind == "poll":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Wild",  callback_data="ad:vote:wild"),
             InlineKeyboardButton("❤️ Sweet", callback_data="ad:vote:sweet")]
        ])
    if kind == "truth":
        return InlineKeyboardMarkup([[InlineKeyboardButton("✍️ Answer", callback_data="ad:truth:ans")]])
    if kind == "dare":
        return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="ad:dare:done")]])
    if kind == "drop":
        return InlineKeyboardMarkup([[InlineKeyboardButton("👀 View Drop", callback_data="ad:drop:view")]])
    return InlineKeyboardMarkup([])

def _save_prompt(session_id:int, kind:str, payload:dict) -> int | None:
    row = _exec_returning("""INSERT INTO ad_prompts(session_id,kind,payload)
                             VALUES(%s,%s,%s) RETURNING id""",
                          (session_id, kind, json.dumps(payload)))
    return int(row[0]) if row else None

def _schedule_delete(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, ttl_sec: int):
    """Schedule message deletion after TTL seconds"""
    jq = getattr(context, "job_queue", None)
    if jq:
        jq.run_once(_delete_message_job, when=ttl_sec, 
                    data={"chat_id": chat_id, "message_id": message_id})

async def _delete_message_job(context: ContextTypes.DEFAULT_TYPE):
    """Job to delete a message"""
    data = context.job.data or {}
    chat_id = data.get("chat_id")
    message_id = data.get("message_id")
    if chat_id and message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            log.debug(f"[AD] delete message fail: {e}")

# =============== ENTRY / LOBBY =================
async def _blocked_non_premium(update:Update, context:ContextTypes.DEFAULT_TYPE)->bool:
    uid = update.effective_user.id
    if not reg.has_active_premium(uid):
        await update.effective_message.reply_text(
            "🕯️ *After Dark* is premium-only.\n"
            "Unlock the lounge for intimate polls, dark truths & exclusive drops.\n"
            "💎 /premium to upgrade", parse_mode="Markdown")
        return True
    return False

async def _ensure_lobby_state(update:Update, context:ContextTypes.DEFAULT_TYPE, ttl=10):
    if context.user_data.get(FEATURE_KEY)!="afterdark" or context.user_data.get(MODE_KEY) not in ("lobby","live"):
        await claim_or_reject(update, context, feature="afterdark", mode="lobby", ttl_minutes=ttl)

async def cmd_afterdark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _blocked_non_premium(update, context): return
    await _ensure_lobby_state(update, context)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Enter Lounge", callback_data="ad:enter")],
        [InlineKeyboardButton("🎡 Spin Wheel",   callback_data="ad:wheel")],
        [InlineKeyboardButton("📜 Rules",        callback_data="ad:rules")]
    ])
    await update.message.reply_text(
      "🕯️ *After Dark Lounge*\n"
      "• Time-boxed room • No forwards • Self-destruct media\n"
      f"• Community prompts every {AD_PROMPT_INTERVAL_SEC//60} min\n\nChoose:",
      reply_markup=kb, parse_mode="Markdown"
    )

async def ad_rules_cb(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await _ensure_lobby_state(update, context)
    await q.message.reply_text(
        "📜 *Rules*\n• Be kind.\n• No forwards; media self-destruct.\n"
        "• Bot can't block screenshots—share wisely.\n• Report/Block anytime.",
        parse_mode="Markdown"
    )

async def ad_enter_cb(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await _ensure_lobby_state(update, context)
    if not reg.has_active_premium(q.from_user.id):
        return await q.message.reply_text("🕯️ After Dark is premium-only.\n💎 /premium", parse_mode="Markdown")

    live = _get_live_session()
    sid  = live[0] if live else _create_session(AD_DEFAULT_DURATION_MIN)
    if not sid: return await q.message.reply_text("❌ Could not start lounge. Try again.")

    anon = _join_session(sid, q.from_user.id)
    if not anon: return await q.message.reply_text("❌ Could not join lounge. Try again.")

    context.user_data[FEATURE_KEY] = "afterdark"
    context.user_data[MODE_KEY]    = "live"
    left = _ends_in_minutes(sid)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎡 Spin Wheel", callback_data="ad:wheel")],
        [InlineKeyboardButton("⏳ Extend 15m (20 coins)", callback_data="ad:extend:15")],
        [InlineKeyboardButton("🚪 End", callback_data="ad:end")]
    ])
    await q.message.reply_text(
        f"💬 *After Dark Lounge* • ⏳ {left:02d}:00 left\n"
        "Safety: no forwards • media self-destruct • be kind",
        reply_markup=kb, parse_mode="Markdown"
    )
    _start_prompt_timer(context, sid)

# =============== WHEEL (Truth/Dare/Poll/Drop) ===============
def _start_prompt_timer(context: ContextTypes.DEFAULT_TYPE, session_id:int):
    jq = getattr(context,"job_queue",None)
    if jq:
        jq.run_repeating(_periodic_prompt, interval=AD_PROMPT_INTERVAL_SEC, first=AD_PROMPT_INTERVAL_SEC,
                         data={"session_id": session_id})

async def _periodic_prompt(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data or {}
    sid  = data.get("session_id")
    if not sid: return
    row = _exec("SELECT status, ends_at FROM ad_sessions WHERE id=%s",(sid,))
    if not row or row[0][0]!="live":
        try: context.job.schedule_removal()
        except: pass
        return
    kind = _pick_wheel()
    payload = {}
    if kind=="truth":
        payload = {"text": random.choice(TRUTH_BANK)}
    elif kind=="dare":
        payload = {"text": random.choice(DARE_BANK)}
    elif kind=="poll":
        poll = random.choice(POLL_BANK)
        payload = {"question": poll["question"], "wild": poll["wild"], "sweet": poll["sweet"]}
    elif kind=="drop":
        payload = {"note": "vault"}

    pid = _save_prompt(sid, kind, payload)
    await _broadcast(context, sid, _prompt_text_for(kind, payload), _build_wheel_kb(kind))
    if kind=="poll" and pid:
        jq = getattr(context,"job_queue",None)
        if jq:
            jq.run_once(_poll_summary_job, when=60, data={"session_id": sid, "prompt_id": pid,
                                                          "question": payload["question"],
                                                          "wild": payload["wild"], "sweet": payload["sweet"]})

async def ad_wheel_cb(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await _ensure_lobby_state(update, context)
    live = _get_live_session()
    sid  = live[0] if live else _create_session(AD_DEFAULT_DURATION_MIN)
    if not sid: 
        return await q.message.reply_text("❌ Could not start lounge. Try again.")

    kind = _pick_wheel()
    _set_vibe(sid, kind)

    payload = {}
    if kind=="truth":
        payload = {"text": random.choice(TRUTH_BANK)}
    elif kind=="dare":
        payload = {"text": random.choice(DARE_BANK)}
    elif kind=="poll":
        poll = random.choice(POLL_BANK)
        payload = {"question": poll["question"], "wild": poll["wild"], "sweet": poll["sweet"]}
    elif kind=="drop":
        payload = {"note": "vault"}

    pid = _save_prompt(sid, kind, payload)
    await _broadcast(context, sid, f"🎡 *Wheel of Temptation*: {kind.upper()}")
    await _broadcast(context, sid, _prompt_text_for(kind, payload), _build_wheel_kb(kind))

    if kind=="poll" and pid:
        jq = getattr(context,"job_queue",None)
        if jq:
            jq.run_once(_poll_summary_job, when=60, data={"session_id": sid, "prompt_id": pid,
                                                          "question": payload["question"],
                                                          "wild": payload["wild"], "sweet": payload["sweet"]})

# =============== POLL: vote + summary(1m) =================
async def ad_vote_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer("Vote recorded")
    if context.user_data.get(FEATURE_KEY)!="afterdark" or context.user_data.get(MODE_KEY)!="live":
        return
    live = _get_live_session()
    if not live: return
    sid = live[0]

    choice = q.data.split(":")[-1]  # wild|sweet
    row = _exec("""SELECT anon_name FROM ad_participants
                   WHERE session_id=%s AND user_id=%s AND left_at IS NULL""",
                (sid, q.from_user.id))
    anon = row[0][0] if row else f"{ANON_PREFIX}?"

    _log_ad_event(sid, q.from_user.id, anon, "vote", content="poll", meta={"choice": choice})

    await q.message.reply_text(f"🗳 Vote recorded: **{choice.title()}**", parse_mode="Markdown")

async def _poll_summary_job(context: ContextTypes.DEFAULT_TYPE):
    """Job to send poll summary after 1 minute"""
    data = context.job.data or {}
    sid = data.get("session_id")
    pid = data.get("prompt_id")
    question = data.get("question")
    wild_text = data.get("wild")
    sweet_text = data.get("sweet")
    
    if not sid: return
    
    # Count votes
    votes = _exec("""SELECT meta->>'choice' as choice, COUNT(*) as count
                     FROM ad_messages 
                     WHERE session_id=%s AND msg_type='vote' AND content='poll'
                     GROUP BY meta->>'choice'""", (sid,))
    
    wild_count = 0
    sweet_count = 0
    for vote_row in (votes or []):
        choice, count = vote_row
        if choice == "wild":
            wild_count = int(count)
        elif choice == "sweet":
            sweet_count = int(count)
    
    total = wild_count + sweet_count
    if total == 0:
        summary = "📊 *Poll Results*: No votes yet!"
    else:
        wild_pct = int((wild_count / total) * 100)
        sweet_pct = int((sweet_count / total) * 100)
        summary = f"📊 *Poll Results*: {question}\n\n🔥 *Wild* ({wild_count}): {wild_pct}%\n❤️ *Sweet* ({sweet_count}): {sweet_pct}%"
    
    await _broadcast(context, sid, summary)

# =============== TRUTH: answer + broadcast ===============
async def ad_truth_ans_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # claim a short truth-answer mode (30s TTL)
    await claim_or_reject(update, context, feature="afterdark", mode="truth_ans", ttl_minutes=1)
    await q.message.reply_text("✍️ Send your *one-line* truth answer now.", parse_mode="Markdown")

async def ad_truth_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get(FEATURE_KEY)!="afterdark" or context.user_data.get(MODE_KEY)!="truth_ans":
        return
    live = _get_live_session()
    if not live: return
    sid = live[0]
    row = _exec("""SELECT anon_name FROM ad_participants
                   WHERE session_id=%s AND user_id=%s AND left_at IS NULL""",
                (sid, update.effective_user.id))
    anon = row[0][0] if row else f"{ANON_PREFIX}?"
    txt = (update.effective_message.text or "").strip()
    if not txt: return
    _log_ad_event(sid, update.effective_user.id, anon, "truth", content=txt)
    # broadcast the answer
    for uid in [u[0] for u in _list_participants(sid) if u[0]!=update.effective_user.id]:
        try:
            await context.bot.send_message(uid, f"💬 **{anon}** (Truth): {txt}", parse_mode="Markdown")
        except Exception as e:
            log.debug(f"[AD] truth broadcast fail: {e}")
    # back to live mode
    context.user_data[MODE_KEY] = "live"

# =============== DARE: done + broadcast ===============
async def ad_dare_done_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Noted!")
    if context.user_data.get(FEATURE_KEY)!="afterdark" or context.user_data.get(MODE_KEY)!="live":
        return
    live = _get_live_session()
    if not live: return
    sid = live[0]
    row = _exec("""SELECT anon_name FROM ad_participants
                   WHERE session_id=%s AND user_id=%s AND left_at IS NULL""",
                (sid, q.from_user.id))
    anon = row[0][0] if row else f"{ANON_PREFIX}?"
    _log_ad_event(sid, q.from_user.id, anon, "dare_done")
    await q.message.reply_text(f"✅ **{anon}** completed the dare.", parse_mode="Markdown")

# =============== DROP: vault reveal ===============
async def ad_drop_view_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # Only when After Dark live
    if context.user_data.get(FEATURE_KEY) != "afterdark" or context.user_data.get(MODE_KEY) != "live":
        return

    live = _get_live_session()
    if not live:
        return
    sid = live[0]

    # Fetch any approved vault content (random)
    row = _exec("""
        SELECT id, media_type, file_id, file_url, content_text
        FROM vault_content
        WHERE approval_status='approved' AND status='approved'
        ORDER BY RANDOM()
        LIMIT 1
    """)
    if not row:
        return await q.message.reply_text("⚠️ No approved drops available right now.")

    vc_id, media_type, file_id, file_url, content_text = row[0]

    participants = [u[0] for (u,_,_) in _list_participants(sid)]
    sent_ids = []

    try:
        if media_type in ("image","photo") and file_id:
            for uid in participants:
                sent = await context.bot.send_photo(
                    uid, file_id,
                    caption="👀 *Dark Drop revealed!*",
                    parse_mode="Markdown",
                    protect_content=True
                )
                sent_ids.append((sent.chat_id, sent.message_id))

        elif media_type=="video" and file_id:
            for uid in participants:
                sent = await context.bot.send_video(
                    uid, file_id,
                    caption="👀 *Dark Drop revealed!*",
                    parse_mode="Markdown",
                    protect_content=True
                )
                sent_ids.append((sent.chat_id, sent.message_id))

        else:
            # fallback to text drop
            body = content_text or "👀 *Dark Drop revealed!*"
            for uid in participants:
                await context.bot.send_message(uid, body, parse_mode="Markdown")

        # optional self-destruct
        if sent_ids and AD_MEDIA_TTL_SEC>0:
            for (cid, mid) in sent_ids:
                _schedule_delete(context, cid, mid, AD_MEDIA_TTL_SEC)

        # update counters
        _exec("""
            UPDATE vault_content
               SET view_count = COALESCE(view_count,0)+1,
                   reveal_count = COALESCE(reveal_count,0)+1
             WHERE id=%s
        """, (vc_id,))
    except Exception as e:
        log.error(f"[AD] drop error: {e}")
        await q.message.reply_text("❌ Failed to reveal drop. Try again.")

# =============== SESSION MANAGEMENT ===============
async def ad_extend_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if context.user_data.get(FEATURE_KEY)!="afterdark" or context.user_data.get(MODE_KEY)!="live":
        return
    live = _get_live_session()
    if not live: return
    sid = live[0]
    
    minutes = int(q.data.split(":")[-1])  # ad:extend:15 -> 15
    cost = minutes + 5  # 15min costs 20 coins
    
    if not reg.has_enough_coins(q.from_user.id, cost):
        return await q.message.reply_text(f"💰 Need {cost} coins to extend {minutes}m.\n/coins to buy more.")
    
    reg.deduct_coins(q.from_user.id, cost)
    _extend_session(sid, minutes)
    left = _ends_in_minutes(sid)
    
    await q.message.reply_text(f"⏳ Extended session by {minutes}m. Time left: {left:02d}:00")

async def ad_end_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if context.user_data.get(FEATURE_KEY)!="afterdark":
        return
    live = _get_live_session()
    if live:
        sid = live[0]
        _exec("UPDATE ad_sessions SET status='cancelled' WHERE id=%s", (sid,))
        await _broadcast(context, sid, "🚪 *Session ended by participant.*")
    
    clear_state(context)
    await q.message.reply_text("🚪 You left After Dark lounge.")

# =============== RELAY (TEXT + MEDIA TTL) ===============
async def ad_relay_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get(FEATURE_KEY)!="afterdark" or context.user_data.get(MODE_KEY)!="live":
        return
    live = _get_live_session()
    if not live: return
    sid = live[0]
    
    row = _exec("""SELECT anon_name FROM ad_participants
                   WHERE session_id=%s AND user_id=%s AND left_at IS NULL""",
                (sid, update.effective_user.id))
    anon = row[0][0] if row else f"{ANON_PREFIX}?"
    txt = update.effective_message.text or ""
    _log_ad_event(sid, update.effective_user.id, anon, "text", content=txt)
    
    # relay to others
    for uid in [u[0] for u in _list_participants(sid) if u[0]!=update.effective_user.id]:
        try:
            await context.bot.send_message(uid, f"**{anon}**: {txt}", parse_mode="Markdown")
        except Exception as e:
            log.debug(f"[AD] text relay fail: {e}")

async def ad_relay_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get(FEATURE_KEY)!="afterdark" or context.user_data.get(MODE_KEY)!="live":
        return
    live = _get_live_session()
    if not live: return
    sid = live[0]
    
    row = _exec("""SELECT anon_name FROM ad_participants
                   WHERE session_id=%s AND user_id=%s AND left_at IS NULL""",
                (sid, update.effective_user.id))
    anon = row[0][0] if row else f"{ANON_PREFIX}?"
    
    msg = update.effective_message
    media = msg.photo or msg.video or msg.document or msg.sticker
    if not media: return
    
    media_id = media[-1].file_id if isinstance(media, list) else media.file_id
    _log_ad_event(sid, update.effective_user.id, anon, "media", content=media_id)
    
    # relay with TTL
    for uid in [u[0] for u in _list_participants(sid) if u[0]!=update.effective_user.id]:
        try:
            sent = None
            if msg.photo:
                sent = await context.bot.send_photo(uid, media_id, caption=f"📸 {anon}", protect_content=True)
            elif msg.video:
                sent = await context.bot.send_video(uid, media_id, caption=f"🎥 {anon}", protect_content=True)
            elif msg.document:
                sent = await context.bot.send_document(uid, media_id, caption=f"📄 {anon}", protect_content=True)
            elif msg.sticker:
                sent = await context.bot.send_sticker(uid, media_id)
            
            if sent and AD_MEDIA_TTL_SEC > 0:
                _schedule_delete(context, sent.chat_id, sent.message_id, AD_MEDIA_TTL_SEC)
        except Exception as e:
            log.debug(f"[AD] media relay fail: {e}")

# =================== REGISTER ===================
def register(app):
    # Command
    app.add_handler(CommandHandler("afterdark", cmd_afterdark), group=AD_GROUP_LOBBY_PRIORITY)
    
    # Buttons
    app.add_handler(CallbackQueryHandler(ad_rules_cb,  pattern=r"^ad:rules$"),           group=AD_GROUP_LOBBY_PRIORITY)
    app.add_handler(CallbackQueryHandler(ad_enter_cb,  pattern=r"^ad:enter$"),           group=AD_GROUP_LOBBY_PRIORITY)
    app.add_handler(CallbackQueryHandler(ad_wheel_cb,  pattern=r"^ad:wheel$"),           group=AD_GROUP_LOBBY_PRIORITY)
    app.add_handler(CallbackQueryHandler(ad_extend_cb, pattern=r"^ad:extend:(\d+)$"),     group=AD_GROUP_LOBBY_PRIORITY)
    app.add_handler(CallbackQueryHandler(ad_end_cb,    pattern=r"^ad:end$"),             group=AD_GROUP_LOBBY_PRIORITY)
    
    # Wheel interactions
    app.add_handler(CallbackQueryHandler(ad_vote_cb,       pattern=r"^ad:vote:(wild|sweet)$"), group=AD_GROUP_LOBBY_PRIORITY)
    app.add_handler(CallbackQueryHandler(ad_truth_ans_cb,  pattern=r"^ad:truth:ans$"),         group=AD_GROUP_LOBBY_PRIORITY)
    app.add_handler(CallbackQueryHandler(ad_dare_done_cb,  pattern=r"^ad:dare:done$"),         group=AD_GROUP_LOBBY_PRIORITY)
    app.add_handler(CallbackQueryHandler(ad_drop_view_cb,  pattern=r"^ad:drop:view$"),         group=AD_GROUP_LOBBY_PRIORITY)
    
    # Truth text capture (slightly below relay so it wins when mode is 'truth_ans')
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ad_truth_text), group=AD_GROUP_RELAY_PRIORITY+1)
    
    # Relay (text + media) — high priority
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ad_relay_text), group=AD_GROUP_RELAY_PRIORITY)
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.Sticker.ALL, ad_relay_media), group=AD_GROUP_RELAY_PRIORITY)