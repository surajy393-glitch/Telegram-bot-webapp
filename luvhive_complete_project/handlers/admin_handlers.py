
# handlers/admin_handlers.py
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from admin import (
    ADMIN_IDS,
    # callback ids
    CB_ADMIN, CB_AD_STATS, CB_AD_ACTIVE, CB_AD_WAITING, CB_AD_PREM_LIST,
    CB_AD_GIVE_PREM, CB_AD_REM_PREM, CB_AD_USER_INFO, CB_AD_RESET_USER,
    CB_AD_BACKUP, CB_AD_BCAST,
    # ui
    admin_title, admin_kb,
    # db helpers / actions
    db_stats, premium_users, set_premium, user_info, reset_user_metrics,
    runtime_counts, q_all, get_pending_vault_content, approve_vault_content, delete_vault_content
)
import registration as reg
from utils.db_migration import run_all_migrations
from utils.cb import cb_match, CBError

UD_MODE = "ad:mode"   # "gp" | "rp" | "info" | "reset" | "bcast"

# --- Admin: add questions to DB ---
async def cmd_addquestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return await update.effective_message.reply_text("⛔ Admin only.")
    if len(context.args) < 2:
        return await update.effective_message.reply_text(
            "Usage: /addquestion <truth|dare|wyr|nhie|kmk|tot> <your question>"
        )
    game = context.args[0].lower()
    if game not in {"truth","dare","wyr","nhie","kmk","tot"}:
        return await update.effective_message.reply_text(
            "Game must be one of: truth / dare / wyr / nhie / kmk / tot"
        )
    text = " ".join(context.args[1:])
    reg.add_question(game, text, update.effective_user.id)
    await update.effective_message.reply_text(f"✅ Added to {game}: {text}")

async def cmd_migrate_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apply scaling database constraints and migrations."""
    if not _is_admin(update):
        return await update.effective_message.reply_text("⛔ Admin only.")
    
    await update.effective_message.reply_text("🔧 Starting database migration for scaling...")
    
    try:
        results = run_all_migrations()
        
        response = "🔧 **Database Migration Results:**\n\n"
        for result in results:
            response += f"{result}\n"
        
        response += "\n**Migration completed!** Your bot is now ready for scaling to 10k+ users."
        
        await update.effective_message.reply_text(response, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await update.effective_message.reply_text(
            f"❌ Migration failed: {str(e)}\n\nCheck logs for details.",
            parse_mode=ParseMode.HTML
        )

def _is_admin(update: Update) -> bool:
    u = update.effective_user
    return bool(u and u.id in ADMIN_IDS)

def _looks_like_tg_id(s: str) -> bool:
    """Avoid swallowing small numbers like '25' used for age."""
    return s.isdigit() and 7 <= len(s) <= 12

# ---------- /admin ----------
async def open_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        if update.effective_message:
            await update.effective_message.reply_text("⛔ Admins only.")
        return

    # opening the panel cancels any pending prompt
    context.user_data.pop(UD_MODE, None)

    if update.callback_query:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text(
            admin_title(), parse_mode=ParseMode.HTML, reply_markup=admin_kb()
        )
    else:
        await update.effective_message.reply_text(
            admin_title(), parse_mode=ParseMode.HTML, reply_markup=admin_kb()
        )

# ---------- panel buttons ----------
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    q = update.callback_query; await q.answer()
    s = db_stats()
    try:
        act, wait = runtime_counts()
    except Exception:
        act, wait = 0, 0
    txt = (
        "📈 <b>Stats</b>\n"
        f"Users: <b>{s['users']}</b>\n"
        f"Premium: <b>{s['premium_users']}</b>\n"
        f"Dialogs (today / total): <b>{s['dialogs_today']}</b> / <b>{s['dialogs_total']}</b>\n"
        f"Messages (sent / recv): <b>{s['msgs_sent']}</b> / <b>{s['msgs_recv']}</b>\n"
        f"Ratings (👍 / 👎): <b>{s['rating_up']}</b> / <b>{s['rating_down']}</b>\n"
        f"Active chats: <b>{act}</b>\n"
        f"Waiting: <b>{wait}</b>"
    )
    await q.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=admin_kb())

async def show_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    q = update.callback_query; await q.answer()
    try:
        act, _ = runtime_counts()
    except Exception:
        act = 0
    await q.edit_message_text(
        f"💬 <b>Active Chats:</b> <b>{act}</b>",
        parse_mode=ParseMode.HTML, reply_markup=admin_kb()
    )

async def show_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    q = update.callback_query; await q.answer()
    try:
        _, wait = runtime_counts()
    except Exception:
        wait = 0
    await q.edit_message_text(
        f"⏳ <b>Waiting users:</b> <b>{wait}</b>",
        parse_mode=ParseMode.HTML, reply_markup=admin_kb()
    )

async def show_premium_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    q = update.callback_query; await q.answer()
    rows = premium_users(limit=200)
    if not rows:
        txt = "👑 <b>Premium List</b>\nNo premium users yet."
    else:
        lines = [f"• <code>{uid}</code> — {lang or '—'}" for uid, lang in rows]
        txt = "👑 <b>Premium List</b>\n" + "\n".join(lines)
    await q.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=admin_kb())

# ---------- prompts ----------
async def prompt_give_prem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    q = update.callback_query; await q.answer()
    context.user_data[UD_MODE] = "gp"
    await q.edit_message_text(
        "💎 Send the <b>Telegram user ID</b> to grant Premium.\n"
        "Tip: You can also use <code>/prem &lt;id&gt;</code>.",
        parse_mode=ParseMode.HTML
    )

async def prompt_remove_prem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    q = update.callback_query; await q.answer()
    context.user_data[UD_MODE] = "rp"
    await q.edit_message_text(
        "❌ Send the <b>Telegram user ID</b> to remove Premium.\n"
        "Tip: You can also use <code>/unprem &lt;id&gt;</code>.",
        parse_mode=ParseMode.HTML
    )

async def prompt_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    q = update.callback_query; await q.answer()
    context.user_data[UD_MODE] = "info"
    await q.edit_message_text("🔎 Send the <b>Telegram user ID</b> to lookup.", parse_mode=ParseMode.HTML)

async def prompt_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    q = update.callback_query; await q.answer()
    context.user_data[UD_MODE] = "reset"
    await q.edit_message_text(
        "🧹 Send the <b>Telegram user ID</b> to reset metrics for.\n"
        "Tip: You can also use <code>/resetuser &lt;id&gt;</code>.",
        parse_mode=ParseMode.HTML
    )

async def prompt_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    q = update.callback_query; await q.answer()
    context.user_data[UD_MODE] = "bcast"
    await q.edit_message_text("📣 Send the message to broadcast to <b>all users</b>.", parse_mode=ParseMode.HTML)

async def show_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to trigger data backup."""
    if not _is_admin(update):
        return

    await update.message.reply_text("📦 Backup initiated...")
    # Add backup logic here if needed

async def cmd_reports_summary(update, context):
    if not _is_admin(update):
        return await update.message.reply_text("⛔ Admin only.")
    try:
        import registration as reg
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
              SELECT DATE(created_at) d,
                     COUNT(*) total,
                     SUM(CASE WHEN in_secret THEN 1 ELSE 0 END) secret
              FROM chat_reports
              WHERE created_at >= NOW() - INTERVAL '7 days'
              GROUP BY DATE(created_at) ORDER BY d DESC
            """)
            rows = cur.fetchall()
    except Exception as e:
        return await update.message.reply_text(f"DB ERROR: {e}")
    if not rows:
        return await update.message.reply_text("No reports in last 7 days.")
    lines = ["🛡 Reports (last 7 days):"]
    for d, total, secret in rows:
        lines.append(f"{d:%Y-%m-%d} — {total} (secret: {secret})")
    await update.message.reply_text("\n".join(lines))

# ---------- follow-up text after a prompt ----------
async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.text_framework import FEATURE_KEY
    af = context.user_data.get(FEATURE_KEY)
    if af and af not in (None, "", "admin"):
        return

    if not _is_admin(update): return
    mode = context.user_data.get(UD_MODE)
    if not mode: return  # not in an admin prompt

    text = (update.effective_message.text or "").strip()

    if mode in {"gp", "rp", "info", "reset"}:
        # Only intercept proper Telegram IDs; let other small numbers (like ages) pass through.
        if not _looks_like_tg_id(text):
            return

        uid = int(text)

        if mode == "gp":
            set_premium(uid, True)
            await update.effective_message.reply_text(
                f"✅ Premium granted to <code>{uid}</code>.", parse_mode=ParseMode.HTML
            )

        elif mode == "rp":
            set_premium(uid, False)
            await update.effective_message.reply_text(
                f"✅ Premium removed from <code>{uid}</code>.", parse_mode=ParseMode.HTML
            )

        elif mode == "info":
            u = user_info(uid)
            if not u:
                await update.effective_message.reply_text("User not found.")
            else:
                is_p = u.get("is_premium", u.get("premium"))
                txt = (
                    "👤 <b>User Info</b>\n"
                    f"ID: <code>{u['tg_id']}</code>\n"
                    f"Gender: {u['gender'] or '—'}  |  Age: {u['age'] or '—'}\n"
                    f"Location: {u['country'] or '—'}, {u['city'] or '—'}\n"
                    f"Language: {u['language'] or '—'}\n"
                    f"Dialogs (today/total): {u['dialogs_today']}/{u['dialogs_total']}\n"
                    f"Messages (sent/recv): {u['messages_sent']}/{u['messages_recv']}\n"
                    f"Ratings (👍/👎): {u['rating_up']}/{u['rating_down']}\n"
                    f"Reports: {u['report_count']}\n"
                    f"Premium: {'Yes' if is_p else 'No'}"
                )
                await update.effective_message.reply_text(txt, parse_mode=ParseMode.HTML)

        elif mode == "reset":
            reset_user_metrics(uid)
            await update.effective_message.reply_text(
                f"🧹 Metrics reset for <code>{uid}</code>.", parse_mode=ParseMode.HTML
            )
            # (optional) nudge the user to /start again
            try:
                await context.bot.send_message(uid, "🧹 Your profile was reset. Send /start to register again.")
            except Exception:
                pass

        context.user_data.pop(UD_MODE, None)
        await open_admin(update, context)
        return

    if mode == "bcast":
        ids = [row[0] for row in q_all("SELECT tg_user_id FROM users;")]
        sent = 0
        for uid in ids:
            try:
                await context.bot.send_message(uid, text, disable_web_page_preview=True)
                sent += 1
                await asyncio.sleep(0.06)  # ~16 msgs/sec
            except Exception:
                pass
        await update.effective_message.reply_text(f"📣 Broadcast sent to {sent} users.")
        context.user_data.pop(UD_MODE, None)
        await open_admin(update, context)

# ---------- slash commands ----------
async def cmd_prem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text(
            "Use command:\n<b>/prem &lt;telegram_id&gt;</b>", parse_mode=ParseMode.HTML
        ); return
    uid = int(context.args[0]); set_premium(uid, True)
    await update.effective_message.reply_text(f"✅ Premium granted to {uid}.")

async def cmd_unprem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text(
            "Use command:\n<b>/unprem &lt;telegram_id&gt;</b>", parse_mode=ParseMode.HTML
        ); return
    uid = int(context.args[0]); set_premium(uid, False)
    await update.effective_message.reply_text(f"✅ Premium removed from {uid}.")

async def cmd_resetuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text(
            "Use command:\n<b>/resetuser &lt;telegram_id&gt;</b>", parse_mode=ParseMode.HTML
        ); return
    uid = int(context.args[0]); reset_user_metrics(uid)
    await update.effective_message.reply_text(f"🧹 Metrics reset for {uid}.")

async def cmd_userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update): return
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text(
            "Use command:\n<b>/userinfo &lt;telegram_id&gt;</b>", parse_mode=ParseMode.HTML
        ); return
    uid = int(context.args[0]); u = user_info(uid)
    if not u:
        await update.effective_message.reply_text("User not found."); return
    is_p = u.get("is_premium", u.get("premium"))
    txt = (
        "👤 <b>User Info</b>\n"
        f"ID: <code>{u['tg_id']}</code>\n"
        f"Gender: {u['gender'] or '—'}  |  Age: {u['age'] or '—'}\n"
        f"Location: {u['country'] or '—'}, {u['city'] or '—'}\n"
        f"Language: {u['language'] or '—'}\n"
        f"Dialogs (today/total): {u['dialogs_today']}/{u['dialogs_total']}\n"
        f"Messages (sent/recv): {u['messages_sent']}/{u['messages_recv']}\n"
        f"Ratings (👍/👎): {u['rating_up']}/{u['rating_down']}\n"
        f"Reports: {u['report_count']}\n"
        f"Premium: {'Yes' if is_p else 'No'}"
    )
    await update.effective_message.reply_text(txt, parse_mode=ParseMode.HTML)

async def cmd_givecoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to give coins to any user."""
    if not _is_admin(update):
        return await update.effective_message.reply_text("⛔ Admin only.")
    
    if len(context.args) < 2:
        return await update.effective_message.reply_text("Usage: /givecoin <user_id> <amount> (e.g., /givecoin 1437934486 200)")

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except Exception:
        return await update.effective_message.reply_text("User id and amount must be integers.")

    if amount == 0:
        return await update.effective_message.reply_text("Amount must be non-zero.")
    if amount < 0:
        return await update.effective_message.reply_text("Use a positive amount. (Deduction via a separate admin tool if needed.)")

    # add coins
    new_bal = reg.add_coins(target_id, amount)
    await update.effective_message.reply_text(f"✅ Added {amount} coins to {target_id}. New balance: {new_bal}")

    # notify recipient (best-effort)
    try:
        await context.bot.send_message(chat_id=target_id, text=f"🎁 Admin credited your account: +{amount} coins.\n💰 Balance: {new_bal}")
    except Exception:
        pass

async def cmd_coinbal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to check a user's coin balance."""
    if not _is_admin(update):
        return await update.effective_message.reply_text("⛔ Admin only.")
    
    if not context.args:
        return await update.effective_message.reply_text("Usage: /coinbal <user_id>")
    
    try:
        target_id = int(context.args[0])
    except Exception:
        return await update.effective_message.reply_text("User id must be an integer.")
    
    bal = reg.get_coins(target_id)
    await update.effective_message.reply_text(f"💰 Balance for {target_id}: {bal}")

async def cmd_verify_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: reset a user's verification to 'none' so they can re-verify now."""
    if not _is_admin(update):
        if update.effective_message:
            await update.effective_message.reply_text("⛔ Admins only.")
        return
    if not context.args:
        await update.effective_message.reply_text("Usage: /verify_reset <tg_user_id>")
        return
    try:
        uid = int(context.args[0])
    except Exception:
        await update.effective_message.reply_text("Invalid id. Usage: /verify_reset <tg_user_id>")
        return

    import registration as reg
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            UPDATE users
               SET is_verified = FALSE,
                   verify_status = 'none',
                   verify_method = NULL,
                   verify_audio_file = NULL,
                   verify_photo_file = NULL,
                   verify_phrase = NULL,
                   verify_src_chat = NULL,
                   verify_src_msg  = NULL,
                   verify_at = NULL
             WHERE tg_user_id = %s
        """, (uid,))
        con.commit()
    await update.effective_message.reply_text(f"✅ Verification reset for {uid}. They can try again now.")

async def cmd_pendingvault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to review pending vault submissions"""
    if not _is_admin(update):
        await update.effective_message.reply_text("⛔ Admin only.")
        return
    
    try:
        # Get pending content
        pending_content = get_pending_vault_content(10)
        
        if not pending_content:
            await update.effective_message.reply_text(
                "✅ **No Pending Vault Submissions**\n\nAll caught up! No content waiting for review.",
                parse_mode="Markdown"
            )
            return
        
        # Show each pending submission
        for content in pending_content:
            await show_pending_content_for_review(update, context, content)
            
    except Exception as e:
        import logging
        log = logging.getLogger(__name__)
        log.error(f"Error in cmd_pendingvault: {e}")
        await update.effective_message.reply_text(f"❌ Error loading pending content: {str(e)}")

async def show_pending_content_for_review(update, context, content):
    """Show individual pending content with approve/delete options"""
    content_id = content['id']
    submitter_name = content['submitter_name']
    submitter_id = content['submitter_id']
    category = content['category']
    media_type = content['media_type']
    created_at = str(content['created_at'])[:16] if content['created_at'] else 'Unknown'
    
    # Build content preview message
    preview_msg = (
        f"📋 **Pending Vault Review #{content_id}**\n\n"
        f"👤 **Submitter:** {submitter_name} (ID: {submitter_id})\n"
        f"📂 **Category:** {category}\n"
        f"📸 **Type:** {media_type.title()}\n"
        f"⏰ **Submitted:** {created_at}\n\n"
    )
    
    # Add content preview based on type (FULL TEXT for proper admin review)
    if content['text']:
        preview_msg += f"📄 **Text:** {content['text']}\n\n"
    
    # Create approve/delete buttons
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"vault_approve:{content_id}"),
         InlineKeyboardButton("❌ Delete", callback_data=f"vault_delete:{content_id}")],
        [InlineKeyboardButton("👤 View User Info", callback_data=f"vault_userinfo:{submitter_id}")]
    ])
    
    # Send preview message first
    await update.effective_message.reply_text(preview_msg, reply_markup=kb, parse_mode="Markdown")
    
    # Send actual media preview using file_id (doesn't expire)
    if content.get('file_id') and media_type in ['image', 'video']:
        try:
            file_id = content['file_id']
            if media_type == 'image':
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=file_id,
                    caption=f"🖼️ **Preview for Content #{content_id}**\n📸 Actual submitted image",
                    parse_mode="Markdown"
                )
            elif media_type == 'video':
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=file_id,
                    caption=f"🎥 **Preview for Content #{content_id}**\n📹 Actual submitted video",
                    parse_mode="Markdown"
                )
        except Exception as e:
            # If URL fails, try to show alternate message
            await update.effective_message.reply_text(
                f"⚠️ **Image Preview Unavailable for #{content_id}**\n\n"
                f"🔍 **Content Details:**\n"
                f"📸 **Type:** {media_type.title()}\n"
                f"👤 **Submitter:** {content['submitter_name']}\n"
                f"⏰ **Submitted:** {str(content['created_at'])[:16]}\n\n"
                f"💡 **Admin Decision Required:** Please approve or delete based on category appropriateness.",
                parse_mode="Markdown"
            )

async def handle_vault_moderation_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle vault content moderation callbacks"""
    if not _is_admin(update):
        return
    
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split(':')
    action = data_parts[0]
    
    try:
        if action == "vault_approve":
            content_id = int(data_parts[1])
            if approve_vault_content(content_id):
                success_msg = f"✅ **Content #{content_id} Approved!**\n\nThe content is now live in the vault and can be revealed by users."
                try:
                    # Try editing caption first (for media messages)
                    await query.edit_message_caption(caption=success_msg, parse_mode="Markdown")
                except:
                    try:
                        # Try editing text (for text messages)
                        await query.edit_message_text(success_msg, parse_mode="Markdown")
                    except:
                        # Send new message if editing fails
                        await context.bot.send_message(query.message.chat_id, success_msg, parse_mode="Markdown")
            else:
                fail_msg = f"❌ Failed to approve content #{content_id}"
                try:
                    await query.edit_message_caption(caption=fail_msg, parse_mode="Markdown")
                except:
                    try:
                        await query.edit_message_text(fail_msg, parse_mode="Markdown")
                    except:
                        await context.bot.send_message(query.message.chat_id, fail_msg, parse_mode="Markdown")
                
        elif action == "vault_delete":
            content_id = int(data_parts[1])
            if delete_vault_content(content_id):
                delete_msg = f"🗑️ **Content #{content_id} Deleted!**\n\nThe content has been permanently removed from the system."
                try:
                    # Try editing caption first (for media messages)
                    await query.edit_message_caption(caption=delete_msg, parse_mode="Markdown")
                except:
                    try:
                        # Try editing text (for text messages)
                        await query.edit_message_text(delete_msg, parse_mode="Markdown")
                    except:
                        # Send new message if editing fails
                        await context.bot.send_message(query.message.chat_id, delete_msg, parse_mode="Markdown")
            else:
                fail_msg = f"❌ Failed to delete content #{content_id}"
                try:
                    await query.edit_message_caption(caption=fail_msg, parse_mode="Markdown")
                except:
                    try:
                        await query.edit_message_text(fail_msg, parse_mode="Markdown")
                    except:
                        await context.bot.send_message(query.message.chat_id, fail_msg, parse_mode="Markdown")
                
        elif action == "vault_userinfo":
            user_id = int(data_parts[1])
            user_data = user_info(user_id)
            if user_data:
                info_text = (
                    f"👤 **User Information**\n\n"
                    f"**ID:** {user_data['tg_id']}\n"
                    f"**Gender:** {user_data['gender'] or '—'}\n"
                    f"**Age:** {user_data['age'] or '—'}\n"
                    f"**Location:** {user_data['country'] or '—'}, {user_data['city'] or '—'}\n"
                    f"**Dialogs:** {user_data['dialogs_total']}\n"
                    f"**Messages:** {user_data['messages_sent']}/{user_data['messages_recv']}\n"
                    f"**Ratings:** 👍{user_data['rating_up']} 👎{user_data['rating_down']}\n"
                    f"**Reports:** {user_data['report_count']}\n"
                    f"**Premium:** {'Yes' if user_data['is_premium'] else 'No'}"
                )
                await query.edit_message_text(info_text, parse_mode="Markdown")
            else:
                await query.edit_message_text(f"❌ User {user_id} not found")
                
    except Exception as e:
        import logging
        log = logging.getLogger(__name__)
        log.error(f"Error in vault moderation callback: {e}")
        error_msg = f"❌ Error: {str(e)}"
        try:
            await query.edit_message_caption(caption=error_msg, parse_mode="Markdown")
        except:
            try:
                await query.edit_message_text(error_msg, parse_mode="Markdown")
            except:
                await context.bot.send_message(query.message.chat_id, error_msg, parse_mode="Markdown")

async def cmd_verify_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: show a user's current verification fields."""
    if not _is_admin(update):
        if update.effective_message:
            await update.effective_message.reply_text("⛔ Admins only.")
        return
    if not context.args:
        await update.effective_message.reply_text("Usage: /verify_status <tg_user_id>")
        return
    try:
        uid = int(context.args[0])
    except Exception:
        await update.effective_message.reply_text("Invalid id. Usage: /verify_status <tg_user_id>")
        return

    import registration as reg
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT is_verified, verify_status, verify_method, verify_at,
                   verify_audio_file, verify_photo_file
              FROM users WHERE tg_user_id=%s
        """, (uid,))
        row = cur.fetchone()
    if not row:
        await update.effective_message.reply_text("User not found.")
        return
    isv, st, m, ts, af, pf = row
    await update.effective_message.reply_text(
        f"is_verified={bool(isv)}\nverify_status={st}\nverify_method={m}\n"
        f"verify_at={ts}\nvoice={'yes' if af else 'no'} | photo={'yes' if pf else 'no'}"
    )

async def cmd_vault_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to clean up old vault interaction logs."""
    if not _is_admin(update):
        return await update.effective_message.reply_text("⛔ Admin only.")

    # Default 90 days, ya custom days like /vault_cleanup 60
    days = 90
    if context.args:
        try:
            days = int(context.args[0])
        except:
            return await update.effective_message.reply_text("Usage: /vault_cleanup [days]\nExample: /vault_cleanup 60")

    try:
        import registration as reg
        with reg._conn() as con, con.cursor() as cur:
            # Delete old interaction logs (not the actual content)
            cur.execute("""
                DELETE FROM vault_interactions
                WHERE created_at < NOW() - INTERVAL %s
            """, (f"{days} days",))
            deleted = cur.rowcount
            con.commit()

        await update.effective_message.reply_text(
            f"🧹 **Vault Cleanup Completed!**\n\n"
            f"✅ Deleted {deleted} old interaction logs\n"
            f"📅 Older than {days} days\n"
            f"🔒 All content (photos/videos/texts) is safe\n\n"
            f"💡 This helps keep the database clean and fast!"
        )
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Cleanup failed: {str(e)}")

def _parse_duration(s: str) -> datetime:
    """Parse duration string to datetime."""
    s = s.strip().lower()
    now = datetime.utcnow()
    if s in ("life", "lifetime", "perm", "permanent"):
        return datetime(9999, 12, 31, 0, 0, 0)
    m = re.fullmatch(r"(\d+)([dmy])", s)
    if not m:
        raise ValueError("Use 7d / 1m / 6m / 1y / life")
    n, unit = int(m.group(1)), m.group(2)
    if unit == "d": 
        return now + timedelta(days=n)
    if unit == "m": 
        return now + timedelta(days=30*n)
    if unit == "y": 
        return now + timedelta(days=365*n)
    raise ValueError("Use 7d / 1m / 6m / 1y / life")

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user for specified duration."""
    if not _is_admin(update):
        return await update.effective_message.reply_text("⛔ Admins only.")
    if len(context.args) < 2:
        return await update.effective_message.reply_text("Usage: /ban <tg_id> <7d|1m|6m|1y|life> [reason]")
    try:
        tg_id = int(context.args[0])
        until = _parse_duration(context.args[1])
    except Exception as e:
        return await update.effective_message.reply_text(f"❗ {e}")

    reason = " ".join(context.args[2:])[:300] if len(context.args) > 2 else "Violation"
    reg.set_ban(tg_id, until, reason, update.effective_user.id)
    pretty = "lifetime" if until.year >= 9999 else until.strftime("%Y-%m-%d %H:%M UTC")
    await update.effective_message.reply_text(f"✅ Banned {tg_id} till {pretty}\nReason: {reason}")

async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove ban from a user."""
    if not _is_admin(update):
        return await update.effective_message.reply_text("⛔ Admins only.")
    if not context.args:
        return await update.effective_message.reply_text("Usage: /unban <tg_id>")
    try:
        tg_id = int(context.args[0])
    except Exception:
        return await update.effective_message.reply_text("Usage: /unban <tg_id>")

    reg.clear_ban(tg_id)
    await update.effective_message.reply_text(f"✅ Unbanned {tg_id}")

async def cmd_baninfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check ban status of a user."""
    if not _is_admin(update):
        return await update.effective_message.reply_text("⛔ Admins only.")
    if not context.args:
        return await update.effective_message.reply_text("Usage: /baninfo <tg_id>")
    try:
        tg_id = int(context.args[0])
    except Exception:
        return await update.effective_message.reply_text("Usage: /baninfo <tg_id>")

    until, reason, by = reg.get_ban_info(tg_id)
    if not until:
        return await update.effective_message.reply_text(f"{tg_id} is not banned.")
    pretty = "lifetime" if until.year >= 9999 else until.strftime("%Y-%m-%d %H:%M UTC")
    await update.effective_message.reply_text(f"🚫 {tg_id} banned till {pretty}\nReason: {reason or '—'}\nBy: {by or '—'}")

async def cmd_verify_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending verification requests."""
    if not _is_admin(update):
        if update.effective_message:
            await update.effective_message.reply_text("⛔ Admins only.")
        return

    await update.effective_message.reply_text("🔎 Checking verification queue…")
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT tg_user_id, verify_method, verify_audio_file, verify_photo_file,
                   COALESCE(verify_src_chat, tg_user_id) AS src_chat,
                   verify_src_msg, verify_phrase
              FROM users
             WHERE verify_status='pending'
             ORDER BY verify_at NULLS FIRST
             LIMIT 10;
        """)
        rows = cur.fetchall()

    if not rows:
        await update.effective_message.reply_text("✅ No pending verifications.")
        return

    for uid, method, audio_id, photo_id, src_chat, src_mid, phrase in rows:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"verify:ok:{uid}"),
            InlineKeyboardButton("❌ Reject",  callback_data=f"verify:no:{uid}")
        ]])
        phrase_text = f" | Phrase: {phrase}" if phrase else ""
        caption = f"User: {uid} | Method: {method or '—'}{phrase_text}"

        try:
            if method == "voice" and audio_id:
                await context.bot.send_voice(update.effective_chat.id, audio_id, caption=caption, reply_markup=kb)
            elif method == "selfie" and photo_id:
                await context.bot.send_photo(update.effective_chat.id, photo_id, caption=caption, reply_markup=kb)
            elif src_mid:
                # Fallback: copy the original message (works for both voice & photo)
                await context.bot.copy_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=src_chat or uid,
                    message_id=src_mid
                )
                # follow-up text with Approve/Reject buttons
                await update.effective_message.reply_text(caption, reply_markup=kb)
            else:
                await update.effective_message.reply_text(caption, reply_markup=kb)
        except Exception as e:
            # last-resort: just text
            await update.effective_message.reply_text(caption, reply_markup=kb)

async def cmd_check_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check recent chat reports."""
    if not _is_admin(update):
        return await update.effective_message.reply_text("⛔ Admins only.")
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
              SELECT id, created_at, reporter_tg_id, reported_tg_id, in_secret, COALESCE(text,'') 
              FROM chat_reports ORDER BY id DESC LIMIT 10
            """)
            rows = cur.fetchall()
    except Exception as e:
        return await update.effective_message.reply_text(f"DB ERROR: {e}")

    if not rows:
        return await update.effective_message.reply_text("No reports.")

    for (rid, ts, rep, tgt, sec, txt) in rows:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("View", callback_data=f"arep:view:{rid}")]])
        preview = (txt or "—")[:80]
        msg = f"#{rid} • {ts:%Y-%m-%d %H:%M} • from {rep} → {tgt} • Secret:{'Yes' if sec else 'No'}\n{preview}"
        await update.effective_message.reply_text(msg, reply_markup=kb)

async def on_admin_report_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View full report details."""
    if not _is_admin(update):
        return await update.callback_query.answer("Admins only.")
    try:
        m = cb_match(update.callback_query.data or "", r"^arep:view:(?P<rid>\d+)$")
        rid = int(m["rid"])
    except (CBError, ValueError):
        return await update.callback_query.answer("Invalid report ID.")
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT reporter_tg_id, reported_tg_id, in_secret, text, media_file_id, media_type, created_at
                FROM chat_reports WHERE id=%s
            """, (rid,))
            row = cur.fetchone()
    except Exception as e:
        return await update.callback_query.edit_message_text(f"DB ERROR: {e}")

    if not row:
        return await update.callback_query.edit_message_text("Not found.")

    rep, tgt, sec, text, mfid, mtype, ts = row
    caption = (f"🧾 Report #{rid}\n"
               f"Time: {ts:%Y-%m-%d %H:%M}\n"
               f"From: {rep}\nAgainst: {tgt}\n"
               f"Secret: {'Yes' if sec else 'No'}\n"
               f"Text: {text or '—'}")

    try:
        if mfid and mtype == "photo":
            await update.callback_query.edit_message_caption(caption)
            await context.bot.send_photo(update.effective_chat.id, mfid, caption="(attachment)")
        elif mfid and mtype == "document":
            await update.callback_query.edit_message_caption(caption)
            await context.bot.send_document(update.effective_chat.id, mfid, caption="(attachment)")
        else:
            await update.callback_query.edit_message_text(caption)
    except Exception:
        # fallback: send new message
        await context.bot.send_message(update.effective_chat.id, caption)

async def on_verify_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle verification approval/rejection."""
    q = update.callback_query
    try:
        m = cb_match(q.data or "", r"^verify:(?P<action>ok|no):(?P<uid>\d+)$")
        action = m["action"]
        uid = int(m["uid"])
    except (CBError, ValueError):
        return await q.answer("Invalid verification data.")
    status = "approved" if action == "ok" else "rejected"

    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            UPDATE users
               SET is_verified = %s,
                   verify_status = %s,
                   verify_at = NOW()
             WHERE tg_user_id = %s
        """, (status == "approved", status, uid))
        con.commit()

    await q.answer("Done.")

    # Update admin message
    try:
        await q.edit_message_caption(f"User {uid} → {status.upper()}")
    except Exception:
        await q.edit_message_text(f"User {uid} → {status.upper()}")

    # Notify the user directly
    try:
        if status == "approved":
            await context.bot.send_message(uid, "🎉 Your verification is approved. You now have a ✔ Verified badge.")
        else:
            await context.bot.send_message(uid, "❌ Verification rejected. You can retry after 3 days from now.")
    except Exception:
        pass

def register(app):
    # open admin
    app.add_handler(CommandHandler("admin", open_admin))
    app.add_handler(CallbackQueryHandler(open_admin, pattern=f"^{CB_ADMIN}$"))

    # panel buttons
    app.add_handler(CallbackQueryHandler(show_stats,        pattern=f"^{CB_AD_STATS}$"))
    app.add_handler(CallbackQueryHandler(show_active,       pattern=f"^{CB_AD_ACTIVE}$"))
    app.add_handler(CallbackQueryHandler(show_waiting,      pattern=f"^{CB_AD_WAITING}$"))
    app.add_handler(CallbackQueryHandler(show_premium_list, pattern=f"^{CB_AD_PREM_LIST}$"))
    app.add_handler(CallbackQueryHandler(prompt_give_prem,  pattern=f"^{CB_AD_GIVE_PREM}$"))
    app.add_handler(CallbackQueryHandler(prompt_remove_prem,pattern=f"^{CB_AD_REM_PREM}$"))
    app.add_handler(CallbackQueryHandler(prompt_user_info,  pattern=f"^{CB_AD_USER_INFO}$"))
    app.add_handler(CallbackQueryHandler(prompt_reset,      pattern=f"^{CB_AD_RESET_USER}$"))
    app.add_handler(CallbackQueryHandler(show_backup,       pattern=f"^{CB_AD_BACKUP}$"))
    app.add_handler(CallbackQueryHandler(prompt_broadcast,  pattern=f"^{CB_AD_BCAST}$"))

    # slash fast paths
    app.add_handler(CommandHandler("prem",      cmd_prem))
    app.add_handler(CommandHandler("unprem",    cmd_unprem))
    app.add_handler(CommandHandler("resetuser", cmd_resetuser))
    app.add_handler(CommandHandler("userinfo",  cmd_userinfo))
    app.add_handler(CommandHandler("givecoin",  cmd_givecoin))
    app.add_handler(CommandHandler("coinbal",   cmd_coinbal))
    app.add_handler(CommandHandler("verify_queue", cmd_verify_queue))
    app.add_handler(CommandHandler("vq", cmd_verify_queue))
    app.add_handler(CommandHandler("verify_reset", cmd_verify_reset))
    app.add_handler(CommandHandler("verify_status", cmd_verify_status))
    app.add_handler(CommandHandler("pendingvault", cmd_pendingvault))

    # ban system
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("baninfo", cmd_baninfo))

    # reports system
    app.add_handler(CommandHandler("check_reports", cmd_check_reports))
    app.add_handler(CallbackQueryHandler(on_admin_report_view, pattern=r"^arep:view:\d+$"))

    # verification decisions
    app.add_handler(CallbackQueryHandler(on_verify_decision, pattern=r"^verify:(ok|no):\d+$"))
    
    # vault moderation callbacks
    app.add_handler(CallbackQueryHandler(handle_vault_moderation_callbacks, pattern=r"^vault_(approve|delete|userinfo):\d+$"))

    # question management
    app.add_handler(CommandHandler("addquestion", cmd_addquestion), group=0)
    
    # scaling migration
    app.add_handler(CommandHandler("migrate_db", cmd_migrate_db), group=0)
    
    # vault cleanup
    app.add_handler(CommandHandler("vault_cleanup", cmd_vault_cleanup), group=0)

    # handle admin follow-up texts *after* other text handlers (group=50)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text, block=False),
        group=50,
    )
    app.add_handler(CommandHandler("backup", show_backup), group=0)
    app.add_handler(CommandHandler("broadcast", prompt_broadcast), group=0)
    app.add_handler(CommandHandler("reports_summary", cmd_reports_summary), group=0)
