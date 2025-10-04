
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import registration as reg
from utils.display import safe_display_name
import asyncio

# Import unified auto-delete utility
from handlers.posts_handlers import send_and_delete_notification as send_and_delete

async def on_friend_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle fr:acc:<user_id> callback - accept friend request"""
    q = update.callback_query
    await q.answer()
    
    try:
        requester_uid = int(q.data.split(":")[2])
    except Exception:
        return await q.answer("❌ Invalid request.", show_alert=True)
    
    approver_uid = q.from_user.id
    
    # Remove the request and add friendship
    reg.delete_friend_request(requester_uid, approver_uid)
    reg.add_friend(approver_uid, requester_uid)
    
    # Update the message with auto-deletion
    try:
        await q.edit_message_text("✅ Friend request accepted!")
        # Schedule message deletion after 5 seconds
        async def delete_after_delay():
            await asyncio.sleep(5)
            try:
                await context.bot.delete_message(q.message.chat.id, q.message.message_id)
            except Exception:
                pass
        asyncio.create_task(delete_after_delay())
    except Exception:
        pass
    
    # Notify the requester with auto-deletion
    try:
        name = safe_display_name(approver_uid)
        asyncio.create_task(send_and_delete(context.bot, requester_uid, f"✅ {name} approved your request. You're now friends.", delay=5))
    except Exception:
        pass
    
    # Refresh profile if user is on profile page
    try:
        from handlers.posts_handlers import view_profile
        # Check if this callback came from a profile context (look for profile callback patterns)
        if q.message and q.message.reply_markup and q.message.reply_markup.inline_keyboard:
            # If the message has profile-like callback data, refresh the profile
            for row in q.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.callback_data and (button.callback_data.startswith('feed:user:') or 
                                                 button.callback_data.startswith('crush:') or
                                                 button.callback_data.startswith('uprof:friends:') or
                                                 button.callback_data.startswith('blk:')):
                        return await view_profile(update, context)
    except Exception:
        pass

async def on_friend_decline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle fr:dec:<user_id> callback - decline friend request"""
    q = update.callback_query
    await q.answer()
    
    try:
        requester_uid = int(q.data.split(":")[2])
    except Exception:
        return await q.answer("❌ Invalid request.", show_alert=True)
    
    approver_uid = q.from_user.id
    
    # Remove the request
    reg.delete_friend_request(requester_uid, approver_uid)
    
    # Update the message with auto-deletion
    try:
        await q.edit_message_text("❌ Friend request declined.")
        # Schedule message deletion after 5 seconds
        async def delete_decline_after_delay():
            await asyncio.sleep(5)
            try:
                await context.bot.delete_message(q.message.chat.id, q.message.message_id)
            except Exception:
                pass
        asyncio.create_task(delete_decline_after_delay())
    except Exception:
        pass
    
    # Notify the requester
    try:
        name = safe_display_name(approver_uid)
        asyncio.create_task(send_and_delete(context.bot, requester_uid, f"❌ {name} declined your request.", delay=5))
    except Exception:
        pass
        
    # Refresh profile if user is on profile page
    try:
        from handlers.posts_handlers import view_profile
        # Check if this callback came from a profile context
        if q.message and q.message.reply_markup and q.message.reply_markup.inline_keyboard:
            # If the message has profile-like buttons, refresh the profile
            for row in q.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.callback_data and (button.callback_data.startswith('feed:user:') or 
                                                 button.callback_data.startswith('crush:') or
                                                 button.callback_data.startswith('uprof:friends:') or
                                                 button.callback_data.startswith('blk:')):
                        return await view_profile(update, context)
    except Exception:
        pass

async def on_friend_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle fr:req:<user_id> callback - send friend request"""
    q = update.callback_query
    await q.answer()
    
    try:
        target_uid = int(q.data.split(":")[2])
    except Exception:
        return await q.answer("❌ Invalid request.", show_alert=True)
    
    requester_uid = q.from_user.id
    
    if requester_uid == target_uid:
        return await q.answer("❌ You can't add yourself as a friend.", show_alert=True)
    
    # Check if already friends
    if reg.is_friends(requester_uid, target_uid):
        return await q.answer("✅ You're already friends!", show_alert=True)
    
    # Check if request already exists
    if reg.has_sent_request(requester_uid, target_uid):
        return await q.answer("⏳ Friend request already sent.", show_alert=True)
    
    # Check if target already sent a request to requester (mutual request)
    if reg.has_sent_request(target_uid, requester_uid):
        # Auto-accept mutual request
        reg.delete_friend_request(target_uid, requester_uid)
        reg.add_friend(requester_uid, target_uid)
        
        try:
            await q.edit_message_text("✅ Friend request accepted! You're now friends.")
            # Schedule message deletion after 10 seconds
            async def delete_mutual_after_delay():
                await asyncio.sleep(10)
                try:
                    await context.bot.delete_message(q.message.chat.id, q.message.message_id)
                except Exception:
                    pass
            asyncio.create_task(delete_mutual_after_delay())
        except Exception:
            pass
        
        # Notify both users with auto-deletion
        try:
            requester_name = safe_display_name(requester_uid)
            target_name = safe_display_name(target_uid)
            asyncio.create_task(send_and_delete(context.bot, target_uid, f"✅ {requester_name} accepted your friend request! You're now friends.", delay=10))
        except Exception:
            pass
        return
    
    # Send new friend request
    reg.create_friend_request(requester_uid, target_uid)
    
    try:
        await q.edit_message_text("📤 Friend request sent!")
        # Schedule message deletion after 10 seconds
        async def delete_sent_after_delay():
            await asyncio.sleep(10)
            try:
                await context.bot.delete_message(q.message.chat.id, q.message.message_id)
            except Exception:
                pass
        asyncio.create_task(delete_sent_after_delay())
    except Exception:
        pass
    
    # Notify the target user
    try:
        requester_name = safe_display_name(requester_uid)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"fr:acc:{requester_uid}"),
                InlineKeyboardButton("❌ Decline", callback_data=f"fr:dec:{requester_uid}")
            ]
        ])
        await context.bot.send_message(
            target_uid, 
            f"👥 {requester_name} sent you a friend request!", 
            reply_markup=keyboard
        )
    except Exception:
        pass

def register(app):
    """Register friend handlers"""
    # Register all friend-related callback handlers
    app.add_handler(CallbackQueryHandler(on_friend_request, pattern=r"^fr:req:\d+$"), group=0)
    app.add_handler(CallbackQueryHandler(on_friend_accept, pattern=r"^fr:acc:\d+$"), group=0)
    app.add_handler(CallbackQueryHandler(on_friend_decline, pattern=r"^fr:dec:\d+$"), group=0)
