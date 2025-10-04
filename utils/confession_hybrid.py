# utils/confession_hybrid.py - ROTATING CONFESSION POOL SYSTEM
import logging
from typing import List, Dict, Any
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.hybrid_db import (
    get_available_confessions_for_user_hybrid,
    track_confession_delivery_hybrid, 
    get_active_user_ids_hybrid,
    get_db_status
)

log = logging.getLogger("luvbot.confession_hybrid")

# Testers for fallback
TESTERS = {8482725798, 647778438, 1437934486}
BATCH_LIMIT = 10
FIRST_PASS_MAX = 2

def clean_text_for_telegram(text: str) -> str:
    """Remove ALL characters that could cause Telegram parsing issues"""
    if not text:
        return ""
    
    # Remove/replace problematic characters that break Telegram parsing
    text = str(text)
    # Remove markdown characters
    text = text.replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')
    # Remove HTML-like tags
    text = text.replace('<', '').replace('>', '')
    # Remove other problematic characters
    text = text.replace('\\', '').replace('{', '').replace('}', '')
    # Clean excessive whitespace
    text = ' '.join(text.split())
    
    return text[:1000]  # Limit length to prevent issues

async def create_exciting_confession_delivery(conf_id: int, confession_text: str, recipient_id: int) -> str:
    """BULLETPROOF confession delivery - NO MARKDOWN, NO PARSING ERRORS"""
    try:
        # Clean the confession text completely
        safe_confession = clean_text_for_telegram(confession_text)
        
        # 3 MESSAGE VARIANTS: Short, Medium, Long (randomly selected)
        import random
        
        # SHORT VARIANT - Clean and minimal
        short_variants = [
            f"""💌 Anonymous confession:

📝 {safe_confession}""",

            f"""🔥 Someone shared this with you:

📝 {safe_confession}""",

            f"""💭 A stranger's secret:

📝 {safe_confession}"""
        ]
        
        # MEDIUM VARIANT - Some personality
        medium_variants = [
            f"""💌 Anonymous confession received!

🎯 Someone chose you to share this with:

📝 {safe_confession}

💫 React with understanding.""",

            f"""🔥 Secret confession delivered!

⚡ This person trusted you with their truth:

📝 {safe_confession}

🎭 Your reaction matters.""",

            f"""💭 Confession roulette!

🌟 You've been selected to receive:

📝 {safe_confession}

💝 Be kind in your response."""
        ]
        
        # LONG VARIANT - More engaging (but cleaner than before)
        long_variants = [
            f"""💌 ANONYMOUS CONFESSION RECEIVED!

🎯 A stranger chose YOU to receive their deepest truth:

📝 {safe_confession}

🌙 This person trusted you with their vulnerability.
💖 Your reaction could mean everything to them.

🎭 Be the support they need.""",

            f"""🔥 CONFESSION ALERT!

⚡ Someone couldn't keep this to themselves and sent it to YOU:

📝 {safe_confession}

🌟 Out of everyone, their confession found you.
💫 Your understanding matters more than you know.

💝 React with compassion.""",

            f"""💭 SECRET CONFESSION DELIVERED!

🎰 You've hit the confession jackpot - someone trusted YOU:

📝 {safe_confession}

🔮 These are thoughts they've never spoken aloud.
🎭 Your reaction could change their day completely.

✨ Show them they're not alone."""
        ]
        
        # Randomly select variant type (33% each)
        variant_choice = random.randint(1, 3)
        
        if variant_choice == 1:
            # Short variant
            selected_variants = short_variants
        elif variant_choice == 2:
            # Medium variant  
            selected_variants = medium_variants
        else:
            # Long variant
            selected_variants = long_variants
        
        # Select specific message from chosen variant
        return selected_variants[recipient_id % len(selected_variants)]
        
    except Exception as e:
        log.error(f"❌ Error creating confession delivery: {e}")
        # Ultra-safe fallback with zero formatting
        safe_confession = clean_text_for_telegram(confession_text)
        return f"""💌 Anonymous confession:

📝 {safe_confession}"""

def create_confession_reaction_keyboard(confession_id: int):
    """Create reaction and reply buttons for confessions"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❤️", callback_data=f"conf_react:{confession_id}:love"),
            InlineKeyboardButton("😂", callback_data=f"conf_react:{confession_id}:laugh"),
            InlineKeyboardButton("😢", callback_data=f"conf_react:{confession_id}:sad"),
            InlineKeyboardButton("😮", callback_data=f"conf_react:{confession_id}:wow")
        ],
        [
            InlineKeyboardButton("💬 Reply Anonymously", callback_data=f"conf_reply:{confession_id}"),
            InlineKeyboardButton("🔄 Share Yours", callback_data="confession_menu:confess")
        ]
    ])

async def deliver_confessions_batch_hybrid(context: ContextTypes.DEFAULT_TYPE):
    """
    🔄 ROTATING CONFESSION POOL SYSTEM
    Every person gets 1 confession, no repeats, confessions get reused!
    """
    try:
        # Get DB status
        db_status = get_db_status()
        log.info(f"🔧 Using {db_status['mode']} database")
        
        # Build recipient pool
        active_users = set(get_active_user_ids_hybrid())
        # ALWAYS include testers for guaranteed delivery
        active_users |= TESTERS
        log.info(f"[confession-hybrid] 🎯 Total recipient pool: {len(active_users)} users")
        log.info(f"[confession-hybrid] 🧪 Pool includes: {sorted(active_users)}")
        
        # ROTATING POOL: Each user gets a confession they haven't seen before
        assignments = []
        
        for user_id in active_users:
            # Get confessions available for this specific user (no repeats)
            available_confessions = get_available_confessions_for_user_hybrid(user_id, limit=1)
            
            if available_confessions:
                confession = available_confessions[0]
                conf_id = confession['id']
                author_id = confession['author_id']
                text = confession['text']
                
                assignments.append((conf_id, author_id, text, user_id))
                log.info(f"🎯 Assigned confession #{conf_id}: {author_id} → {user_id}")
            else:
                log.warning(f"⚠️ No available confessions for user {user_id} (all seen before)")
        
        if not assignments:
            log.warning("⚠️ No assignments made! All users may have seen all available confessions.")
            return
            
        log.info(f"📋 Final assignments: {len(assignments)} confessions to {len(assignments)} unique recipients")
        
        # Send confessions with bulletproof delivery
        sent_count = 0
        for conf_id, author_id, text, recipient in assignments:
            try:
                # Create exciting confession delivery message
                message = await create_exciting_confession_delivery(conf_id, text, recipient)
                
                # Try with reaction buttons first (bulletproof)
                try:
                    reaction_keyboard = create_confession_reaction_keyboard(conf_id)
                    await context.bot.send_message(recipient, message, reply_markup=reaction_keyboard)
                    sent_count += 1
                    log.info(f"✅ Delivered confession #{conf_id} from {author_id} → {recipient} with reaction buttons")
                except Exception as parse_error:
                    log.warning(f"⚠️ Parse mode failed for #{conf_id}, trying ultra-safe fallback: {parse_error}")
                    # Ultra-safe fallback message with zero formatting
                    safe_text = clean_text_for_telegram(text)
                    ultra_safe_message = f"""🌀 ANONYMOUS CONFESSION RECEIVED!

{safe_text}

Someone trusted you with their secret...

Reply: /reply_{conf_id} <your message>
Share yours: /confess"""
                    
                    try:
                        # Try fallback with buttons
                        reaction_keyboard = create_confession_reaction_keyboard(conf_id)
                        await context.bot.send_message(recipient, ultra_safe_message, reply_markup=reaction_keyboard)
                        sent_count += 1
                        log.info(f"✅ Delivered confession #{conf_id} with ultra-safe fallback + buttons")
                    except Exception as final_error:
                        log.error(f"💀 FINAL FALLBACK FAILED for #{conf_id}: {final_error}")
                        continue
                
                # Track delivery (allows confession reuse for others)
                if track_confession_delivery_hybrid(conf_id, recipient):
                    log.info(f"📋 Tracked delivery for confession #{conf_id}")
                else:
                    log.warning(f"⚠️ Failed to track confession #{conf_id} delivery")
                    
            except Exception as e:
                log.error(f"❌ Complete failure for confession #{conf_id} to {recipient}: {e}")
        
        log.info(f"🎯 Successfully delivered {sent_count}/{len(assignments)} confessions")
        log.info(f"🔄 ROTATING POOL: Confessions can be reused for other users!")
        
    except Exception as e:
        log.error(f"🚨 Confession delivery system failed: {e}")
        # This should never fail with HTTP-based Supabase!