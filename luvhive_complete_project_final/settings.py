
# settings.py
from typing import Tuple, Set, Dict, Any, List
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# --- Interests preview for Settings -----------------------------------------
# Keys are the internal interest keys you already use in the editor.
INTEREST_LABELS = {
    "chatting": "🐵 Chatting",
    "friends": "🌈 Friends",
    "relationship": "💞 Relationship", 
    "love": "❤️ Love",
    "games": "🎮 Games",
    "anime": "⚡ Anime",
    "intimate": "🚫 Intimate",
    "vsex": "😈 Virtual Sex", 
    "exchange": "🍓 Exchange",
}

def _load_user_interests_from_db(uid: int) -> set:
    """Load user's interests from database and return as set."""
    try:
        from registration import get_profile
        profile = get_profile(uid)
        return set(profile.get("interests", set()))
    except Exception:
        return set()

def _settings_interests_text(ud: dict) -> str:
    """
    Builds a nice one-line preview of the user's interests from user_data.
    Accepts list/set of keys OR a ready-made string (keeps it).
    """
    v = ud.get("interests")
    if not v:
        return "None"

    # If stored as a string already — show it as-is.
    if isinstance(v, str):
        return v

    # If list / set of keys — map to labels.
    keys = list(v) if isinstance(v, (list, set, tuple)) else []
    if not keys:
        return "None"

    labels = [INTEREST_LABELS.get(str(k).lower(), str(k).title()) for k in keys]
    return ", ".join(labels)

# Callback prefixes
CB_SETTINGS = "settings"
CB_INT      = f"{CB_SETTINGS}:int"
CB_AGE      = f"{CB_SETTINGS}:age"

# Note: Interests are now handled by registration.py to avoid duplication

AGE_OPTIONS = ["18-25", "25-30", "35-40", "45-50", "55-60", "18-99"]

PREMIUM_POPUP = "⚡⭐ To use this feature you must have a premium subscription."

def _get_user_settings(user_data: Dict[str, Any]) -> Dict[str, Any]:
    uid = user_data.get("user_id")
    age_pref = (18, 99)
    allow_forward = False

    if uid:
        try:
            from registration import _conn
            with _conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(min_age_pref,18),
                           COALESCE(max_age_pref,99),
                           COALESCE(allow_forward,FALSE)
                    FROM users WHERE tg_user_id=%s
                """, (uid,))
                row = cur.fetchone()
                if row:
                    age_pref = (int(row[0]), int(row[1]))
                    allow_forward = bool(row[2])
        except Exception:
            pass

    return {
        "interests": set(user_data.get("interests", [])),
        "show_media": bool(user_data.get("show_media", False)),
        "age_pref": age_pref,
        "allow_forward": allow_forward,
        "is_premium": bool(user_data.get("is_premium", False)),
    }

def settings_text(user_data: Dict[str, Any]) -> str:
    uid = user_data.get("user_id")

    # Defaults
    min_age, max_age = (18, 99)
    allow_fwd = bool(user_data.get("allow_forward", False))

    # ✅ If we know who the user is, read directly from DB
    if uid:
        try:
            from registration import get_age_pref, get_allow_forward
            min_age, max_age = get_age_pref(uid)
            allow_fwd = get_allow_forward(uid)
        except Exception:
            # fall back to old path if DB hiccups
            s = _get_user_settings(user_data)
            min_age, max_age = s["age_pref"]
            allow_fwd = s.get("allow_forward", allow_fwd)
    else:
        # Fallback only if user_id missing (shouldn't happen anymore)
        s = _get_user_settings(user_data)
        min_age, max_age = s["age_pref"]
        allow_fwd = s.get("allow_forward", allow_fwd)

    show_media = "Yes" if user_data.get("show_media") else "No"
    verified = "Yes" if user_data.get("is_verified") else "No"
    mvo = "ON" if user_data.get("match_verified_only") else "OFF"
    inc = "ON" if user_data.get("incognito") else "OFF"
    notify = "ON" if user_data.get("feed_notify", True) else "OFF"

    return (
        "⚙️ *Settings*\n"
        f"✔ *Verified:* {verified}\n"
        f"🛡 *Verified-only Match:* {mvo}\n"
        f"🕶 *Incognito (Hide profile link):* {inc}\n"
        f"🔔 *Feed Notifications:* {notify}\n"
        f"🚫 *Partner Age:* {min_age}-{max_age}\n"
        f"🚫 *Forwarding Messages:* {'Yes' if allow_fwd else 'No'}\n"
        f"🖼 *Show Photos/Videos:* {show_media} (Premium)\n"
        f"⭐ *Interests:* {_settings_interests_text(user_data)}"
    )

def settings_keyboard(user_data: Dict[str, Any]) -> InlineKeyboardMarkup:
    s = _get_user_settings(user_data)
    media_label = "✅ Show Photos and Videos (Premium)" if s["show_media"] else "☑️ Show Photos and Videos (Premium)"

    rows = [
        [InlineKeyboardButton("⭐ Edit Interests (Free)", callback_data=f"{CB_SETTINGS}:edit_interests")],
        [InlineKeyboardButton(media_label, callback_data=f"{CB_SETTINGS}:toggle_media")],
        [InlineKeyboardButton("👥 Partner Age (Premium)", callback_data=f"{CB_SETTINGS}:choose_age")],
        [InlineKeyboardButton("➡️ Allow Forwarding Messages (Premium)", callback_data=f"{CB_SETTINGS}:toggle_forward")],
        [InlineKeyboardButton("🛡 Verified-only Match (Premium)", callback_data=f"{CB_SETTINGS}:toggle_verifiedonly")],
        [InlineKeyboardButton("🕶 Incognito (Hide Profile Link)", callback_data=f"{CB_SETTINGS}:toggle_incognito")],
        [InlineKeyboardButton("🔔 Feed Notifications", callback_data=f"{CB_SETTINGS}:toggle_feednotify")],
    ]

    if user_data.get("is_verified"):
        rows.append([InlineKeyboardButton("✔ Verified", callback_data=f"{CB_SETTINGS}:noop")])
    else:
        rows.append([InlineKeyboardButton("✔️ Get Verified", callback_data=f"{CB_SETTINGS}:verify_menu")])

    return InlineKeyboardMarkup(rows)

# interests_keyboard() removed - now using registration.py selector

def age_keyboard(user_data: Dict[str, Any]) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for opt in AGE_OPTIONS:
        row.append(InlineKeyboardButton(opt, callback_data=f"{CB_AGE}:{opt}"))
        if len(row) == 3:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"{CB_SETTINGS}:back")])
    return InlineKeyboardMarkup(rows)

def parse_age_range(s: str) -> Tuple[int, int]:
    parts = s.split("-")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return int(parts[0]), int(parts[1])
    return (18, 99)
