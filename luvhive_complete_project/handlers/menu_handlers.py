# menu_handlers.py
"""
Safe helpers for your bottom menu.

This file does NOT register any handlers (to avoid conflicts with your
existing button handlers in main.py). It only gives you helpers to
optionally add an inline "🛠 Admin" button under your menu message.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
import logging
import asyncio

from admin import ADMIN_IDS, CB_ADMIN
from utils.cb import cb_match, CBError

log = logging.getLogger("luvbot.menu")
from menu import main_menu_kb, CB_HOME_FRIENDS, CB_HOME_BACK, CB_HOME_FHELP  # reply keyboard (unchanged)
import registration as reg

# ---- display helpers ----
from utils.display import safe_display_name
from chat import send_and_delete  # Import auto-delete function
# -------------------------

def add_admin_row(inline_markup: InlineKeyboardMarkup, user_id: int) -> InlineKeyboardMarkup:
    """
    Given an InlineKeyboardMarkup for your main menu message, append a final
    row with '🛠 Admin' if the user is an admin.
    If you are only using a ReplyKeyboard, you can ignore this helper.
    """
    if user_id in ADMIN_IDS and inline_markup is not None:
        rows = list(inline_markup.inline_keyboard)
        rows.append([InlineKeyboardButton("🛠 Admin", callback_data=CB_ADMIN)])
        return InlineKeyboardMarkup(rows)
    return inline_markup

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Convenience function: sends your bottom ReplyKeyboard only.
    (No inline buttons here; your existing handlers in main.py keep working.)
    """
    await update.effective_message.reply_text(
        "What would you like to do next?",
        reply_markup=main_menu_kb(),
    )

async def on_home_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # GUARD: agar koi active text flow chal raha hai (vault/fantasy/confession), to is handler ko skip
    from handlers.text_framework import FEATURE_KEY
    af = context.user_data.get(FEATURE_KEY)
    if af and af not in (None, "", "menu"):
        return

    # source detect
    is_cb = update.callback_query is not None
    uid = update.effective_user.id

    # helper to send/edit
    async def _send(text: str, kb: InlineKeyboardMarkup | None = None):
        if is_cb:
            q = update.callback_query
            try:
                await q.edit_message_text(text, reply_markup=kb, parse_mode=None)
            finally:
                # answer जरूरी है ताकि loading spinner हटे
                try: 
                    await q.answer()
                except Exception: 
                    pass
        else:
            await update.message.reply_text(text, reply_markup=kb, parse_mode=None)

    friends = reg.list_friends(uid, 20)

    if not friends:
        txt = (
            "👥 *Your Friends*\n\n"
            "You haven't added anyone yet.\n\n"
            "*How to add*\n"
            "• While chatting, type `/addfriend` to save your partner.\n"
            "• Or use `/friends` to manage.\n"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅ Back", callback_data=CB_HOME_BACK)]
        ])
        return await _send(txt, kb)

    # build list (top 10)
    rows = []
    for friend_id in friends[:10]:
        name = safe_display_name(friend_id)
        # Get friendship level
        level, count, emoji = reg.get_friendship_level(uid, friend_id)
        level_name = reg.get_level_name(level)
        display_name = f"{emoji} {name} ({level_name})"
        rows.append([
            InlineKeyboardButton(f"🔄 Invite {name}", callback_data=f"rm:ask:{friend_id}"),
            InlineKeyboardButton(f"🗑 Remove", callback_data=f"fr:del:{friend_id}")
        ])
    rows.append([InlineKeyboardButton("❓ Help", callback_data=CB_HOME_FHELP)])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data=CB_HOME_BACK)])

    # Create friends text with levels
    friends_text = "👥 *Your Friends*\n\n"
    for friend_id in friends[:10]:
        name = safe_display_name(friend_id)
        level, count, emoji = reg.get_friendship_level(uid, friend_id)
        level_name = reg.get_level_name(level)
        friends_text += f"{emoji} {name} — {level_name}\n"
    
    friends_text += "\n🌱→🌿→🌳 Level up by chatting more!\nTap *Invite* to re-match instantly."
    await _send(friends_text, InlineKeyboardMarkup(rows))

async def on_home_friends_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    txt = (
        "ℹ️ *How to add friends*\n\n"
        "• While chatting, send `/addfriend` to save your current partner.\n"
        "• Use `/friends` or the Friends button to invite them later.\n\n"
        "Tip: When they *Accept*, re-match starts automatically.\n"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data=CB_HOME_FRIENDS)]])
    await q.edit_message_text(txt, reply_markup=kb, parse_mode=None)
    await q.answer()

async def on_home_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    # show the main home menu again
    try:
        await q.edit_message_text("What would you like to do next?", reply_markup=main_menu_kb())
    except Exception:
        await q.edit_message_text("What would you like to do next?")
    await q.answer()

async def on_friend_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        # Fix pattern to match fr:del:123 format
        m = cb_match(q.data or "", r"^fr:del:(?P<target>\d+)$")
        target = int(m["target"])
    except (CBError, ValueError):
        log.warning(f"Invalid fr:del callback: {q.data}")
        await q.answer("❌ Invalid request.", show_alert=True)
        return
    uid = q.from_user.id

    # Remove the friendship
    reg.remove_friend(uid, target)

    # Show success message briefly, then refresh friends interface
    try:
        # Edit message to show success
        await q.edit_message_text("✅ Friend removed successfully.")
        
        # Schedule refresh of friends interface after 2 seconds
        async def refresh_friends_interface():
            await asyncio.sleep(2)
            try:
                # Call on_home_friends to show updated friends list
                await on_home_friends(update, context)
            except Exception as e:
                log.error(f"Error refreshing friends interface: {e}")
                # Fallback - delete message if refresh fails
                try:
                    await q.message.delete()
                except Exception:
                    pass
        
        asyncio.create_task(refresh_friends_interface())
    except Exception:
        # If edit fails, send new message with auto-deletion
        await send_and_delete(context.bot, uid, "✅ Friend removed successfully.", delay=5)

    # Notify the removed friend
    try:
        name = safe_display_name(uid)
        await context.bot.send_message(target, f"ℹ️ {name} removed you from their friend list.")
    except Exception:
        pass



async def on_profile_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View a friend's profile"""
    q = update.callback_query
    await q.answer()

    try:
        m = cb_match(q.data or "", r"^uprof:(?P<uid>\d+)$")
        target_uid = int(m["uid"])
    except (CBError, ValueError) as e:
        await q.answer(f"❌ Error loading profile: {str(e)}", show_alert=True)
        return

    viewer_uid = q.from_user.id

    # Get profile info
    try:
        from handlers.posts_handlers import ensure_profile, get_username
        profile = ensure_profile(target_uid)
        username = get_username(None, target_uid)
        bio = reg.get_bio(target_uid) or "No bio set"

        # Friend status
        already_friends = reg.is_friends(viewer_uid, target_uid)
        pending_out = reg.has_sent_request(viewer_uid, target_uid)
        pending_in = reg.has_incoming_request(viewer_uid, target_uid)

        name = safe_display_name(target_uid)
        text = (
            f"👤 **{name}**\n\n"
            f"📖 Bio: {bio}\n"
        )

        buttons = []

        # Friend management buttons
        if viewer_uid == target_uid:
            buttons.append([InlineKeyboardButton("👤 This is you!", callback_data="noop")])
        elif already_friends:
            buttons.append([InlineKeyboardButton("✅ Friends", callback_data="noop")])
            buttons.append([InlineKeyboardButton("❌ Remove Friend", callback_data=f"fr:del:{target_uid}")])
        elif pending_in:
            buttons.append([
                InlineKeyboardButton("✅ Accept Request", callback_data=f"fr:acc:{target_uid}"),
                InlineKeyboardButton("❌ Decline Request", callback_data=f"fr:dec:{target_uid}")
            ])
        elif pending_out:
            buttons.append([InlineKeyboardButton("⏳ Request Sent", callback_data="noop")])
        else:
            buttons.append([InlineKeyboardButton("➕ Add Friend", callback_data=f"fr:req:{target_uid}")])

        # Back button
        buttons.append([InlineKeyboardButton("⬅️ Back to Friends", callback_data=CB_HOME_FRIENDS)])

        await q.edit_message_text(
            text=text, 
            reply_markup=InlineKeyboardMarkup(buttons), 
            parse_mode=None
        )

    except Exception as e:
        await q.answer(f"❌ Error loading profile: {str(e)}", show_alert=True)


def register_menu_handlers(app):
    """Register menu handlers with FIXED priority to avoid conflicts"""
    # Text handler for reply keyboard Friends button (HIGHER PRIORITY)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^👥.*Friends$"), on_home_friends), group=-1)

    # Callback handlers for inline buttons (LOWER PRIORITY) 
    app.add_handler(CallbackQueryHandler(on_home_friends,      pattern=r"^home:friends$"),       group=-2)
    app.add_handler(CallbackQueryHandler(on_home_friends_help, pattern=r"^home:friends_help$"),  group=-2)
    app.add_handler(CallbackQueryHandler(on_home_back,         pattern=r"^home:back$"),          group=-2)
    app.add_handler(CallbackQueryHandler(on_friend_remove,     pattern=r"^fr:del:\d+$"),         group=-2)
    


def register(app):
    """
    Register menu handlers for Friends functionality.
    """
    register_menu_handlers(app)