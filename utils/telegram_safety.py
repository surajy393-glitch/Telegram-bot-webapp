# utils/telegram_safety.py - Handle Telegram errors and message limits (ChatGPT Final Polish)
import logging
import telegram
from typing import Optional, Dict, Any, List
from telegram import Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)

class TelegramSafetyHandler:
    """Handle Telegram API errors and message limits gracefully"""
    
    def __init__(self):
        # Telegram limits
        self.MAX_MESSAGE_LENGTH = 4096
        self.MAX_CAPTION_LENGTH = 1024
        self.MAX_MEDIA_PER_MESSAGE = 10
    
    async def safe_send_message(
        self, 
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        text: str,
        **kwargs
    ) -> Optional[telegram.Message]:
        """
        Safely send message with proper error handling for blocked users
        Critical for dating apps - users frequently block the bot
        """
        try:
            # Truncate text if too long
            if len(text) > self.MAX_MESSAGE_LENGTH:
                text = text[:self.MAX_MESSAGE_LENGTH-50] + "... (message truncated)"
            
            return await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
            
        except telegram.error.Forbidden:
            # User blocked the bot - common in dating apps
            log.info(f"🚫 User {chat_id} blocked the bot")
            await self._handle_user_blocked(chat_id, context)
            return None
            
        except telegram.error.ChatNotFound:
            # Chat no longer exists
            log.info(f"💬 Chat {chat_id} not found")
            await self._handle_chat_not_found(chat_id, context)
            return None
            
        except telegram.error.BadRequest as e:
            if "message is too long" in str(e).lower():
                # Fallback: split message
                return await self._send_long_message(context, chat_id, text, **kwargs)
            else:
                log.error(f"BadRequest sending to {chat_id}: {e}")
                return None
                
        except Exception as e:
            log.error(f"Unexpected error sending to {chat_id}: {e}")
            return None
    
    async def _handle_user_blocked(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Handle when user blocks the bot - unpair from any active chats"""
        try:
            # Import here to avoid circular imports
            from chat import find_active_partner, unpair_users
            
            # Find if user has active partner
            partner_id = find_active_partner(user_id)
            if partner_id:
                # Unpair users
                unpair_users(user_id, partner_id)
                
                # Notify partner
                await self.safe_send_message(
                    context,
                    partner_id, 
                    "💔 Your chat partner left the conversation.\n\nType /search to find someone new!",
                    parse_mode='HTML'
                )
                
                log.info(f"🔓 Unpaired {user_id} (blocked bot) from {partner_id}")
                
        except Exception as e:
            log.error(f"Error handling blocked user {user_id}: {e}")
    
    async def _handle_chat_not_found(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Handle when chat is not found - similar cleanup to blocked user"""
        await self._handle_user_blocked(chat_id, context)
    
    async def _send_long_message(
        self, 
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int, 
        text: str,
        **kwargs
    ) -> Optional[telegram.Message]:
        """Split long message into chunks"""
        try:
            chunks = self._split_text(text, self.MAX_MESSAGE_LENGTH - 50)
            last_message = None
            
            for i, chunk in enumerate(chunks):
                if i == 0:
                    last_message = await context.bot.send_message(
                        chat_id=chat_id, text=chunk, **kwargs
                    )
                else:
                    # Remove reply markup for continuation messages
                    kwargs.pop('reply_markup', None)
                    last_message = await context.bot.send_message(
                        chat_id=chat_id, text=chunk, **kwargs
                    )
            
            return last_message
            
        except Exception as e:
            log.error(f"Error sending chunked message: {e}")
            return None
    
    def _split_text(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks at word boundaries"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        words = text.split()
        for word in words:
            if len(current_chunk) + len(word) + 1 <= max_length:
                current_chunk += (word + " ")
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = word + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
    
    async def safe_send_photo(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        photo,
        caption: Optional[str] = None,
        **kwargs
    ) -> Optional[telegram.Message]:
        """Safely send photo with error handling"""
        try:
            # Truncate caption if too long
            if caption and len(caption) > self.MAX_CAPTION_LENGTH:
                caption = caption[:self.MAX_CAPTION_LENGTH-20] + "..."
            
            return await context.bot.send_photo(
                chat_id=chat_id, 
                photo=photo, 
                caption=caption,
                **kwargs
            )
            
        except telegram.error.Forbidden:
            await self._handle_user_blocked(chat_id, context)
            return None
            
        except telegram.error.BadRequest as e:
            if any(err in str(e).lower() for err in [
                "photo_invalid_dimensions", 
                "file_too_big",
                "photo_crop_size_small"
            ]):
                # Try sending as document instead
                log.warning(f"Photo error for {chat_id}, sending as document: {e}")
                try:
                    return await context.bot.send_document(
                        chat_id=chat_id,
                        document=photo,
                        caption=caption,
                        **kwargs
                    )
                except:
                    # Ultimate fallback
                    await self.safe_send_message(
                        context, chat_id, 
                        f"📷 Unable to send photo: {caption or 'Image attachment'}"
                    )
                    return None
            else:
                log.error(f"BadRequest sending photo to {chat_id}: {e}")
                return None
                
        except Exception as e:
            log.error(f"Error sending photo to {chat_id}: {e}")
            return None

    def validate_media_group(self, media_list: List) -> List:
        """Validate and limit media group size"""
        if len(media_list) > self.MAX_MEDIA_PER_MESSAGE:
            log.warning(f"Media group too large ({len(media_list)}), truncating to {self.MAX_MEDIA_PER_MESSAGE}")
            return media_list[:self.MAX_MEDIA_PER_MESSAGE]
        return media_list

# Global safety handler instance
telegram_safety = TelegramSafetyHandler()

# Convenience functions
async def safe_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs):
    """Safe reply to message with error handling"""
    if update.effective_message and update.effective_chat:
        return await telegram_safety.safe_send_message(
            context, 
            update.effective_chat.id, 
            text, 
            **kwargs
        )
    return None

async def safe_send_message(context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str, **kwargs):
    """Safe send message to user with error handling - delegates to main.py safe_send"""
    try:
        # Import here to avoid circular imports
        from main import safe_send
        return await safe_send(context.bot, user_id, text, **kwargs)
    except ImportError:
        # Fallback to telegram_safety implementation
        return await telegram_safety.safe_send_message(context, user_id, text, **kwargs)