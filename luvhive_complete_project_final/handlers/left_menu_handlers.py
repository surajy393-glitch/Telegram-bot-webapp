
# handlers/left_menu_handlers.py
from __future__ import annotations
from typing import Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

import random
import registration as reg
import chat

# ⬇️ IMPORTANT: left_menu lives in the same package (handlers/)
# so we must use a relative import
from .left_menu import set_user_lang_menu, set_default_menu

# ===================== Language picker =====================
LANG_CB_EN = "lang_en"
LANG_CB_HI = "lang_hi"

# ===================== Chat helpers =====================
def _partner_id_of(uid: int) -> Optional[int]:
    """Return partner id if user is in a chat; else None (safe if chat module changes)."""
    try:
        pid = chat.peers.get(uid)  # dict: uid -> partner
        if isinstance(pid, tuple):
            a, b = pid
            pid = b if a == uid else a
        return pid if isinstance(pid, int) else None
    except Exception:
        return None

async def _silent_leave(uid: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    End current chat WITHOUT sending 'You left the chat'.
    Removes pair entries and politely pings the partner only.
    """
    try:
        partner = None
        if hasattr(chat, "peers") and isinstance(chat.peers, dict):
            partner = chat.peers.pop(uid, None)
            if partner:
                chat.peers.pop(partner, None)

        for name in ("waiting_users", "queue", "waiting"):
            w = getattr(chat, name, None)
            if w is not None:
                try:
                    if hasattr(w, "discard"):
                        w.discard(uid)
                    elif hasattr(w, "remove") and uid in w:
                        w.remove(uid)
                except Exception:
                    pass

        if partner:
            try:
                await context.bot.send_message(partner, "⚠️ Your partner left the chat.")
            except Exception:
                pass

        return True
    except Exception:
        return False

# ===================== Commands =====================

async def cmd_quit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/quit: end chat silently, then show Relax Mode on."""
    uid = update.effective_user.id
    left_ok = await _silent_leave(uid, context)
    if not left_ok:
        try:
            await chat.cmd_stop(update, context)  # best-effort fallback
        except Exception:
            pass
    await update.effective_message.reply_text("🧘 Relax Mode on")

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    reg.set_search_pref(uid, "any")   # reset to random
    await chat.start_search(update, context, mode="random")

async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(chat, "cmd_next"):
        await chat.cmd_next(update, context)
    else:
        await update.effective_message.reply_text("➡️ Use this inside a conversation.")

async def cmd_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /link: share *my* Telegram link with my current partner.
    - If I have @username -> send https://t.me/<username>
    - Else fallback to tg://user?id=<uid> and advise to set a username
    """
    uid = update.effective_user.id
    if reg.get_incognito(uid):
        return await update.effective_message.reply_text("🕶 Incognito ON: profile link sharing is disabled.")
    
    pid = _partner_id_of(uid)
    if not pid:
        await update.effective_message.reply_text("ℹ️ You have no partner. Type /search to find one.")
        return

    # Build sender's link
    me = update.effective_user
    uname = (me.username or "").strip()

    try:
        if uname:
            url = f"https://t.me/{uname}"
            # send my link to my partner
            await context.bot.send_message(
                chat_id=pid,
                text=f"🔗 Your partner shared their Telegram: {url}"
            )
            await update.effective_message.reply_text("✅ Sent your profile to your partner.")
        else:
            # no @username: fallback to tg:// link (works inside Telegram),
            # and encourage user to set a username for a prettier link
            url = f"tg://user?id={uid}"
            await context.bot.send_message(
                chat_id=pid,
                text=f"🔗 Your partner shared their Telegram (no @username set): {url}"
            )
            await update.effective_message.reply_text(
                "✅ Sent a contact link to your partner.\n"
                "💡 Tip: set an @username in Telegram settings for an easier link."
            )
    except Exception:
        await update.effective_message.reply_text("❗ Couldn't deliver the link to your partner right now.")

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[
        InlineKeyboardButton("🇺🇸 English", callback_data=LANG_CB_EN),
        InlineKeyboardButton("🇮🇳 हिंदी", callback_data=LANG_CB_HI),
    ]]
    await update.message.reply_text("Choose bot language:", reply_markup=InlineKeyboardMarkup(kb))

async def on_lang_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == LANG_CB_HI:
        # Hindi not yet supported
        try:
            await q.edit_message_text("🇮🇳 हिंदी — coming soon.")
        except Exception:
            await context.bot.send_message(chat_id=uid, text="🇮🇳 हिंदी — coming soon.")
        return

    if q.data == LANG_CB_EN:
        # English stays default
        await q.edit_message_text("🇺🇸 Language set to English.")

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("✅ All operations cancelled.")

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from settings import settings_text, settings_keyboard
    uid = update.effective_user.id
    profile = reg.get_profile(uid)
    context.user_data["interests"] = profile.get("interests", set())
    context.user_data["is_verified"] = bool(profile.get("is_verified", False))
    context.user_data.setdefault("show_media", False)
    context.user_data.setdefault("age_pref", (18, 99))
    context.user_data.setdefault("allow_forward", False)
    await update.effective_message.reply_text(
        settings_text(context.user_data),
        reply_markup=settings_keyboard(context.user_data),
        parse_mode="Markdown",
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "❓ How to use this bot:\n\n"
        "🔎 /search - Find a random chat partner\n"
        "➡️ /next - End current chat and find new partner\n"
        "🛑 /quit - End conversation and return to menu\n"
        "🔗 /link - Share your Telegram profile with partner\n"
        "🌐 /translate - Translate messages (reply to a message)\n"
        "🗑️ /cancel - Cancel current operation\n"
        "🤔 /truth - Get a truth question\n"
        "🎲 /dare - Get a dare challenge\n"
        "⚙️ /settings - Change your preferences\n"
        "💎 /premium - Manage VIP subscription\n"
        "🎫 /promocode - Use promo codes\n"
        "🪪 /myid - View your Telegram ID\n"
        "🎰 /spin - Try your luck (every 12h)\n"
        "🏆 /leaderboard - Top players\n"
        "💰 /paysupport - Payment support\n"
        "📜 /rules - Bot rules\n"
        "📄 /terms - Terms and conditions\n\n"
        "Have fun chatting! 😊"
    )

async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📜 Bot Rules - Do's and Don'ts:\n\n"
        "✅ DO:\n"
        "• Be respectful and kind\n"
        "• Have fun conversations\n"
        "• Report inappropriate behavior\n"
        "• Follow community guidelines\n"
        "• Use appropriate language\n\n"
        "❌ DON'T:\n"
        "• Share personal information (phone, address, etc.)\n"
        "• Send inappropriate content\n"
        "• Harass or bully other users\n"
        "• Spam or send repetitive messages\n"
        "• Use the bot for commercial purposes\n"
        "• Share illegal content\n\n"
        "⚠️ Violations may result in account suspension.\n"
        "Report issues using the report button during chats."
    )

async def cmd_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📄 Terms and Conditions:\n\n"
        "By using this bot, you agree to:\n\n"
        "1. Use the service responsibly and respectfully\n"
        "2. Not share personal information with strangers\n"
        "3. Report inappropriate behavior immediately\n"
        "4. Follow all bot rules and guidelines\n"
        "5. Accept that conversations are not monitored\n"
        "6. Understand that premium features require payment\n"
        "7. Allow us to process necessary data for functionality\n\n"
        "Privacy:\n"
        "• We don't store chat messages\n"
        "• User data is used only for bot functionality\n"
        "• Premium subscriptions are processed securely\n\n"
        "Disclaimer:\n"
        "• Use at your own risk\n"
        "• We're not responsible for user interactions\n"
        "• Users must be 18+ years old\n\n"
        "For support: /paysupport"
    )

async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from premium import premium_text, premium_kb
        await update.effective_message.reply_text(
            premium_text(), reply_markup=premium_kb(), parse_mode="Markdown"
        )
    except Exception:
        await update.effective_message.reply_text(
            "💎 Premium features include interest/gender matching and more."
        )

async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Your Telegram Information block (ID / Username / Name)."""
    u = update.effective_user
    uid = u.id
    uname = f"@{u.username}" if u.username else "—"
    name = (u.full_name or u.first_name or "—").strip()
    txt = (
        "🪪 Your Telegram Information:\n\n"
        f"User ID: <code>{uid}</code>\n"
        f"Username: {uname}\n"
        f"Name: {name}\n\n"
        "You can share your User ID for support purposes."
    )
    await update.effective_message.reply_text(txt, parse_mode="HTML")

async def cmd_paysupport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("💰 For payment help, message our support: @Luvhivehelpbot")

# --- Truth / Dare / Games ---------------------------------------------------

# ---------------------- TRUTH ----------------------
TRUTH_QS = [
    "What's your biggest fear?",
    "Have you ever lied to your parents?",
    "What's the most embarrassing thing you've done?",
    "Who was your first crush?",
    "Have you ever cheated in an exam?",
    "What's the biggest secret you've kept?",
    "What's your guilty pleasure?",
    "Have you ever stalked someone online?",
    "What's the weirdest dream you've had?",
    "Which friend do you trust the most?",
    "Have you ever lied to your partner?",
    "What's the worst habit you have?",
    "If you could change one thing in your life, what would it be?",
    "Have you ever spread a rumor?",
    "What's the most childish thing you still do?",
    "What's the most trouble you've been in at school?",
    "Have you ever been caught lying?",
    "Which family member annoys you most?",
    "What's the biggest lie you've told?",
    "Have you ever ghosted someone?",
    # 🌹 80 MORE NORMAL & SENSUAL TRUTH QUESTIONS 🌹
    "What's the most romantic thing someone has done for you?",
    "Have you ever had feelings for your best friend?",
    "What's your biggest turn-on in a conversation?",
    "Who was your most memorable kiss with?",
    "What's something you find irresistibly attractive?",
    "Have you ever flirted with someone just for fun?",
    "What's the sweetest compliment you've received?",
    "Do you believe in love at first sight?",
    "What's your ideal first date scenario?",
    "Have you ever written a love letter?",
    "What's the most butterflies you've felt for someone?",
    "Do you prefer cute nicknames or your real name?",
    "What's your biggest relationship dealbreaker?",
    "Have you ever confessed feelings and been rejected?",
    "What's the most attractive quality in a partner?",
    "Do you like holding hands in public?",
    "What's your love language?",
    "Have you ever been in love with two people at once?",
    "What's the longest you've waited for a text back?",
    "Do you prefer romantic surprises or planned gestures?",
    "What's your biggest fear in relationships?",
    "Have you ever stalked an ex on social media?",
    "What's the cutest thing about your personality?",
    "Do you get jealous easily?",
    "What's your perfect evening with someone special?",
    "Have you ever had a crush on a teacher?",
    "What's the most romantic movie that made you cry?",
    "Do you prefer texting or calling with your crush?",
    "What's your biggest insecurity about yourself?",
    "Have you ever pretended not to like someone you did?",
    "What's the best pickup line you've heard?",
    "Do you believe soulmates exist?",
    "What's your biggest turn-off in dating?",
    "Have you ever been heartbroken over unrequited love?",
    "What's the most thoughtful gift you've received?",
    "Do you fall in love easily or take time?",
    "What's your favorite thing about being in love?",
    "Have you ever had a long-distance relationship?",
    "What's the most romantic song for you?",
    "Do you prefer deep conversations or light chats?",
    "What's your biggest regret in love?",
    "Have you ever kissed someone on the first date?",
    "What's the sweetest thing you've done for someone?",
    "Do you get nervous around people you like?",
    "What's your idea of the perfect wedding?",
    "Have you ever been friend-zoned?",
    "What's the most attractive thing someone can wear?",
    "Do you prefer spontaneous or planned romance?",
    "What's your biggest fantasy about love?",
    "Have you ever dated someone friends didn't like?",
    "What's beautiful about being vulnerable?",
    "Do you believe in second chances in love?",
    "What's your favorite way to show affection?",
    "Have you ever been jealous of a friend's relationship?",
    "What's the most romantic place you've been?",
    "Do you prefer gentle touches or passionate embraces?",
    "What's your biggest dream for your love life?",
    "Have you ever cried over someone who hurt you?",
    "What's the most meaningful conversation you've had?",
    "Do you like being pursued or doing the pursuing?",
    "What's your favorite memory with someone special?",
    "Have you ever written poetry about someone?",
    "What's the most beautiful compliment you can give?",
    "Do you prefer morning cuddles or goodnight kisses?",
    "What's your biggest weakness when it comes to love?",
    "Have you ever fallen for someone wrong for you?",
    "What's the most romantic gesture you've witnessed?",
    "Do you believe timing matters in love?",
    "What's your favorite thing to do with someone you care about?",
    "Have you ever been scared to tell someone how you feel?",
    "What's the most attractive trait someone can have?",
    "Do you prefer slow dancing or passionate dancing?",
    "What's your ideal rainy day together?",
    "Have you ever felt butterflies from just a text?",
    "What's the most romantic thing you want to experience?",
    "Do you believe in fighting for love or letting go?",
    "What's your favorite love quote?",
    "Have you ever been attracted to someone's intelligence?",
    "What's the sweetest surprise you've planned?",
    "Do you prefer couple photos or private moments?",
    "What's your biggest hope for finding love?",
    "Have you ever been attracted to a friend's ex?",
    "What's beautiful about human connection?",
    "Do you prefer passionate love or comfortable love?",
    "What's your favorite way to be comforted?",
    "Have you ever felt like someone was 'the one'?",
    "What's the most romantic thing you've imagined?",
    "Do you believe love changes people for the better?",
    "What's your favorite thing about first kisses?",
    "Have you ever been attracted to someone's voice?",
    "What's the most meaningful gift you'd give?",
    "Do you prefer adventurous dates or cozy home dates?",
    "What's your biggest turn-on in personality?",
    "Have you ever felt love through just a look?",
    "What's beautiful about being understood?",
    "Do you prefer expressing love through words or actions?",
    "What's your favorite thing about romantic tension?",
    "Have you ever been attracted to someone's passion?",
    "What's the most romantic dream you've had?",
    "Do you believe love conquers all obstacles?",
    "What's your favorite way someone can make you smile?",
    "Have you ever felt instant chemistry with someone?",
    "What's beautiful about sharing secrets?",
    "Do you prefer subtle flirting or bold moves?",
    "What's your biggest desire in relationships?",
    "Have you ever been moved to tears by kindness?",
    "What's attractive about confidence?",
    "Do you believe in fairy tale love stories?",
    "What's your favorite way to show you care?"
]

async def cmd_truth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    pool = TRUTH_QS[:] + reg.get_all_questions("truth")
    q = random.choice(pool)
    txt = f"🤔 *Truth:* {q}"
    await update.effective_message.reply_text(txt, parse_mode="Markdown")
    pid = _partner_id_of(uid)
    if pid:
        try: 
            await context.bot.send_message(pid, txt, parse_mode="Markdown")
        except: 
            pass

# ---------------------- DARE ----------------------
DARE_QS = [
    "Send only emojis for the next 3 messages.",
    "Sing one line of a song in voice note.",
    "Send a funny selfie.",
    "Type without using space for one message.",
    "Pretend to be a teacher and scold your partner.",
    "Send 5 push-up challenge proof (photo/video).",
    "Say the alphabet backwards.",
    "Do 10 squats and send proof.",
    "Talk in rhyme for 3 messages.",
    "Send your favorite meme.",
    "Imitate your partner in text.",
    "Send 3 emojis that describe you.",
    "Tell your most awkward story.",
    "Make animal sounds in a voice note.",
    "Send a tongue twister and try to say it.",
    "Describe your day in only emojis.",
    "Compliment your partner creatively.",
    "Tell a joke in 1 line.",
    "Change your name to something funny for 10 min.",
    "Whisper a secret into voice note.",
    # 🌹 80 MORE ROMANTIC & SENSUAL DARE QUESTIONS 🌹
    "Send a voice note saying 'good morning beautiful' in your sexiest voice.",
    "Text your partner a romantic pickup line right now.",
    "Send a selfie with your most charming smile.",
    "Describe your ideal romantic date in exactly 10 words.",
    "Send a voice note whispering something sweet.",
    "Write a short love poem and send it.",
    "Send 3 heart emojis in different colors and explain what each means.",
    "Compliment your partner's eyes in a creative way.",
    "Send a photo of something that reminds you of romance.",
    "Describe your partner in 5 beautiful adjectives.",
    "Send a voice note humming a romantic song.",
    "Write 'I think you're amazing because...' and finish the sentence.",
    "Send a cute nickname you'd call your partner.",
    "Describe your perfect cuddle session in detail.",
    "Send a selfie making a kiss face.",
    "Tell your partner what you find most attractive about them.",
    "Send a voice note saying 'sweet dreams' seductively.",
    "Write a text like you're writing in their diary about them.",
    "Send 5 emojis that describe how you feel when you see them.",
    "Describe what you'd do on a rainy day together.",
    "Send a photo of your hands with a romantic message.",
    "Write a text as if you're leaving them a love note.",
    "Send a voice note with your most romantic laugh.",
    "Describe your favorite way to show affection.",
    "Send a selfie with something red (for love).",
    "Write what you'd say if you met them for the first time again.",
    "Send a voice note saying their name in the sweetest way.",
    "Describe your ideal 'us time' in 20 words.",
    "Send a photo that represents your mood when talking to them.",
    "Write a text about your favorite memory together (real or imagined).",
    "Send 3 reasons why you enjoy their company.",
    "Describe what 'home' feels like with them.",
    "Send a voice note with the most romantic word you know.",
    "Write what you'd put in a time capsule for them.",
    "Send a selfie showing your genuine happiness.",
    "Describe the perfect goodnight routine together.",
    "Send a text like you're introducing them to your friends.",
    "Write about a place you'd love to watch the sunset together.",
    "Send a voice note saying 'you make me smile' flirtatiously.",
    "Describe what makes your heart skip a beat.",
    "Send a photo of something beautiful and dedicate it to them.",
    "Write a message as if you're texting them good luck before something important.",
    "Send 3 things you appreciate about their personality.",
    "Describe your ideal Saturday morning together.",
    "Send a voice note with your most charming 'hello'.",
    "Write what you'd say in a toast about them.",
    "Send a selfie that shows your most attractive feature.",
    "Describe what you think their love language might be.",
    "Send a text about your favorite type of conversation with them.",
    "Write what you'd say if you could only send one message ever.",
    "Send a voice note humming while thinking of them.",
    "Describe what you find most intriguing about them.",
    "Send a photo that represents your ideal vibe together.",
    "Write a compliment about their mind.",
    "Send 3 emojis that represent your perfect date.",
    "Describe what you'd cook for them if you could.",
    "Send a voice note saying 'you're incredible' with feeling.",
    "Write about a simple moment that would make you happy together.",
    "Send a selfie with the lighting that makes you look most attractive.",
    "Describe what you'd want them to know about you.",
    "Send a text about your favorite way to spend quality time.",
    "Write what you'd say if you could read their mind right now.",
    "Send a voice note with your most genuine laugh.",
    "Describe what adventure you'd want to share together.",
    "Send a photo of your smile just for them.",
    "Write a message like you're planning a surprise for them.",
    "Send 3 words that describe how they make you feel.",
    "Describe your perfect evening walk together.",
    "Send a voice note saying 'thinking of you' romantically.",
    "Write what you'd put on a billboard for them to see.",
    "Send a selfie showing your most confident expression.",
    "Describe what you think would make them laugh.",
    "Send a text about what makes them special.",
    "Write about a song that reminds you of them.",
    "Send a voice note with your best flirty voice saying 'hey gorgeous'.",
    "Describe what you'd want to protect about them.",
    "Send a photo of something that matches their energy.",
    "Write what you'd say if you were giving them a pep talk.",
    "Send 3 things you'd want to experience together.",
    "Describe what you find most admirable about them.",
    "Send a voice note saying 'you're special' with emotion.",
    "Write a text like you're bragging about them to someone else.",
    "Send a selfie that shows your most genuine expression.",
    "Describe what perfect communication looks like to you.",
    "Send a message about what you'd want them to remember about today.",
    "Write what you'd say if you were introducing them to your family.",
    "Send a voice note with your most attractive laugh.",
    "Describe what you think their best quality is.",
    "Send a photo that represents how they make you feel.",
    "Write about what you'd want to celebrate with them.",
    "Send 3 reasons why someone would be lucky to know them.",
    "Describe your ideal way to comfort them.",
    "Send a voice note saying 'you matter' meaningfully.",
    "Write what you'd say if you were writing their horoscope.",
    "Send a selfie that captures your happiest mood.",
    "Describe what you'd want to learn from them.",
    "Send a text about what makes them unforgettable.",
    "Write what you'd say if you could give them one gift.",
    "Send a voice note with your most sincere 'thank you'.",
    "Describe what you think they deserve in life.",
    "Send a photo that represents your ideal energy together.",
    "Write a message about what makes them irreplaceable.",
    "Send 3 hopes you have for their happiness.",
    "Describe what you'd want them to feel proud of.",
    "Send a voice note saying 'you're amazing' with your whole heart."
]

async def cmd_dare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    pool = DARE_QS[:] + reg.get_all_questions("dare")
    q = random.choice(pool)
    txt = f"🎲 *Dare:* {q}"
    await update.effective_message.reply_text(txt, parse_mode="Markdown")
    pid = _partner_id_of(uid)
    if pid:
        try: 
            await context.bot.send_message(pid, txt, parse_mode="Markdown")
        except: 
            pass

# ---------------------- WYR ----------------------
WYR_QS = [
    "Would you rather be invisible or fly?",
    "Would you rather never use Instagram or never use YouTube?",
    "Would you rather have more time or more money?",
    "Would you rather always be early or always be late?",
    "Would you rather give up sweets or give up tea/coffee?",
    "Would you rather live without music or live without games?",
    "Would you rather be famous online or respected offline?",
    "Would you rather travel the world or get ₹10 lakh now?",
    "Would you rather pause time or rewind 5 minutes?",
    "Would you rather always have red lights or always slow internet?",
    "Would you rather live on the beach or in the mountains?",
    "Would you rather be able to talk to animals or speak all languages?",
    "Would you rather be strongest or smartest?",
    "Would you rather never take exams again or never have homework?",
    "Would you rather always be hungry or always be tired?",
    "Would you rather win true love or win ₹50 lakh?",
    "Would you rather teleport anywhere or read minds?",
    "Would you rather lose ability to read or to speak?",
    "Would you rather watch movies forever or series forever?",
    "Would you rather never use social media or never watch movies?",
    # 🌹 80 MORE ROMANTIC & SENSUAL WYR QUESTIONS 🌹
    "Would you rather receive a love letter or a romantic poem?",
    "Would you rather have a candlelit dinner or a sunset picnic?",
    "Would you rather be serenaded or have someone write you a song?",
    "Would you rather hold hands everywhere or exchange cute nicknames?",
    "Would you rather have deep conversations or playful banter?",
    "Would you rather receive flowers unexpectedly or thoughtful little gifts?",
    "Would you rather have a rainy day together inside or a sunny day outside?",
    "Would you rather dance slowly or laugh together uncontrollably?",
    "Would you rather have someone cook for you or cook together?",
    "Would you rather receive morning texts or goodnight calls?",
    "Would you rather share your biggest dreams or your childhood memories?",
    "Would you rather be surprised with a date or plan one together?",
    "Would you rather have breakfast in bed or dinner under the stars?",
    "Would you rather exchange daily compliments or weekly love notes?",
    "Would you rather have a partner who's funny or deeply romantic?",
    "Would you rather travel together or create a cozy home together?",
    "Would you rather have someone remember every detail about you or surprise you constantly?",
    "Would you rather share a warm embrace or a passionate kiss?",
    "Would you rather have a partner who's your best friend or your greatest adventure?",
    "Would you rather write love letters or create a photo album together?",
    "Would you rather have matching outfits or complementary styles?",
    "Would you rather spend a day talking or a day in comfortable silence?",
    "Would you rather have a partner who challenges you or comforts you?",
    "Would you rather receive a single red rose or a bouquet of your favorite flowers?",
    "Would you rather have someone serenade you or dedicate a song to you?",
    "Would you rather slow dance in the kitchen or waltz in a ballroom?",
    "Would you rather have a partner who's spontaneous or thoughtfully planned?",
    "Would you rather share a cup of coffee or a glass of wine?",
    "Would you rather have a weekend getaway or a staycation with someone special?",
    "Would you rather receive a heartfelt compliment or a gentle touch?",
    "Would you rather have deep eye contact or sweet whispered conversations?",
    "Would you rather be someone's first thought in the morning or last thought at night?",
    "Would you rather have a partner who's protective or supportive?",
    "Would you rather share secrets under the stars or over morning coffee?",
    "Would you rather have someone play with your hair or hold your hand?",
    "Would you rather receive a surprise visit or a planned romantic evening?",
    "Would you rather have a partner who's artistic or intellectually stimulating?",
    "Would you rather share a warm blanket or a cool evening breeze together?",
    "Would you rather have someone who remembers your favorite things or discovers new things about you?",
    "Would you rather be wooed with words or actions?",
    "Would you rather have a cozy movie night or an elegant dinner date?",
    "Would you rather receive daily affirmations or weekly romantic gestures?",
    "Would you rather have a partner who's confident or humble?",
    "Would you rather share a meaningful conversation or a fun activity?",
    "Would you rather have someone who's emotionally available or physically affectionate?",
    "Would you rather receive handwritten notes or voice messages?",
    "Would you rather have a partner who's adventurous in love or traditional in romance?",
    "Would you rather share a first dance or a first kiss?",
    "Would you rather have someone who's your emotional anchor or your inspiration?",
    "Would you rather be courted with flowers or with thoughtful gestures?",
    "Would you rather have a partner who's expressive or mysteriously attractive?",
    "Would you rather share a meaningful glance or a heartfelt laugh?",
    "Would you rather have someone who's passionate about life or peaceful in nature?",
    "Would you rather receive compliments about your appearance or your personality?",
    "Would you rather have a partner who's your safe space or your exciting adventure?",
    "Would you rather share intimate conversations or playful moments?",
    "Would you rather have someone who's devoted or independent but caring?",
    "Would you rather be surprised with breakfast or serenaded at dinner?",
    "Would you rather have a partner who's emotionally intelligent or romantically creative?",
    "Would you rather share a quiet moment or an enthusiastic celebration?",
    "Would you rather have someone who's gentle and caring or bold and passionate?",
    "Would you rather receive a love poem or a heartfelt speech?",
    "Would you rather have a partner who's your cheerleader or your calming presence?",
    "Would you rather share a meaningful gift exchange or a simple quality time?",
    "Would you rather have someone who's attentive to details or grand in gestures?",
    "Would you rather be loved for who you are or inspired to become better?",
    "Would you rather have a partner who's emotionally expressive or physically affectionate?",
    "Would you rather share a romantic walk or a cozy cuddle session?",
    "Would you rather have someone who's your missing piece or your perfect complement?",
    "Would you rather receive surprise love notes or planned romantic evenings?",
    "Would you rather have a partner who's your confidant or your adventure buddy?",
    "Would you rather share a meaningful tradition or create new memories?",
    "Would you rather have someone who's consistently loving or surprisingly romantic?",
    "Would you rather be someone's priority or their inspiration?",
    "Would you rather have a partner who's emotionally supportive or motivationally encouraging?",
    "Would you rather share sweet dreams together or wake up to loving messages?",
    "Would you rather have someone who's your peace or your excitement?",
    "Would you rather receive thoughtful surprises or consistent affection?",
    "Would you rather have a partner who's your comfort zone or your growth catalyst?",
    "Would you rather share vulnerable moments or joyful celebrations?",
    "Would you rather have someone who's romantically traditional or creatively expressive?",
    "Would you rather be loved through words of affirmation or acts of service?",
    "Would you rather have a partner who's your best friend or your passionate lover?",
    "Would you rather share everyday moments or special occasions?",
    "Would you rather have someone who's predictably loving or spontaneously romantic?",
    "Would you rather receive morning kisses or evening embraces?",
    "Would you rather have a partner who's your emotional sanctuary or your exciting challenge?",
    "Would you rather share deep intimacy or playful connection?",
    "Would you rather have someone who loves your flaws or helps you grow?",
    "Would you rather be in a love that's comfortable or thrilling?",
    "Would you rather have a partner who's your soulmate or your perfect match?",
    "Would you rather share a lifetime of small moments or a few perfect memories?",
    "Would you rather have someone who's devoted to you or inspires your devotion?",
    "Would you rather receive gentle touches or passionate embraces?",
    "Would you rather have a love that's steady and secure or intense and transformative?",
    "Would you rather share everything with someone or keep some mystery alive?",
    "Would you rather have a partner who completes you or complements you?",
    "Would you rather be loved exactly as you are or loved for who you're becoming?",
    "Would you rather have a relationship that's your safe haven or your greatest adventure?",
    "Would you rather share a love that grows slowly or ignites instantly?",
    "Would you rather have someone who's your home or your journey?",
    "Would you rather be in a love story that's beautifully simple or passionately complex?",
    "Would you rather have a partner who's your missing half or your perfect whole?",
    "Would you rather share a love that's whispered softly or declared boldly?"
]

async def cmd_wyr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    pool = WYR_QS[:] + reg.get_all_questions("wyr")
    q = random.choice(pool)
    txt = f"🌀 *Would You Rather:* {q}"
    await update.effective_message.reply_text(txt, parse_mode="Markdown")
    pid = _partner_id_of(uid)
    if pid:
        try: 
            await context.bot.send_message(pid, txt, parse_mode="Markdown")
        except: 
            pass

# ---------------------- NHIE ----------------------
NHIE_QS = [
    "Never have I ever cheated in an exam.",
    "Never have I ever stalked my ex online.",
    "Never have I ever fallen asleep in class.",
    "Never have I ever lied to my best friend.",
    "Never have I ever ghosted someone.",
    "Never have I ever used someone else's Netflix.",
    "Never have I ever cried in public.",
    "Never have I ever lied in Truth or Dare.",
    "Never have I ever skipped homework.",
    "Never have I ever fake laughed at a bad joke.",
    "Never have I ever lied about my marks.",
    "Never have I ever broken a promise.",
    "Never have I ever stayed up all night chatting.",
    "Never have I ever ignored a message on purpose.",
    "Never have I ever pretended to be sick to skip school.",
    "Never have I ever bragged about something I didn't do.",
    "Never have I ever sent a message to the wrong person.",
    "Never have I ever stalked a crush online.",
    "Never have I ever sung loudly in the shower.",
    "Never have I ever laughed until I cried.",
    # 🌹 80 MORE ROMANTIC & SENSUAL NHIE QUESTIONS 🌹
    "Never have I ever written a love letter to someone.",
    "Never have I ever had butterflies from just a text message.",
    "Never have I ever fallen asleep thinking about someone special.",
    "Never have I ever looked forward to seeing someone all day.",
    "Never have I ever felt my heart skip a beat when someone smiled at me.",
    "Never have I ever stayed up late talking to my crush.",
    "Never have I ever dreamed about someone I have feelings for.",
    "Never have I ever felt nervous before a date.",
    "Never have I ever blushed because of a compliment.",
    "Never have I ever saved screenshots of sweet messages.",
    "Never have I ever written someone's name in my diary.",
    "Never have I ever felt jealous seeing my crush with someone else.",
    "Never have I ever daydreamed about my future with someone.",
    "Never have I ever felt tingles from holding hands.",
    "Never have I ever gotten excited about a good morning text.",
    "Never have I ever felt disappointed when someone didn't text back.",
    "Never have I ever looked up my crush's horoscope compatibility.",
    "Never have I ever felt my cheeks get warm from flirting.",
    "Never have I ever stayed awake wondering what someone was thinking.",
    "Never have I ever felt like time stopped during a perfect moment.",
    "Never have I ever written a poem about someone I liked.",
    "Never have I ever felt nervous about saying 'I love you' first.",
    "Never have I ever practiced conversations in my head before talking to my crush.",
    "Never have I ever felt my stomach flutter during a romantic movie.",
    "Never have I ever wanted to hold someone's hand during a movie.",
    "Never have I ever felt like someone could read my mind through my eyes.",
    "Never have I ever been nervous about meeting someone's friends.",
    "Never have I ever felt like I was floating after a perfect kiss.",
    "Never have I ever wanted to slow dance with someone special.",
    "Never have I ever felt protective over someone I cared about.",
    "Never have I ever planned what I'd say in a love confession.",
    "Never have I ever felt like someone was meant to be in my life.",
    "Never have I ever wanted to surprise someone with their favorite flowers.",
    "Never have I ever felt complete when hugging someone special.",
    "Never have I ever lost track of time while talking to someone I liked.",
    "Never have I ever felt like I could tell someone anything.",
    "Never have I ever wanted to wake up next to someone special.",
    "Never have I ever felt my heart race from just hearing someone's voice.",
    "Never have I ever wanted to cook something special for someone I cared about.",
    "Never have I ever felt like someone's laugh was the most beautiful sound.",
    "Never have I ever wanted to travel the world with someone special.",
    "Never have I ever felt like I could be completely myself with someone.",
    "Never have I ever wanted to give someone the world.",
    "Never have I ever felt like someone's presence calmed me down.",
    "Never have I ever wanted to memorize every detail of someone's face.",
    "Never have I ever felt like someone understood me without words.",
    "Never have I ever wanted to be someone's safe space.",
    "Never have I ever felt like someone made me a better person.",
    "Never have I ever wanted to share all my secrets with someone.",
    "Never have I ever felt like someone's touch was healing.",
    "Never have I ever wanted to grow old with someone special.",
    "Never have I ever felt like someone was my missing puzzle piece.",
    "Never have I ever wanted to be someone's first and last thought of the day.",
    "Never have I ever felt like someone's love could conquer anything.",
    "Never have I ever wanted to write our story together.",
    "Never have I ever felt like someone was my home.",
    "Never have I ever wanted to protect someone's heart.",
    "Never have I ever felt like I could love someone forever.",
    "Never have I ever wanted to be someone's greatest love story.",
    "Never have I ever felt like someone was worth waiting for.",
    "Never have I ever wanted to make someone feel like royalty.",
    "Never have I ever felt like someone's happiness was my priority.",
    "Never have I ever wanted to be the reason someone smiles.",
    "Never have I ever felt like someone made ordinary moments magical.",
    "Never have I ever wanted to be someone's always and forever.",
    "Never have I ever felt like someone was my greatest adventure.",
    "Never have I ever wanted to be someone's comfort and joy.",
    "Never have I ever felt like someone completed my soul.",
    "Never have I ever wanted to be someone's sweet escape.",
    "Never have I ever felt like someone was my heart's desire.",
    "Never have I ever wanted to be someone's dreams come true.",
    "Never have I ever felt like someone was my perfect match.",
    "Never have I ever wanted to be someone's happily ever after.",
    "Never have I ever felt like someone was my destiny.",
    "Never have I ever wanted to love someone with all my heart.",
    "Never have I ever felt like someone was my everything.",
    "Never have I ever wanted to be someone's reason to believe in love.",
    "Never have I ever felt like someone was my miracle.",
    "Never have I ever wanted to be someone's greatest blessing.",
    "Never have I ever felt like someone was my answered prayer.",
    "Never have I ever wanted to be someone's sweetest dream.",
    "Never have I ever felt like someone was my heart's home.",
    "Never have I ever wanted to be someone's most precious treasure.",
    "Never have I ever felt like someone was my soul's recognition.",
    "Never have I ever wanted to be someone's infinite love.",
    "Never have I ever felt like someone was my heart's symphony.",
    "Never have I ever wanted to be someone's eternal spring.",
    "Never have I ever felt like someone was my life's greatest gift.",
    "Never have I ever wanted to be someone's most beautiful story.",
    "Never have I ever felt like someone was my heart's deepest truth.",
    "Never have I ever wanted to be someone's most cherished memory.",
    "Never have I ever felt like someone was my soul's perfect harmony.",
    "Never have I ever wanted to be someone's most radiant sunshine.",
    "Never have I ever felt like someone was my heart's sweetest song.",
    "Never have I ever wanted to be someone's most gentle love.",
    "Never have I ever felt like someone was my spirit's twin flame.",
    "Never have I ever wanted to be someone's most sacred promise.",
    "Never have I ever felt like someone was my heart's truest compass.",
    "Never have I ever wanted to be someone's most beautiful beginning.",
    "Never have I ever felt like someone was my soul's deepest connection.",
    "Never have I ever wanted to be someone's most perfect love story.",
    "Never have I ever felt like someone was my heart's greatest treasure.",
    "Never have I ever wanted to be someone's most beautiful forever.",
    "Never have I ever felt like someone made me believe in magic again."
]

async def cmd_nhie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    pool = NHIE_QS[:] + reg.get_all_questions("nhie")
    q = random.choice(pool)
    txt = f"🙅 *Never Have I Ever:* {q}"
    await update.effective_message.reply_text(txt, parse_mode="Markdown")
    pid = _partner_id_of(uid)
    if pid:
        try: 
            await context.bot.send_message(pid, txt, parse_mode="Markdown")
        except: 
            pass

# ---------------------- KMK ----------------------
KMK_QS = [
    "Virat Kohli, MS Dhoni, Rohit Sharma",
    "Deepika Padukone, Alia Bhatt, Katrina Kaif",
    "Shah Rukh Khan, Salman Khan, Aamir Khan",
    "Batman, Superman, Spider-Man",
    "Iron Man, Thor, Hulk",
    "Harry Potter, Hermione, Ron Weasley",
    "Naruto, Sasuke, Sakura",
    "Tom, Jerry, Oggy",
    "Barbie, Ken, Elsa",
    "Mickey, Donald, Goofy",
    "Pikachu, Bulbasaur, Charmander",
    "BTS Jungkook, BTS V, BTS Jimin",
    "Taylor Swift, Selena Gomez, Ariana Grande",
    "Cristiano Ronaldo, Lionel Messi, Neymar",
    "Google, Apple, Microsoft",
    "PUBG, Free Fire, COD Mobile",
    "Pizza, Burger, Pasta",
    "iPhone, Samsung, OnePlus",
    "TikTok, Instagram, Snapchat",
    "Prime Minister Modi, Rahul Gandhi, Arvind Kejriwal",
    # 🌹 80 MORE ROMANTIC & SENSUAL KMK OPTIONS 🌹
    "Ryan Gosling, Michael B. Jordan, Chris Evans",
    "Emma Stone, Margot Robbie, Scarlett Johansson",
    "Zendaya, Timothée Chalamet, Tom Holland",
    "Morning kisses, Goodnight hugs, Afternoon cuddles",
    "Love letters, Voice messages, Surprise visits",
    "Candlelit dinner, Beach picnic, Rooftop date",
    "Slow dancing, Hand holding, Forehead kisses",
    "Red roses, Handwritten notes, Surprise flowers",
    "Coffee dates, Wine evenings, Tea mornings",
    "Rain walks, Sunset views, Stargazing",
    "Cooking together, Reading together, Dancing together",
    "French accent, British accent, Italian accent",
    "Deep conversations, Playful banter, Comfortable silence",
    "Warm hugs, Gentle touches, Sweet whispers",
    "First date butterflies, Anniversary celebrations, Random surprises",
    "Love poems, Song dedications, Photo memories",
    "Morning texts, Lunch calls, Goodnight stories",
    "Adventure trips, Cozy nights, Romantic getaways",
    "Shared hobbies, New experiences, Quiet moments",
    "Thoughtful gifts, Quality time, Words of affirmation",
    "Breakfast in bed, Dinner under stars, Lunch in the park",
    "Matching outfits, Complementary styles, Individual expression",
    "Long drives, Walking together, Staying home",
    "Funny partners, Romantic partners, Intellectual partners",
    "Spontaneous dates, Planned surprises, Regular routines",
    "Physical affection, Emotional support, Mental stimulation",
    "Early mornings together, Lazy afternoons, Late night talks",
    "Adventure seeking, Home building, Memory making",
    "Passionate love, Comfortable love, Growing love",
    "Weekend getaways, Staycations, Daily adventures",
    "Love songs, Romantic movies, Poetry readings",
    "Gentle personalities, Bold personalities, Mysterious personalities",
    "Artistic souls, Athletic bodies, Intelligent minds",
    "Protective nature, Supportive nature, Inspiring nature",
    "Confident charm, Humble sweetness, Playful energy",
    "Deep eyes, Warm smile, Gentle voice",
    "Strong hands, Soft touch, Caring embrace",
    "Morning energy, Evening calmness, Midnight passion",
    "Outdoor adventures, Indoor comfort, City exploration",
    "Traditional romance, Modern dating, Unique courtship",
    "Written words, Spoken promises, Silent understanding",
    "First kisses, Last kisses, Unexpected kisses",
    "Dreamy dates, Practical plans, Spontaneous moments",
    "Emotional depth, Physical attraction, Mental connection",
    "Future building, Present enjoying, Memory cherishing",
    "Heart racing, Soul calming, Mind inspiring",
    "Forever promises, Daily choices, Moment treasuring",
    "Love languages, Inside jokes, Shared dreams",
    "Romantic gestures, Thoughtful actions, Simple presence",
    "Couple goals, Individual growth, Shared adventures",
    "Sweet surprises, Consistent love, Passionate moments",
    "Date nights, Home evenings, Adventure days",
    "Love stories, Real life, Future dreams",
    "Emotional intimacy, Physical closeness, Mental bonding",
    "Gentle romance, Passionate love, Playful affection",
    "Morning person, Night owl, Anytime lover",
    "Beach vacations, Mountain retreats, City breaks",
    "Love at first sight, Growing affection, Developed feelings",
    "Handwritten letters, Digital messages, Spoken words",
    "Surprise visits, Planned meetings, Accidental encounters",
    "Roses and chocolates, Simple gestures, Grand surprises",
    "Sharing secrets, Making memories, Building futures",
    "Cozy winters, Sunny summers, Romantic springs",
    "Dancing partners, Walking companions, Talking friends",
    "Heart connections, Soul bonds, Mind meetings",
    "Love confessions, Silent understanding, Obvious attraction",
    "Perfect timing, Right person, Beautiful moments",
    "Relationship goals, Personal growth, Shared values",
    "Romantic dinners, Casual dates, Adventure activities",
    "Love quotes, Personal poetry, Heartfelt speeches",
    "Gentle touches, Warm embraces, Passionate kisses",
    "Future planning, Present living, Memory making",
    "Emotional support, Physical comfort, Mental stimulation",
    "Daily texts, Weekly calls, Monthly visits",
    "Love languages, Communication styles, Affection types",
    "Morning coffee, Evening wine, Midnight snacks",
    "Shared laughter, Comfortable silence, Deep conversations",
    "Adventure seeking, Peace finding, Joy creating",
    "Heart melting, Soul touching, Mind blowing",
    "Love stories, Fairy tales, Real relationships",
    "First dates, Anniversary celebrations, Random Tuesdays",
    "Sunset watching, Star counting, Cloud gazing",
    "Love notes, Voice messages, Picture memories",
    "Gentle souls, Passionate hearts, Beautiful minds",
    "Forever love, Present moment, Beautiful journey",
    "Romantic comedy, Love drama, Passion story",
    "Sweet dreams, Morning smiles, Evening embraces",
    "Heart songs, Soul dances, Mind symphonies",
    "Love whispers, Laughter echoes, Silence speaks",
    "Beautiful beginnings, Sweet middles, Perfect endings"
]

async def cmd_kmk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    pool = KMK_QS[:] + reg.get_all_questions("kmk")
    q = random.choice(pool)
    txt = f"💋 *Kiss, Marry, Kill:*\nChoose between: {q}"
    await update.effective_message.reply_text(txt, parse_mode="Markdown")
    pid = _partner_id_of(uid)
    if pid:
        try: 
            await context.bot.send_message(pid, txt, parse_mode="Markdown")
        except: 
            pass

# ---------------------- THIS or THAT ----------------------
TOT_QS = [
    "Coffee ☕ or Tea 🍵?",
    "Mountains 🏔 or Beach 🏖?",
    "Pizza 🍕 or Burger 🍔?",
    "iOS 📱 or Android 🤖?",
    "Morning 🌅 or Night 🌙?",
    "Summer ☀️ or Winter ❄️?",
    "Car 🚗 or Bike 🏍?",
    "City 🏙 or Village 🌾?",
    "Football ⚽ or Cricket 🏏?",
    "Comedy 😂 or Horror 👻?",
    "Online Shopping 🛒 or Offline 🏬?",
    "Book 📚 or Movie 🎥?",
    "Cat 🐱 or Dog 🐶?",
    "Instagram 📸 or Twitter 🐦?",
    "Chatting 💬 or Call 📞?",
    "Money 💰 or Love ❤️?",
    "Long drive 🚗 or Long walk 🚶?",
    "Chocolate 🍫 or Ice Cream 🍦?",
    "Dance 💃 or Singing 🎤?",
    "PC 🖥 or Console 🎮?",
    # 🌹 80 MORE ROMANTIC & SENSUAL THIS OR THAT QUESTIONS 🌹
    "Love letters 💌 or Voice messages 🎤?",
    "Candlelit dinner 🕯️ or Sunset picnic 🌅?",
    "Morning cuddles 🤗 or Goodnight kisses 😘?",
    "Slow dancing 💃 or Hand holding 🤝?",
    "Deep conversations 💭 or Comfortable silence 🤫?",
    "Surprise dates 🎁 or Planned romance 📅?",
    "Red roses 🌹 or Handwritten notes 📝?",
    "Coffee dates ☕ or Wine evenings 🍷?",
    "Beach walks 🏖️ or Rain dancing 🌧️?",
    "Sweet whispers 🗣️ or Gentle touches 👋?",
    "Adventure trips 🎒 or Cozy nights 🏠?",
    "Love poems 📖 or Song dedications 🎵?",
    "Morning texts 📱 or Goodnight calls 📞?",
    "Shared hobbies 🎨 or New experiences 🌟?",
    "Physical affection 🤗 or Words of affirmation 💬?",
    "Breakfast in bed 🛏️ or Dinner under stars ⭐?",
    "Matching outfits 👫 or Individual styles 👤?",
    "Spontaneous romance 💫 or Traditional courtship 👑?",
    "Future planning 📋 or Living in the moment ⏰?",
    "Heart racing 💓 or Soul calming 🧘?",
    "Passionate love 🔥 or Gentle affection 🌸?",
    "Weekend getaways ✈️ or Daily adventures 🚶?",
    "Love songs 🎶 or Romantic movies 🎬?",
    "Confident partners 😎 or Humble souls 😊?",
    "Artistic dates 🎨 or Outdoor activities 🌳?",
    "Emotional intimacy 💝 or Physical closeness 🤗?",
    "First date butterflies 🦋 or Anniversary celebrations 🎉?",
    "Written words 📝 or Spoken promises 🗣️?",
    "Dreamy romance 💭 or Practical love 🔧?",
    "Heart connections 💖 or Mind meetings 🧠?",
    "Forever promises 💍 or Daily choices ☀️?",
    "Love at first sight 👀 or Growing affection 🌱?",
    "Romantic gestures 💐 or Simple presence 🧘?",
    "Sweet surprises 🎁 or Consistent love 💝?",
    "Date nights 🌙 or Home evenings 🏠?",
    "Love stories 📚 or Real moments 📸?",
    "Gentle souls 😇 or Passionate hearts 🔥?",
    "Morning person ☀️ or Night owl 🌙?",
    "Beach romance 🏖️ or Mountain love ⛰️?",
    "Handwritten letters ✍️ or Digital messages 📱?",
    "Surprise visits 🚪 or Planned meetings 📅?",
    "Grand gestures 🎭 or Small tokens 🎁?",
    "Secret sharing 🤐 or Memory making 📷?",
    "Winter cuddles ❄️ or Summer adventures ☀️?",
    "Dancing together 💃 or Walking together 🚶?",
    "Heart songs 🎵 or Soul dances 💃?",
    "Love confessions 💌 or Silent understanding 🤫?",
    "Perfect timing ⏰ or Right person 👤?",
    "Romantic dinners 🍽️ or Casual dates ☕?",
    "Love quotes 📖 or Personal poetry ✍️?",
    "Gentle touches 👋 or Warm embraces 🤗?",
    "Daily texts 📱 or Weekly calls 📞?",
    "Morning coffee ☕ or Evening wine 🍷?",
    "Shared laughter 😂 or Deep talks 💭?",
    "Adventure seeking 🗺️ or Peace finding 🕊️?",
    "Heart melting 💘 or Mind blowing 🤯?",
    "Love stories 💕 or Fairy tales 🧚?",
    "First dates 💕 or Random Tuesdays 📅?",
    "Sunset watching 🌅 or Star gazing ⭐?",
    "Love notes 💌 or Picture memories 📸?",
    "Forever love 💞 or Beautiful journey 🛤️?",
    "Sweet dreams 😴 or Morning smiles 😊?",
    "Romantic comedy 😂 or Love drama 😭?",
    "Love whispers 🗣️ or Laughter echoes 😂?",
    "Beautiful beginnings 🌅 or Perfect endings 🌙?",
    "Intelligent conversations 🧠 or Emotional connections 💖?",
    "Creative dates 🎨 or Traditional romance 👑?",
    "Protective love 🛡️ or Supportive care 🤝?",
    "Shy romance 😊 or Bold affection 😎?",
    "Poetry readings 📖 or Music sharing 🎵?",
    "Cozy mornings 🌅 or Romantic evenings 🌙?",
    "Love languages 💬 or Inside jokes 😂?",
    "Future dreams 🌟 or Present moments ⏰?",
    "Heart racing dates 💓 or Soul calming times 🧘?",
    "Adventure partners 🎒 or Home builders 🏠?",
    "Romantic trips ✈️ or Everyday magic ✨?",
    "Love declarations 💌 or Silent devotion 🤫?",
    "Passionate moments 🔥 or Tender touches 🌸?",
    "Memory makers 📷 or Future planners 📋?",
    "Heart healers 💝 or Soul inspirers 🌟?",
    "Love givers 💖 or Love receivers 💝?",
    "Dream sharers 💭 or Reality builders 🔧?",
    "Gentle love 🌸 or Fierce devotion 🔥?",
    "Quiet romance 🤫 or Loud celebrations 🎉?",
    "Morning sunshine ☀️ or Evening moonlight 🌙?",
    "Love letters 📝 or Love actions 🤗?",
    "Heart homes 🏠 or Soul journeys 🛤️?",
    "Romantic rebels 😎 or Traditional lovers 👑?",
    "Love warriors 🛡️ or Peace makers 🕊️?",
    "Dream catchers 🌟 or Reality shapers 🔧?",
    "Heart composers 🎵 or Soul dancers 💃?",
    "Love storytellers 📚 or Memory collectors 📸?",
    "Gentle giants 🌸 or Fierce protectors 🛡️?",
    "Love whisperers 🗣️ or Heart listeners 👂?",
    "Soul mates 💫 or Perfect matches 💯?",
    "Love adventures 🎒 or Heart sanctuaries 🏠?",
    "Romantic dreamers 💭 or Love builders 🔧?",
    "Heart singers 🎵 or Soul writers ✍️?",
    "Love discoverers 🔍 or Heart protectors 🛡️?",
    "Gentle lovers 🌸 or Passionate souls 🔥?",
    "Love creators 🎨 or Heart nurturers 🌱?",
    "Dream weavers 🕸️ or Reality painters 🎨?",
    "Heart dancers 💃 or Soul musicians 🎵?",
    "Love architects 🏗️ or Heart gardeners 🌱?",
    "Romantic poets 📝 or Love composers 🎵?",
    "Heart explorers 🗺️ or Soul settlers 🏠?",
    "Love magicians ✨ or Heart healers 💝?"
]

async def cmd_tot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    pool = TOT_QS[:] + reg.get_all_questions("tot")
    q = random.choice(pool)
    txt = f"⚖️ *This or That:* {q}"
    await update.effective_message.reply_text(txt, parse_mode="Markdown")
    pid = _partner_id_of(uid)
    if pid:
        try: 
            await context.bot.send_message(pid, txt, parse_mode="Markdown")
        except: 
            pass

async def cmd_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("🎫 Enter your promo code here…")

# --- Game chooser -------------------------------------------------------------
async def cmd_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤔 Truth", callback_data="game:truth"),
            InlineKeyboardButton("🎲 Dare",  callback_data="game:dare"),
        ],
        [
            InlineKeyboardButton("🌀 WYR",   callback_data="game:wyr"),
            InlineKeyboardButton("🙅 NHIE",  callback_data="game:nhie"),
        ],
        [
            InlineKeyboardButton("💋 KMK",   callback_data="game:kmk"),
            InlineKeyboardButton("⚖️ This/That", callback_data="game:tot"),
        ],
    ])
    await update.message.reply_text("🎮 Choose a game:", reply_markup=kb)

async def on_game_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()                      # stop loading spinner
    choice = q.data.split(":")[1]
    # optional: remove keyboard for clean look
    try:
        await q.edit_message_reply_markup(None)
    except Exception:
        pass

    if choice == "truth": 
        return await cmd_truth(update, context)
    if choice == "dare":  
        return await cmd_dare(update, context)
    if choice == "wyr":   
        return await cmd_wyr(update, context)
    if choice == "nhie":  
        return await cmd_nhie(update, context)
    if choice == "kmk":   
        return await cmd_kmk(update, context)
    if choice == "tot":   
        return await cmd_tot(update, context)

# Maintenance – refresh left menu on demand
async def cmd_fixmenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_default_menu(context.application)
    await update.effective_message.reply_text("✅ Left menu refreshed. Send /start.")

# ===================== register =====================
def register(app: Application) -> None:
    app.add_handler(CommandHandler("quit",       cmd_quit),       group=0)
    app.add_handler(CommandHandler("link",       cmd_link),       group=0)
    app.add_handler(CommandHandler("lang",       cmd_lang),       group=0)
    app.add_handler(CallbackQueryHandler(on_lang_chosen,
                                         pattern=r"^(lang_en|lang_hi)$",
                                         block=False),           group=-1)
    app.add_handler(CommandHandler("cancel",     cmd_cancel),     group=0)
    app.add_handler(CommandHandler("settings",   cmd_settings),   group=0)
    app.add_handler(CommandHandler("help",       cmd_help),       group=0)
    app.add_handler(CommandHandler("rules",      cmd_rules),      group=0)
    app.add_handler(CommandHandler("terms",      cmd_terms),      group=0)
    app.add_handler(CommandHandler("premium",    cmd_premium),    group=0)
    app.add_handler(CommandHandler("myid",       cmd_myid),       group=0)
    app.add_handler(CommandHandler("paysupport", cmd_paysupport), group=0)
    app.add_handler(CommandHandler("truth",      cmd_truth),      group=0)
    app.add_handler(CommandHandler("dare",       cmd_dare),       group=0)
    app.add_handler(CommandHandler("wyr",        cmd_wyr),        group=0)
    app.add_handler(CommandHandler("nhie",       cmd_nhie),       group=0)
    app.add_handler(CommandHandler("kmk",        cmd_kmk),        group=0)
    app.add_handler(CommandHandler("tot",        cmd_tot),        group=0)
    app.add_handler(CommandHandler("game",       cmd_game),       group=0)
    # HIGH PRIORITY so generic CallbackQueryHandler doesn't consume it first
    app.add_handler(CallbackQueryHandler(on_game_choice, pattern=r"^game:(truth|dare|wyr|nhie|kmk|tot)$"), group=-1)
    app.add_handler(CommandHandler("promocode",  cmd_promocode),  group=0)
    # Privacy command (ChatGPT Final Polish)
    from handlers.privacy_content import cmd_privacy
    app.add_handler(CommandHandler("privacy",    cmd_privacy),    group=0)
    
    # My Data command - shows user data summary
    from handlers.my_data_handler import cmd_my_data
    app.add_handler(CommandHandler("my_data",    cmd_my_data),    group=0)
    
    app.add_handler(CommandHandler("fixmenu",    cmd_fixmenu),    group=0)
