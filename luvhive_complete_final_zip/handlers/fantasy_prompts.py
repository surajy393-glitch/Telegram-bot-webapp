# handlers/fantasy_prompts.py
from telegram.ext import ContextTypes, CommandHandler
from telegram import Update
from datetime import datetime
import random
import logging
import pytz

log = logging.getLogger("fantasy_prompts")

# IST timezone (consistent with your project)
IST = pytz.timezone("Asia/Kolkata")

# bot_data keys
PROMPT_JOBS = "fantasy_prompt_jobs"  # bot_data key: { match_id: job }
PROMPT_MODE_KEY = "fantasy_prompt_mode"   # "auto" | "weekday" | "weekend"

# weekend days: Saturday=5, Sunday=6
WEEKEND_DAYS = {5, 6}

# --- prompt bank (short, neutral, fun) ---
DEFAULT_PROMPTS = [
    "🎭 Roleplay warmup: You meet as strangers in a hotel lobby. Who breaks the ice?",
    "💬 One-liner: 'My wildest midnight idea is…'",
    "🕯️ Slow-burn: Describe the perfect room lighting in 5 words.",
    "🌧️ Rain scene: What's the first move in a downpour?",
    "🎧 Vibe check: Which song fits this moment?",
    "🗺️ Setting switch: Beach, balcony, elevator, or car—pick one and continue.",
    "⏳ 60-second story: Tell a tiny fantasy in 2 lines.",
    "💡 Truth: What detail turns you on instantly?",
    "🔥 Dare: Describe a kiss without using the word 'kiss'.",
    "✨ Memory lane: A moment you still replay, in one sentence."
]

# Optional: vibe-based pools (fallback to DEFAULT)
VIBE_PROMPTS = {
    "romantic": [
        "🕯️ Romantic scene: What's your ideal slow moment?",
        "💌 Whisper one sweet line you've always wanted to hear."
    ],
    "roleplay": [
        "🎭 Roleplay hook: Teacher & student, boss & intern, or strangers—pick one and start.",
        "🎭 Add a prop: glasses, notebook, or tie—how does it change the scene?"
    ],
    "wild": [
        "😈 Wild card: Describe a reckless move in 7 words.",
        "😏 Two words that feel forbidden together?"
    ],
    "adventure": [
        "🏔️ Outdoor spark: Night drive, hiking peak, or empty beach—continue the scene.",
        "🧭 'We took the wrong turn and…' finish it."
    ],
    "travel": [
        "🛫 Transit tease: Window seat or aisle—why?",
        "🏨 Hotel hallway moment—what's the vibe?"
    ],
    "intimate": [
        "🫶 Tender detail: Which touch says 'I'm home'?",
        "🕯️ Slow detail: Describe a breath in one sentence."
    ]
}

# merge the 30 extra prompts for weekends
EXTRA_PROMPTS = [
    # ❤️ Romantic Evening
    "🕯️ Describe the perfect candlelight setup in 5 words.",
    "💌 If you could send one love letter right now, what would its first line be?",
    "🌹 One song lyric that describes how you'd flirt?",
    "🥂 Imagine a slow dance — where are you and what's playing?",
    "💖 Write a compliment you've never dared to say aloud.",
    # 🎭 Roleplay Scenarios
    "🎭 Choose a role: teacher, stranger, boss — start the first line.",
    "🕶️ Add a prop to the roleplay: tie, glasses, notebook. How does it change the scene?",
    "📖 Fantasy script: *Scene 1, interior, night…* continue it.",
    "🎭 Which movie scene would you like to reenact together?",
    "💬 Role-swap: imagine being each other for 2 lines.",
    # 😈 Wild / Spontaneous
    "🔥 Describe the most reckless thought you've had in 7 words.",
    "😏 Quick challenge: two words that feel forbidden together?",
    "⚡ What's more thrilling: caught or almost caught?",
    "🚀 Fast fantasy: 'We had only 5 minutes…' finish it.",
    "💥 Admit one place you'd never expect but still imagine…",
    # 🏔️ Adventure / Outdoor
    "🏝️ Pick a setting: rooftop, beach, forest trail — why that one?",
    "🧭 Finish the line: *We took the wrong turn and…*",
    "🚗 Night drive vibe: which city, which song?",
    "⛺ If camping, what's the late-night fantasy twist?",
    "🌄 Sunrise challenge: describe in 1 sentence how you'd make it unforgettable.",
    # 🛫 Travel Dreams
    "🛫 Dream trip: first city you'd land in?",
    "🏨 Hotel hallway — what's the vibe?",
    "🌍 Bucket-list country + your wildest scene there?",
    "🚉 Station fantasy: strangers meeting by accident — your line?",
    "✈️ Window seat vs aisle — which and why?",
    # 🕯️ Intimate Moments
    "🫶 Which touch says 'I'm home' instantly?",
    "💭 Describe a breath without saying 'breath'.",
    "🤲 Imagine slow hands — which detail do they notice first?",
    "👀 Write one line starting with: *I crave…*",
    "🕯️ Tiny moment that feels bigger than any fantasy?"
]

def _bd(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.application.bot_data

def _jobs(context: ContextTypes.DEFAULT_TYPE) -> dict:
    bd = _bd(context)
    if PROMPT_JOBS not in bd:
        bd[PROMPT_JOBS] = {}
    return bd[PROMPT_JOBS]

def _is_weekend_now() -> bool:
    try:
        return datetime.now(IST).weekday() in WEEKEND_DAYS
    except Exception:
        # fallback without tz
        return datetime.now().weekday() in WEEKEND_DAYS

def _get_prompt_mode(context) -> str:
    """Returns 'auto'|'weekday'|'weekend' (default 'auto')."""
    bd = context.application.bot_data
    return (bd.get(PROMPT_MODE_KEY) or "auto").lower()

# Public helper functions for admin toggle
def get_prompt_mode(context) -> str:
    try:
        return (context.application.bot_data.get(PROMPT_MODE_KEY) or "auto").lower()
    except Exception:
        return "auto"

def set_prompt_mode(context, mode: str):
    if mode in ("auto", "weekday", "weekend"):
        context.application.bot_data[PROMPT_MODE_KEY] = mode

def _select_pool_for(vibe: str, context) -> list[str]:
    """
    Decide which pool to use:
    - auto: weekend → (vibe + DEFAULT + EXTRA), weekday → (vibe + DEFAULT)
    - weekend: always (vibe + DEFAULT + EXTRA)
    - weekday: always (vibe + DEFAULT)
    """
    mode = _get_prompt_mode(context)
    is_weekend = _is_weekend_now()
    base = VIBE_PROMPTS.get(vibe, []) + DEFAULT_PROMPTS

    use_extra = (mode == "weekend") or (mode == "auto" and is_weekend)
    return base + EXTRA_PROMPTS if use_extra else base

def _pick_prompt_for(vibe: str, context) -> str:
    pool = _select_pool_for(vibe, context)
    return random.choice(pool)

def _pick_prompt(vibe: str) -> str:
    pool = VIBE_PROMPTS.get(vibe, []) + DEFAULT_PROMPTS
    return random.choice(pool)

async def _send_prompt(context: ContextTypes.DEFAULT_TYPE):
    if not context.job or not context.job.data:
        return
    data = context.job.data
    mid  = data.get("match_id")
    u1   = data.get("u1")
    u2   = data.get("u2")
    vibe = data.get("vibe", "romantic")
    
    if not mid or not u1 or not u2:
        return

    text = "🎯 " + _pick_prompt_for(vibe, context)
    try:
        await context.bot.send_message(u1, text)
        await context.bot.send_message(u2, text)
    except Exception as e:
        log.warning(f"[prompts] send fail: {e}")

def _has_active_relay(context: ContextTypes.DEFAULT_TYPE, match_id: int) -> bool:
    # Optional: you can consult fantasy_relay's bot_data mapping if needed
    return True  # keep simple; schedule cancels from end hook

def start_prompts_for(context: ContextTypes.DEFAULT_TYPE, match_id: int, u1: int, u2: int, vibe: str, interval_sec: int = 180):
    """Schedule rotating prompts every N seconds during chat session."""
    jq = getattr(context, "job_queue", None)
    if not jq:
        return
    jobs = _jobs(context)
    # avoid duplicates
    if match_id in jobs:
        return
    jobs[match_id] = jq.run_repeating(
        _send_prompt, interval=interval_sec, first=interval_sec,
        data={"match_id": match_id, "u1": u1, "u2": u2, "vibe": vibe}
    )

def stop_prompts_for(context: ContextTypes.DEFAULT_TYPE, match_id: int):
    """Cancel prompt schedule for a match."""
    jobs = _jobs(context)
    try:
        j = jobs.pop(match_id, None)
        if j:
            j.schedule_removal()
    except Exception:
        pass

# (Optional) Admin command to force mode
async def cmd_fantasy_prompt_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.fantasy_common import reply_any, effective_uid
    
    uid = effective_uid(update)
    if uid is None:
        return await reply_any(update, context, "Could not identify user.")
    
    try:
        from admin import ADMIN_IDS
        if uid not in ADMIN_IDS:
            return await reply_any(update, context, "❌ Admin only command.")
    except ImportError:
        # Fallback if admin module not available
        return

    mode = (context.args[0].lower() if context.args and len(context.args) > 0 else "auto")
    if mode not in ("auto","weekday","weekend"):
        return await reply_any(update, context, "Usage: /fantasy_prompt_mode auto|weekday|weekend")

    context.application.bot_data[PROMPT_MODE_KEY] = mode
    await reply_any(update, context, f"✅ Prompt mode set to: {mode}")

def register_prompt_mode_command(app):
    app.add_handler(CommandHandler("fantasy_prompt_mode", cmd_fantasy_prompt_mode), group=0)