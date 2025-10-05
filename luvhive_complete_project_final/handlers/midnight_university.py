# handlers/midnight_university.py
# Midnight University Chronicles - Interactive Mystery Story System

import logging
import datetime
import os
import pytz
from typing import List, Dict, Optional, Tuple
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from registration import _conn
from handlers.text_framework import set_state, clear_state, requires_state, make_cancel_kb, claim_or_reject

log = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

# ==================== CORE UTILITY FUNCTIONS ====================

def _ensure_user_engagement(user_id: int) -> Dict:
    """Ensure user has engagement record, return current stats"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Try to get existing record
            cur.execute("""
                SELECT streak_days, detective_score, last_seen_episode_id 
                FROM muc_user_engagement 
                WHERE user_id = %s
            """, (user_id,))
            
            result = cur.fetchone()
            if result:
                return {
                    'streak_days': result[0],
                    'detective_score': result[1],
                    'last_seen_episode_id': result[2]
                }
            
            # Create new record
            cur.execute("""
                INSERT INTO muc_user_engagement (user_id, streak_days, detective_score)
                VALUES (%s, 0, 0)
                RETURNING streak_days, detective_score, last_seen_episode_id
            """, (user_id,))
            
            result = cur.fetchone()
            con.commit()
            
            return {
                'streak_days': result[0],
                'detective_score': result[1],
                'last_seen_episode_id': result[2]
            }
    except Exception as e:
        log.error(f"[MUC] Error ensuring user engagement for {user_id}: {e}")
        return {'streak_days': 0, 'detective_score': 0, 'last_seen_episode_id': None}

def _get_current_episode() -> Optional[Dict]:
    """Get the current active episode"""
    try:
        with _conn() as con, con.cursor() as cur:
            now = datetime.datetime.now(IST)
            
            cur.execute("""
                SELECT id, title, teaser_md, body_md, cliff_md, status, 
                       publish_at, close_at
                FROM muc_episodes 
                WHERE status IN ('published', 'voting') 
                  AND (publish_at IS NULL OR publish_at <= %s)
                ORDER BY publish_at DESC, id DESC
                LIMIT 1
            """, (now,))
            
            result = cur.fetchone()
            if not result:
                return None
                
            return {
                'id': result[0],
                'title': result[1],
                'teaser_md': result[2],
                'body_md': result[3],
                'cliff_md': result[4],
                'status': result[5],
                'publish_at': result[6],
                'close_at': result[7]
            }
    except Exception as e:
        log.error(f"[MUC] Error getting current episode: {e}")
        return None

def _get_first_published_episode() -> Optional[Dict]:
    """Get the first published episode (lowest idx)"""
    try:
        with _conn() as con, con.cursor() as cur:
            now = datetime.datetime.now(IST)
            
            cur.execute("""
                SELECT id, title, teaser_md, body_md, cliff_md, status, 
                       publish_at, close_at, idx
                FROM muc_episodes 
                WHERE status IN ('published', 'voting') 
                  AND (publish_at IS NULL OR publish_at <= %s)
                ORDER BY idx ASC, id ASC
                LIMIT 1
            """, (now,))
            
            result = cur.fetchone()
            if not result:
                return None
                
            return {
                'id': result[0],
                'title': result[1],
                'teaser_md': result[2],
                'body_md': result[3],
                'cliff_md': result[4],
                'status': result[5],
                'publish_at': result[6],
                'close_at': result[7],
                'idx': result[8]
            }
    except Exception as e:
        log.error(f"[MUC] Error getting first published episode: {e}")
        return None

def _get_episode_by_id(episode_id: int) -> Optional[Dict]:
    """Get episode by specific ID"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT id, title, teaser_md, body_md, cliff_md, status, 
                       publish_at, close_at, idx
                FROM muc_episodes 
                WHERE id = %s
            """, (episode_id,))
            
            result = cur.fetchone()
            if not result:
                return None
                
            return {
                'id': result[0],
                'title': result[1],
                'teaser_md': result[2],
                'body_md': result[3],
                'cliff_md': result[4],
                'status': result[5],
                'publish_at': result[6],
                'close_at': result[7],
                'idx': result[8]
            }
    except Exception as e:
        log.error(f"[MUC] Error getting episode by id {episode_id}: {e}")
        return None

def _get_next_episode_id(current_episode_id: int) -> Optional[int]:
    """Get the next episode ID in sequence by idx"""
    try:
        with _conn() as con, con.cursor() as cur:
            now = datetime.datetime.now(IST)
            
            # First get current episode's idx
            cur.execute("SELECT idx FROM muc_episodes WHERE id = %s", (current_episode_id,))
            result = cur.fetchone()
            if not result:
                return None
            
            current_idx = result[0]
            
            # Get next episode with higher idx
            cur.execute("""
                SELECT id FROM muc_episodes 
                WHERE idx > %s 
                  AND status IN ('published', 'voting')
                  AND (publish_at IS NULL OR publish_at <= %s)
                ORDER BY idx ASC 
                LIMIT 1
            """, (current_idx, now))
            
            result = cur.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        log.error(f"[MUC] Error getting next episode for {current_episode_id}: {e}")
        return None

def _update_last_seen_episode(user_id: int, episode_id: int):
    """Update user's last seen episode"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                UPDATE muc_user_engagement 
                SET last_seen_episode_id = %s
                WHERE user_id = %s
            """, (episode_id, user_id))
            con.commit()
    except Exception as e:
        log.error(f"[MUC] Error updating last seen episode for user {user_id}: {e}")

def _get_latest_episodes(limit: int = 5) -> List[Dict]:
    """Get the latest published episodes"""
    try:
        with _conn() as con, con.cursor() as cur:
            now = datetime.datetime.now(IST)
            
            cur.execute("""
                SELECT id, title, teaser_md, body_md, cliff_md, status, 
                       publish_at, close_at, idx
                FROM muc_episodes 
                WHERE status IN ('published', 'voting') 
                  AND (publish_at IS NULL OR publish_at <= %s)
                ORDER BY idx DESC, publish_at DESC, id DESC
                LIMIT %s
            """, (now, limit))
            
            results = cur.fetchall()
            episodes = []
            
            for result in results:
                episodes.append({
                    'id': result[0],
                    'title': result[1],
                    'teaser_md': result[2],
                    'body_md': result[3],
                    'cliff_md': result[4],
                    'status': result[5],
                    'publish_at': result[6],
                    'close_at': result[7],
                    'idx': result[8]
                })
            
            return episodes
            
    except Exception as e:
        log.error(f"[MUC] Error getting latest episodes: {e}")
        return []

def _get_episode_polls(episode_id: int) -> List[Dict]:
    """Get all polls for an episode with their options"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT p.id, p.prompt, p.layer, p.allow_multi,
                       po.id as option_id, po.opt_key, po.text, po.next_hint
                FROM muc_polls p
                LEFT JOIN muc_poll_options po ON p.id = po.poll_id
                WHERE p.episode_id = %s
                ORDER BY p.id, po.id
            """, (episode_id,))
            
            results = cur.fetchall()
            polls = {}
            
            for row in results:
                poll_id = row[0]
                if poll_id not in polls:
                    polls[poll_id] = {
                        'id': poll_id,
                        'prompt': row[1],
                        'layer': row[2],
                        'allow_multi': row[3],
                        'options': []
                    }
                
                if row[4]:  # option_id exists
                    polls[poll_id]['options'].append({
                        'id': row[4],
                        'opt_key': row[5],
                        'text': row[6],
                        'next_hint': row[7]
                    })
            
            return list(polls.values())
    except Exception as e:
        log.error(f"[MUC] Error getting episode polls: {e}")
        return []

def _get_user_votes(user_id: int, episode_id: int) -> Dict[int, int]:
    """Get user's votes for an episode, returns {poll_id: option_id}"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT v.poll_id, v.option_id
                FROM muc_votes v
                JOIN muc_polls p ON v.poll_id = p.id
                WHERE v.user_id = %s AND p.episode_id = %s
            """, (user_id, episode_id))
            
            return {row[0]: row[1] for row in cur.fetchall()}
    except Exception as e:
        log.error(f"[MUC] Error getting user votes: {e}")
        return {}

def _get_poll_results(poll_id: int) -> Dict:
    """Get voting results for a poll"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT option_id, COUNT(*) as vote_count
                FROM muc_votes 
                WHERE poll_id = %s
                GROUP BY option_id
                ORDER BY vote_count DESC
            """, (poll_id,))
            
            results = {}
            total_votes = 0
            
            for option_id, count in cur.fetchall():
                results[option_id] = count
                total_votes += count
            
            return {'votes': results, 'total': total_votes}
    except Exception as e:
        log.error(f"[MUC] Error getting poll results: {e}")
        return {'votes': {}, 'total': 0}

def _update_detective_score(user_id: int, points: int):
    """Add points to user's detective score"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                UPDATE muc_user_engagement 
                SET detective_score = detective_score + %s
                WHERE user_id = %s
            """, (points, user_id))
            con.commit()
    except Exception as e:
        log.error(f"[MUC] Error updating detective score: {e}")

def _update_last_seen_episode(user_id: int, episode_id: int):
    """Update user's last seen episode"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                UPDATE muc_user_engagement 
                SET last_seen_episode_id = %s
                WHERE user_id = %s
            """, (episode_id, user_id))
            con.commit()
    except Exception as e:
        log.error(f"[MUC] Error updating last seen episode: {e}")

# ==================== DIRECT ADMIN COMMANDS ====================

async def cmd_add_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to add new episode with optional poll"""
    user_id = update.effective_user.id
    
    if not _is_admin(user_id):
        return await update.message.reply_text("❌ You are not authorized to add episodes.")
    
    if len(context.args) < 2:
        return await update.message.reply_text(
            "📝 **Usage**: `/muc_add_episode <title> <content> [POLL:<question>|option1|option2|option3...]`\n\n"
            "**Example**: `/muc_add_episode \"Chapter 5: The Secret\" Sarah discovers something shocking... POLL:What should Sarah do next?|Tell her friend|Keep it secret|Investigate further|Confront the person`\n\n"
            "📚 **Format your content with**:\n"
            "• **Bold text** for emphasis\n"
            "• *Italic text* for thoughts\n"
            "• 🔥 *Cliffhanger text* for dramatic endings\n\n"
            "🗳️ **Poll Format** (optional):\n"
            "• Add `POLL:` at the end\n"
            "• Question followed by `|`\n"
            "• Separate options with `|`\n"
            "• Users will vote directly in the story!\n\n"
            "**No length limit** - episodes can be as long as you want!",
            parse_mode='Markdown'
        )
    
    title = context.args[0].strip('"\'')  # Remove quotes if present
    full_content = " ".join(context.args[1:])
    
    # Check if there's a poll in the content
    poll_data = None
    content = full_content
    
    if " POLL:" in full_content:
        parts = full_content.split(" POLL:", 1)
        content = parts[0].strip()
        poll_section = parts[1].strip()
        
        # Parse poll: question|option1|option2|option3...
        poll_parts = poll_section.split("|")
        if len(poll_parts) >= 3:  # At least question + 2 options
            poll_data = {
                'question': poll_parts[0].strip(),
                'options': [opt.strip() for opt in poll_parts[1:] if opt.strip()]
            }
    
    try:
        with _conn() as con, con.cursor() as cur:
            # Get next episode index
            cur.execute("SELECT COALESCE(MAX(idx), 0) + 1 FROM muc_episodes")
            next_idx = cur.fetchone()[0]
            
            # Insert new episode (using default series_id = 2)
            cur.execute("""
                INSERT INTO muc_episodes (series_id, idx, title, body_md, status, publish_at)
                VALUES (2, %s, %s, %s, 'published', NOW())
                RETURNING id
            """, (next_idx, title, content))
            
            episode_id = cur.fetchone()[0]
            
            # Add poll if provided
            poll_id = None
            if poll_data:
                cur.execute("""
                    INSERT INTO muc_polls (episode_id, prompt)
                    VALUES (%s, %s)
                    RETURNING id
                """, (episode_id, poll_data['question']))
                
                poll_id = cur.fetchone()[0]
                
                # Add poll options
                for idx, option_text in enumerate(poll_data['options']):
                    opt_key = f"opt_{idx + 1}"  # Generate option key like opt_1, opt_2, etc.
                    cur.execute("""
                        INSERT INTO muc_poll_options (poll_id, idx, opt_key, text)
                        VALUES (%s, %s, %s, %s)
                    """, (poll_id, idx, opt_key, option_text))
            
            con.commit()
            
            success_message = (
                f"✅ **Episode {next_idx} Added Successfully!**\n\n"
                f"📚 **Title**: {title}\n"
                f"🆔 **Episode ID**: {episode_id}\n"
                f"📅 **Published**: Now\n\n"
            )
            
            if poll_data:
                success_message += (
                    f"🗳️ **Poll Added**: {poll_data['question']}\n"
                    f"📊 **Options**: {len(poll_data['options'])} choices\n\n"
                )
            
            success_message += "Users can now read this episode in Midnight University Chronicles!"
            
            await update.message.reply_text(success_message, parse_mode='Markdown')
            
            log.info(f"Admin {user_id} added new MUC episode: {title}" + (" with poll" if poll_data else ""))
            
    except Exception as e:
        log.error(f"Error adding episode: {e}")
        await update.message.reply_text("❌ Failed to add episode. Please try again.")

async def cmd_delete_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to delete episode"""
    user_id = update.effective_user.id
    
    if not _is_admin(user_id):
        return await update.message.reply_text("❌ You are not authorized to delete episodes.")
    
    if not context.args:
        return await update.message.reply_text(
            "🗑️ **Usage**: `/muc_delete_episode <episode_id>`\n\n"
            "**Example**: `/muc_delete_episode 5`\n\n"
            "⚠️ **Warning**: This will permanently delete the episode and all its theories/votes!"
        )
    
    try:
        episode_id = int(context.args[0])
        
        with _conn() as con, con.cursor() as cur:
            # Check if episode exists
            cur.execute("SELECT title FROM muc_episodes WHERE id = %s", (episode_id,))
            episode = cur.fetchone()
            
            if not episode:
                return await update.message.reply_text("❌ Episode not found.")
            
            # Delete episode and all related data
            cur.execute("DELETE FROM muc_votes WHERE poll_id IN (SELECT id FROM muc_polls WHERE episode_id = %s)", (episode_id,))
            cur.execute("DELETE FROM muc_polls WHERE episode_id = %s", (episode_id,))
            cur.execute("DELETE FROM muc_theories WHERE episode_id = %s", (episode_id,))
            cur.execute("DELETE FROM muc_episodes WHERE id = %s", (episode_id,))
            con.commit()
            
            await update.message.reply_text(
                f"🗑️ **Episode Deleted Successfully!**\n\n"
                f"📚 **Title**: {episode[0]}\n"
                f"🆔 **Episode ID**: {episode_id}\n\n"
                f"All related theories and votes have been removed.",
                parse_mode='Markdown'
            )
            
            log.info(f"Admin {user_id} deleted MUC episode: {episode[0]}")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid episode ID. Please provide a number.")
    except Exception as e:
        log.error(f"Error deleting episode: {e}")
        await update.message.reply_text("❌ Failed to delete episode. Please try again.")

async def cmd_delete_theory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to delete inappropriate theories"""
    user_id = update.effective_user.id
    
    if not _is_admin(user_id):
        return await update.message.reply_text("❌ You are not authorized to delete theories.")
    
    if not context.args:
        return await update.message.reply_text(
            "🗑️ **Usage**: `/muc_delete_theory <theory_id>`\n\n"
            "**Example**: `/muc_delete_theory 15`\n\n"
            "💡 **To find theory IDs**: Use admin dashboard or check 'View All Theories' section"
        )
    
    try:
        theory_id = int(context.args[0])
        
        with _conn() as con, con.cursor() as cur:
            # Check if theory exists and get details
            cur.execute("""
                SELECT t.text, u.first_name, e.title 
                FROM muc_theories t 
                LEFT JOIN users u ON t.user_id = u.user_id 
                LEFT JOIN muc_episodes e ON t.episode_id = e.id 
                WHERE t.id = %s
            """, (theory_id,))
            
            theory = cur.fetchone()
            
            if not theory:
                return await update.message.reply_text("❌ Theory not found.")
            
            # Delete theory
            cur.execute("DELETE FROM muc_theories WHERE id = %s", (theory_id,))
            con.commit()
            
            theory_preview = theory[0][:100] + "..." if len(theory[0]) > 100 else theory[0]
            
            await update.message.reply_text(
                f"🗑️ **Theory Deleted Successfully!**\n\n"
                f"💭 **Content**: {theory_preview}\n"
                f"👤 **By**: {theory[1] or 'Unknown'}\n"
                f"📚 **Episode**: {theory[2] or 'Unknown'}\n"
                f"🆔 **Theory ID**: {theory_id}",
                parse_mode='Markdown'
            )
            
            log.info(f"Admin {user_id} deleted MUC theory ID {theory_id}")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid theory ID. Please provide a number.")
    except Exception as e:
        log.error(f"Error deleting theory: {e}")
        await update.message.reply_text("❌ Failed to delete theory. Please try again.")

# ==================== ADMIN FUNCTIONS ====================

def get_admin_ids():
    """Get admin IDs from environment with proper parsing"""
    admin_str = os.getenv("ADMIN_IDS", "647778434")  # fallback to default
    # Clean up quotes and other characters
    admin_str = admin_str.replace('"', '').replace("'", "").replace(",", " ")
    try:
        return {int(x.strip()) for x in admin_str.split() if x.strip().isdigit()}
    except ValueError:
        # Fallback to default if parsing fails
        return {647778434}

def _is_admin(user_id: int) -> bool:
    """Check if user is admin using proper admin ID parsing"""
    admin_ids = get_admin_ids()
    return user_id in admin_ids

async def muc_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin dashboard for managing MUC episodes and polls"""
    try:
        user_id = update.effective_user.id
        
        if not _is_admin(user_id):
            if update.callback_query:
                await update.callback_query.answer("❌ Admin access required.", show_alert=True)
            else:
                await update.message.reply_text("❌ Admin access required.")
            return
        
        with _conn() as con, con.cursor() as cur:
            # Get latest episodes with voting stats
            cur.execute("""
                SELECT e.idx, e.title, e.status, 
                       COUNT(DISTINCT v.id) as total_votes,
                       COUNT(DISTINCT t.id) as total_theories
                FROM muc_episodes e
                LEFT JOIN muc_polls p ON e.id = p.episode_id
                LEFT JOIN muc_votes v ON p.id = v.poll_id
                LEFT JOIN muc_theories t ON e.id = t.episode_id
                GROUP BY e.id, e.idx, e.title, e.status
                ORDER BY e.idx DESC
                LIMIT 5
            """)
            recent_episodes = cur.fetchall()
        
        admin_text = f"""🔧 **MUC ADMIN DASHBOARD**

📊 **Recent Episodes:**
"""
        
        for idx, title, status, votes, theories in recent_episodes:
            admin_text += f"**Episode {idx}**: {title}\n"
            admin_text += f"   Status: {status} | Votes: {votes} | Theories: {theories}\n\n"
        
        admin_text += "🎯 **Admin Actions:**"
        
        keyboard = [
            [InlineKeyboardButton("📝 Create New Episode", callback_data="muc_admin:create_episode")],
            [InlineKeyboardButton("📊 View Voting Results", callback_data="muc_admin:voting_results")],
            [InlineKeyboardButton("🔍 View All Theories", callback_data="muc_admin:all_theories")], 
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                admin_text, parse_mode='Markdown', reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                admin_text, parse_mode='Markdown', reply_markup=reply_markup
            )
            
    except Exception as e:
        log.error(f"[MUC] Error in admin dashboard: {e}")
        error_msg = "🚨 Admin dashboard error."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def admin_create_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin function to guide episode creation"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if not _is_admin(user_id):
            await query.edit_message_text("❌ Admin access required.")
            return
        
        # Get current highest episode number
        with _conn() as con, con.cursor() as cur:
            cur.execute("SELECT MAX(idx) FROM muc_episodes")
            result = cur.fetchone()
            next_idx = (result[0] or 0) + 1
        
        create_text = f"""📝 **CREATE EPISODE {next_idx}**

🎯 **Continue the Wattpad-style story!**

**Current Status**: 
- Episode 7 ended with community choice
- {next_idx - 7} episodes beyond original "Week 1" limit
- Story now unlimited and ongoing! ✅

**Manual Creation Process**:
1. Check voting results from latest episode
2. Read community theories for inspiration  
3. Write Episode {next_idx} based on community input
4. Add new polls for next story direction

**Admin Actions:**"""

        keyboard = [
            [InlineKeyboardButton("📊 View Latest Results", callback_data="muc_admin:voting_results")],
            [InlineKeyboardButton("🔍 Read All Theories", callback_data="muc_admin:all_theories")],
            [InlineKeyboardButton("📋 Episode Template", callback_data="muc_admin:template")],
            [InlineKeyboardButton("🏠 Back to Admin", callback_data="muc_admin:dashboard")]
        ]
        
        await query.edit_message_text(
            create_text, parse_mode='Markdown', 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"[MUC] Error in admin_create_episode: {e}")
        await query.edit_message_text("🚨 Error in episode creation.")

async def admin_voting_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed voting results for latest episode"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        if not _is_admin(user_id):
            await query.edit_message_text("❌ Admin access required.")
            return
        
        # Get latest episode voting results
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT e.idx, e.title, p.prompt, po.text, COUNT(v.id) as votes
                FROM muc_episodes e
                JOIN muc_polls p ON e.id = p.episode_id
                JOIN muc_poll_options po ON p.id = po.poll_id
                LEFT JOIN muc_votes v ON po.id = v.option_id
                WHERE e.idx = (SELECT MAX(idx) FROM muc_episodes)
                GROUP BY e.idx, e.title, p.id, p.prompt, po.id, po.text
                ORDER BY p.id, votes DESC
            """)
            
            results = cur.fetchall()
        
        if not results:
            await query.edit_message_text("📊 No voting data available.")
            return
        
        episode_idx = results[0][0]
        episode_title = results[0][1]
        
        results_text = f"""📊 **LATEST VOTING RESULTS**
**Episode {episode_idx}: {episode_title}**

**Community Choices:**

"""
        
        current_prompt = None
        for idx, title, prompt, option_text, votes in results:
            if prompt != current_prompt:
                results_text += f"\n❓ **{prompt}**\n"
                current_prompt = prompt
            
            results_text += f"▫️ {option_text}: **{votes} votes**\n"
        
        results_text += f"\n💡 **Use these results to write Episode {episode_idx + 1}!**"
        
        keyboard = [
            [InlineKeyboardButton("🔍 View Community Theories", callback_data="muc_admin:all_theories")],
            [InlineKeyboardButton("📝 Create Next Episode", callback_data="muc_admin:create_episode")],
            [InlineKeyboardButton("🏠 Back to Admin", callback_data="muc_admin:dashboard")]
        ]
        
        await query.edit_message_text(
            results_text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"[MUC] Error in admin_voting_results: {e}")
        await query.edit_message_text("🚨 Error loading voting results.")

# Removed handle_theory_like function - likes feature completely removed as requested

# ==================== SEQUENTIAL NAVIGATION HANDLERS ====================

async def start_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start reading from the first episode"""
    user_id = update.effective_user.id
    
    try:
        # Get first published episode
        first_episode = _get_first_published_episode()
        
        if not first_episode:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "📚 No episodes are available yet. Check back soon for the first chapter!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]])
            )
            return
        
        # Show the first episode
        await show_single_episode(update, context, first_episode['id'])
        
    except Exception as e:
        log.error(f"[MUC] Error in start_reading: {e}")
        await update.callback_query.answer("❌ Error starting story")

async def continue_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Continue reading from last seen episode"""
    user_id = update.effective_user.id
    
    try:
        # Get user's last seen episode
        user_stats = _ensure_user_engagement(user_id)
        last_seen_id = user_stats.get('last_seen_episode_id')
        
        if not last_seen_id:
            # No progress, start from beginning
            await start_reading(update, context)
            return
        
        # Check if episode still exists and is published
        episode = _get_episode_by_id(last_seen_id)
        if not episode or episode['status'] not in ('published', 'voting'):
            # Episode no longer available, start from beginning
            await start_reading(update, context)
            return
        
        # Show the last seen episode
        await show_single_episode(update, context, episode['id'])
        
    except Exception as e:
        log.error(f"[MUC] Error in continue_reading: {e}")
        await update.callback_query.answer("❌ Error continuing story")

async def next_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navigate to next episode in sequence"""
    user_id = update.effective_user.id
    
    try:
        # Extract current episode ID from callback data
        callback_data = update.callback_query.data
        current_id = int(callback_data.split(':')[-1])
        
        # Get next episode ID
        next_id = _get_next_episode_id(current_id)
        
        if not next_id:
            # No more episodes available
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "🎉 **You're all caught up!**\n\n"
                "You've reached the latest episode of Midnight University Chronicles. "
                "Check back soon for the next thrilling chapter!\n\n"
                "✨ *Your choices are shaping the destiny of Midnight University...* ✨",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 Episodes Archive", callback_data="muc:archive")],
                    [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
                ])
            )
            return
        
        # Show next episode
        await show_single_episode(update, context, next_id)
        
    except Exception as e:
        log.error(f"[MUC] Error in next_episode: {e}")
        await update.callback_query.answer("❌ Error loading next episode")

async def show_episodes_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show archive of all available episodes"""
    user_id = update.effective_user.id
    
    try:
        episodes = _get_latest_episodes(limit=10)
        
        if not episodes:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "📚 **Episodes Archive**\n\n"
                "No episodes are available yet. Check back soon for the first chapter!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]])
            )
            return
        
        # Build episodes list
        archive_text = "📚 **Episodes Archive**\n\n"
        keyboard = []
        
        for ep in episodes:
            status_emoji = "📖" if ep['status'] == 'published' else "🗳️" if ep['status'] == 'voting' else "⏳"
            archive_text += f"{status_emoji} *{ep['title']}*\n"
            keyboard.append([InlineKeyboardButton(f"{status_emoji} {ep['title']}", callback_data=f"muc:episode:{ep['id']}")])
        
        archive_text += "\n*Choose any episode to jump directly to it*"
        
        keyboard.append([InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")])
        
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            archive_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"[MUC] Error showing episodes archive: {e}")
        await update.callback_query.answer("❌ Error loading archive")

async def show_single_episode(update: Update, context: ContextTypes.DEFAULT_TYPE, episode_id: int):
    """Show a single episode with Next button navigation"""
    user_id = update.effective_user.id
    
    try:
        # Get episode data
        episode = _get_episode_by_id(episode_id)
        if not episode:
            await update.callback_query.answer("❌ Episode not found")
            return
        
        # Update user's last seen episode
        _update_last_seen_episode(user_id, episode_id)
        
        # Build episode content (no pagination, show full episode)
        episode_text = f"📖 **{episode['title']}**\n\n"
        
        # Add full episode content
        if episode['body_md']:
            episode_text += f"{episode['body_md']}\n\n"
        
        # Get and display polls for this episode
        episode_polls = _get_episode_polls(episode_id)
        user_votes = _get_user_votes(user_id, episode_id)
        
        keyboard = []
        
        # Add poll voting/results
        for poll in episode_polls:
            user_voted_for_poll = poll['id'] in user_votes if user_votes else False
            
            episode_text += f"❓ **{poll['prompt']}**\n\n"
            
            if not user_voted_for_poll:
                # Show voting options as clickable buttons
                for option in poll['options']:
                    button_text = f"▫️ {option['text']}"
                    callback_data = f"muc:poll:{poll['id']}:opt:{option['id']}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            else:
                # Show user's choice and current results
                voted_option = next((opt for opt in poll['options'] if opt['id'] == user_votes[poll['id']]), None)
                if voted_option:
                    episode_text += f"✅ Your choice: *{voted_option['text']}*\n\n"
                
                # Show current voting results
                results = _get_poll_results(poll['id'])
                episode_text += f"📊 **Current Results:**\n"
                
                for option in poll['options']:
                    count = results.get(option['id'], 0)
                    percentage = (count / max(sum(results.values()), 1)) * 100
                    bar = "█" * int(percentage // 10) + "░" * (10 - int(percentage // 10))
                    episode_text += f"{option['text']}: {count} votes ({percentage:.1f}%)\n{bar}\n\n"
        
        # Add navigation buttons
        nav_buttons = []
        
        # Check if there's a next episode
        next_id = _get_next_episode_id(episode_id)
        if next_id:
            nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"muc:next:{episode_id}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # Add other action buttons
        keyboard.extend([
            [InlineKeyboardButton("💭 Submit Your Theory", callback_data=f"muc:theories:{episode_id}")],
            [InlineKeyboardButton("🔍 View All Theories", callback_data=f"muc:view_theories:{episode_id}")],
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send response
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            episode_text, parse_mode='Markdown', reply_markup=reply_markup
        )
        
    except Exception as e:
        log.error(f"[MUC] Error showing single episode {episode_id}: {e}")
        await update.callback_query.answer("❌ Error loading episode")

# ==================== MAIN MENU HANDLER ====================

async def muc_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main Midnight University Chronicles menu"""
    user_id = update.effective_user.id
    
    try:
        # Get user engagement stats
        user_stats = _ensure_user_engagement(user_id)
        
        # Simple episode status
        first_episode = _get_first_published_episode()
        if first_episode:
            episode_status = "📖 New episode available!"
            episode_desc = "Read: Episode"
        else:
            episode_status = "⏰ Episode coming soon"
            episode_desc = "Stay tuned detective"
        
        # Build menu text
        menu_text = f"""🌙 **MIDNIGHT UNIVERSITY CHRONICLES** 🌙
*Where every choice echoes in the darkness...*

📊 **Detective Profile:**
🔍 Detective Score: **{user_stats['detective_score']}** points
🔥 Investigation Streak: **{user_stats['streak_days']}** days

📺 **Current Episode:**
{episode_status}
{episode_desc}

🎯 What would you like to investigate?"""

        # Build keyboard with all available episodes
        keyboard = []
        
        # Add simple Read Episode button
        if first_episode:
            keyboard.append([InlineKeyboardButton("📖 Read Episode", callback_data="muc:start")])
        else:
            keyboard.append([InlineKeyboardButton("📚 No Episodes Yet", callback_data="muc:help")])
        
        keyboard.extend([
            [InlineKeyboardButton("💭 Submit Theory", callback_data="muc:theories:17")],
            [InlineKeyboardButton("📊 View Results", callback_data="muc:results:6")],
            [InlineKeyboardButton("🏆 Detective Leaderboard", callback_data="muc:leaderboard")],
            [InlineKeyboardButton("❓ How to Play", callback_data="muc:help")]
        ])
        
        # Admin button for admins only
        if _is_admin(user_id):
            keyboard.append([InlineKeyboardButton("🔧 Admin Dashboard", callback_data="muc_admin:dashboard")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send response
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                menu_text, parse_mode='Markdown', reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                menu_text, parse_mode='Markdown', reply_markup=reply_markup
            )
        
    except Exception as e:
        log.error(f"[MUC] Error in muc_menu: {e}")
        error_msg = "🚨 Detective system temporarily offline. Try again in a moment."
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

# ==================== EPISODE DISPLAY HANDLER ====================

async def show_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display episode content with new sequential navigation (redirects to show_single_episode)"""
    try:
        query = update.callback_query
        
        # Extract episode ID from callback data (ignore old page parameter)
        parts = query.data.split(':')
        episode_id = int(parts[2])
        
        # Use the new sequential navigation system
        await show_single_episode(update, context, episode_id)
        
    except Exception as e:
        log.error(f"[MUC] Error in show_episode: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text("🚨 Error loading episode. Please try again.")
        else:
            await update.message.reply_text("🚨 Error loading episode. Please try again.")

# ==================== VOTING SYSTEM ====================

async def handle_poll_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process poll votes with callback pattern: muc:poll:<poll_id>:opt:<opt_id>"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        # Parse callback data: muc:poll:<poll_id>:opt:<opt_id>
        parts = query.data.split(':')
        if len(parts) != 5:
            await query.edit_message_text("❌ Invalid vote format")
            return
        
        poll_id = int(parts[2])
        option_id = int(parts[4])
        
        # Verify poll and option exist
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT p.episode_id, p.prompt, po.text
                FROM muc_polls p
                JOIN muc_poll_options po ON p.id = po.poll_id
                WHERE p.id = %s AND po.id = %s
            """, (poll_id, option_id))
            
            result = cur.fetchone()
            if not result:
                await query.edit_message_text("❌ Invalid poll or option")
                return
            
            episode_id, poll_prompt, option_text = result
            
            # Try to insert vote (will fail if user already voted due to UNIQUE constraint)
            try:
                cur.execute("""
                    INSERT INTO muc_votes (poll_id, option_id, user_id)
                    VALUES (%s, %s, %s)
                """, (poll_id, option_id, user_id))
                
                con.commit()
                
                # Award points for voting
                _update_detective_score(user_id, 10)
                
                # Success feedback
                feedback_text = f"""✅ **Vote Recorded!**
                
❓ *{poll_prompt}*
🗳️ Your choice: **{option_text}**

🔍 +10 Detective Points earned!

Your choice is now locked in. The story will unfold based on the community's collective decisions."""

                keyboard = [
                    [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")],
                    [InlineKeyboardButton("📖 Continue Reading", callback_data=f"muc:episode:{episode_id}")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    feedback_text, parse_mode='Markdown', reply_markup=reply_markup
                )
                
            except Exception as db_error:
                if "duplicate key" in str(db_error).lower() or "unique constraint" in str(db_error).lower():
                    # User already voted
                    await query.edit_message_text(
                        "⚠️ You've already voted on this choice! Your original vote stands.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
                        ])
                    )
                else:
                    raise db_error
                    
    except Exception as e:
        log.error(f"[MUC] Error in handle_poll_vote: {e}")
        await query.edit_message_text("🚨 Error recording vote. Please try again.")

# ==================== RESULTS DISPLAY ====================

async def show_poll_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show voting results with percentages and community choices"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Extract episode ID from callback data
        episode_id = int(query.data.split(':')[2])
        user_id = update.effective_user.id
        
        # Get episode and polls
        episode = _get_current_episode()
        if not episode or episode['id'] != episode_id:
            with _conn() as con, con.cursor() as cur:
                cur.execute("SELECT title FROM muc_episodes WHERE id = %s", (episode_id,))
                result = cur.fetchone()
                episode_title = result[0] if result else "Unknown Episode"
        else:
            episode_title = episode['title']
        
        polls = _get_episode_polls(episode_id)
        user_votes = _get_user_votes(user_id, episode_id)
        
        if not polls:
            await query.edit_message_text("📊 No voting results available for this episode.")
            return
        
        results_text = f"📊 **VOTING RESULTS**\n*{episode_title}*\n\n"
        
        for poll in polls:
            results = _get_poll_results(poll['id'])
            
            results_text += f"❓ **{poll['prompt']}**\n"
            
            if results['total'] == 0:
                results_text += "No votes yet.\n\n"
                continue
            
            # Sort options by vote count
            sorted_options = sorted(poll['options'], 
                                  key=lambda x: results['votes'].get(x['id'], 0), 
                                  reverse=True)
            
            for i, option in enumerate(sorted_options):
                votes = results['votes'].get(option['id'], 0)
                percentage = (votes / results['total'] * 100) if results['total'] > 0 else 0
                
                # Mark winning choice
                if i == 0 and votes > 0:
                    prefix = "👑"
                else:
                    prefix = "▫️"
                
                # Mark user's choice
                if poll['id'] in user_votes and user_votes[poll['id']] == option['id']:
                    choice_marker = " ← YOUR CHOICE"
                else:
                    choice_marker = ""
                
                results_text += f"{prefix} {option['text']}: {votes} votes ({percentage:.1f}%){choice_marker}\n"
            
            results_text += f"\n💫 Total votes: {results['total']}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📖 Read Episode", callback_data=f"muc:episode:{episode_id}")],
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            results_text, parse_mode='Markdown', reply_markup=reply_markup
        )
        
    except Exception as e:
        log.error(f"[MUC] Error in show_poll_results: {e}")
        await query.edit_message_text("🚨 Error loading results. Please try again.")

# ==================== THEORY SUBMISSION ====================

async def handle_theory_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle theory submission for mysteries"""
    try:
        if update.callback_query:
            # Starting theory submission
            query = update.callback_query
            await query.answer()
            
            episode_id = int(query.data.split(':')[2])
            
            # Check if user can submit (rate limiting)
            user_id = update.effective_user.id
            today = datetime.date.today()
            
            with _conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM muc_theories 
                    WHERE user_id = %s AND episode_id = %s 
                      AND DATE(created_at) = %s
                """, (user_id, episode_id, today))
                
                theories_today = cur.fetchone()[0]
                
                if theories_today >= 3:  # Limit 3 theories per episode per day
                    await query.edit_message_text(
                        "⚠️ You've reached the daily limit of 3 theories per episode. Come back tomorrow!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
                        ])
                    )
                    return
            
            # Request theory input
            if not await claim_or_reject(update, context, "muc", "theory_submit"):
                return
            
            context.user_data['muc_episode_id'] = episode_id
            
            await query.edit_message_text(
                "🔍 **Share Your Theory**\n\nWhat do you think is really happening? Who is the culprit? What are their motives?\n\n📝 Type your theory (max 500 characters):",
                reply_markup=make_cancel_kb()
            )
            
        else:
            # Processing theory text
            if not context.user_data.get('muc_episode_id'):
                await update.message.reply_text("❌ Theory session expired. Please start again.")
                return
            
            theory_text = update.message.text.strip()
            
            # Validate theory length
            if len(theory_text) < 10:
                await update.message.reply_text(
                    "🤔 Your theory seems a bit short. Can you elaborate? (Minimum 10 characters)",
                    reply_markup=make_cancel_kb()
                )
                return
            
            if len(theory_text) > 500:
                await update.message.reply_text(
                    f"📝 Please keep your theory under 500 characters. Current: {len(theory_text)} characters.",
                    reply_markup=make_cancel_kb()
                )
                return
            
            # Save theory
            user_id = update.effective_user.id
            episode_id = context.user_data['muc_episode_id']
            
            try:
                with _conn() as con, con.cursor() as cur:
                    cur.execute("""
                        INSERT INTO muc_theories (episode_id, user_id, text)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (episode_id, user_id, theory_text))
                    
                    theory_id = cur.fetchone()[0]
                    con.commit()
                
                # Award points for theory submission
                _update_detective_score(user_id, 25)
                
                clear_state(context)
                
                success_text = f"""✅ **Theory Submitted!**

🔍 Your investigation theory has been recorded in the case files.

🏆 +25 Detective Points earned!

🎭 Your theory will be shared with other detectives and they can like theories they find compelling."""

                keyboard = [
                    [InlineKeyboardButton("📋 View All Theories", callback_data=f"muc:view_theories:{episode_id}")],
                    [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
                ]
                
                await update.message.reply_text(
                    success_text, parse_mode='Markdown', 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            except Exception as db_error:
                log.error(f"[MUC] Error saving theory: {db_error}")
                await update.message.reply_text("🚨 Error saving theory. Please try again.")
                
    except Exception as e:
        log.error(f"[MUC] Error in handle_theory_submission: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text("🚨 Error processing theory submission.")
        else:
            await update.message.reply_text("🚨 Error processing theory submission.")

async def view_theories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display existing theories with like counts"""
    try:
        query = update.callback_query
        await query.answer()
        
        episode_id = int(query.data.split(':')[2])
        
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT text, likes, created_at
                FROM muc_theories 
                WHERE episode_id = %s
                ORDER BY likes DESC, created_at DESC
                LIMIT 10
            """, (episode_id,))
            
            theories = cur.fetchall()
        
        if not theories:
            await query.edit_message_text(
                "🔍 No theories submitted yet. Be the first detective to share your insights!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💭 Submit Theory", callback_data=f"muc:theories:{episode_id}")],
                    [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
                ])
            )
            return
        
        theories_text = "🔍 **DETECTIVE THEORIES**\n\n"
        
        for i, (text, likes, created_at) in enumerate(theories, 1):
            # Truncate long theories for display
            display_text = text[:150] + "..." if len(text) > 150 else text
            
            theories_text += f"**Theory #{i}**\n"
            theories_text += f"💭 {display_text}\n"
            theories_text += f"👍 {likes} likes\n\n"
        
        keyboard = [
            [InlineKeyboardButton("💭 Submit Your Theory", callback_data=f"muc:theories:{episode_id}")],
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
        ]
        
        await query.edit_message_text(
            theories_text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"[MUC] Error in view_theories: {e}")
        await query.edit_message_text("🚨 Error loading theories. Please try again.")

# ==================== LEADERBOARD ====================

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detective leaderboard"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        
        with _conn() as con, con.cursor() as cur:
            # Get top detectives
            cur.execute("""
                SELECT user_id, detective_score, streak_days
                FROM muc_user_engagement
                WHERE detective_score > 0
                ORDER BY detective_score DESC
                LIMIT 10
            """, ())
            
            top_detectives = cur.fetchall()
            
            # Get user's rank
            cur.execute("""
                SELECT COUNT(*) + 1 as rank
                FROM muc_user_engagement
                WHERE detective_score > (
                    SELECT detective_score 
                    FROM muc_user_engagement 
                    WHERE user_id = %s
                )
            """, (user_id,))
            
            user_rank = cur.fetchone()[0]
            
            # Get user's stats
            user_stats = _ensure_user_engagement(user_id)
        
        leaderboard_text = "🏆 **DETECTIVE LEADERBOARD**\n*Top Mystery Solvers*\n\n"
        
        if not top_detectives:
            leaderboard_text += "🔍 No detectives on the board yet. Be the first!"
        else:
            for i, (uid, score, streak) in enumerate(top_detectives, 1):
                if i == 1:
                    medal = "🥇"
                elif i == 2:
                    medal = "🥈"
                elif i == 3:
                    medal = "🥉"
                else:
                    medal = f"{i}."
                
                # Anonymize other users
                if uid == user_id:
                    detective_name = "YOU"
                else:
                    detective_name = f"Detective #{uid % 1000}"
                
                leaderboard_text += f"{medal} {detective_name}: **{score}** points (🔥{streak} streak)\n"
        
        leaderboard_text += f"\n🎯 **Your Position:**\n"
        leaderboard_text += f"📍 Rank #{user_rank}\n"
        leaderboard_text += f"🔍 Score: {user_stats['detective_score']} points\n"
        leaderboard_text += f"🔥 Streak: {user_stats['streak_days']} days"
        
        keyboard = [
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
        ]
        
        await query.edit_message_text(
            leaderboard_text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"[MUC] Error in show_leaderboard: {e}")
        await query.edit_message_text("🚨 Error loading leaderboard. Please try again.")

# ==================== HELP SYSTEM ====================

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show how to play guide"""
    try:
        query = update.callback_query
        await query.answer()
        
        help_text = """❓ **HOW TO PLAY**
*Midnight University Chronicles*

🌙 **The Mystery Unfolds:**
• New episodes are released regularly
• Each episode advances the dark story
• Your choices determine what happens next

🔍 **Detective Actions:**
• **Read Episodes** - Follow the mystery
• **Vote on Choices** - Shape the story direction  
• **Submit Theories** - Share your deductions
• **Earn Points** - Build your detective reputation

🏆 **Scoring System:**
• +10 points for voting on story choices
• +25 points for submitting theories
• Build streaks by participating daily
• Climb the detective leaderboard

💫 **Community Impact:**
• Your votes influence story direction
• Popular theories may influence future episodes
• Collaborate with fellow detectives
• Uncover the university's dark secrets together

🎭 Ready to solve the mystery?"""

        keyboard = [
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="muc:menu")]
        ]
        
        await query.edit_message_text(
            help_text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"[MUC] Error in show_help: {e}")
        await query.edit_message_text("🚨 Error loading help. Please try again.")

# ==================== COMMAND REGISTRATION ====================

def register(app):
    """Register all Midnight University Chronicles handlers"""
    try:
        # Command handler for /chronicles
        app.add_handler(CommandHandler("chronicles", muc_menu))
        
        # Callback query handlers for all muc: patterns
        app.add_handler(CallbackQueryHandler(muc_menu, pattern=r"^muc:menu$"))
        app.add_handler(CallbackQueryHandler(start_reading, pattern=r"^muc:start$"))
        app.add_handler(CallbackQueryHandler(continue_reading, pattern=r"^muc:continue$"))
        app.add_handler(CallbackQueryHandler(next_episode, pattern=r"^muc:next:\d+$"))
        app.add_handler(CallbackQueryHandler(show_episodes_archive, pattern=r"^muc:archive$"))
        app.add_handler(CallbackQueryHandler(show_episode, pattern=r"^muc:episode:\d+(:\d+)?$"))  # Support both muc:episode:id and muc:episode:id:page
        app.add_handler(CallbackQueryHandler(handle_poll_vote, pattern=r"^muc:poll:\d+:opt:\d+$"))
        app.add_handler(CallbackQueryHandler(show_poll_results, pattern=r"^muc:results:\d+$"))
        app.add_handler(CallbackQueryHandler(handle_theory_submission, pattern=r"^muc:theories:\d+$"))
        app.add_handler(CallbackQueryHandler(view_theories, pattern=r"^muc:view_theories:\d+$"))
        app.add_handler(CallbackQueryHandler(show_leaderboard, pattern=r"^muc:leaderboard$"))
        app.add_handler(CallbackQueryHandler(show_help, pattern=r"^muc:help$"))
        
        # Admin handlers
        app.add_handler(CallbackQueryHandler(muc_admin_dashboard, pattern=r"^muc_admin:dashboard$"))
        app.add_handler(CallbackQueryHandler(admin_create_episode, pattern=r"^muc_admin:create_episode$"))
        app.add_handler(CallbackQueryHandler(admin_voting_results, pattern=r"^muc_admin:voting_results$"))
        app.add_handler(CommandHandler("muc_admin", muc_admin_dashboard))
        
        # Theory likes handler
        # Removed theory like handler - likes feature removed as requested
        
        # Text handler for theory submission (requires state)
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.VIA_BOT,
            requires_state("muc", "theory_submit")(handle_theory_submission)
        ), group=-2)  # High priority for text framework integration
        
        # Admin commands for direct episode management
        app.add_handler(CommandHandler("muc_add_episode", cmd_add_episode))
        app.add_handler(CommandHandler("muc_delete_episode", cmd_delete_episode))  
        app.add_handler(CommandHandler("muc_delete_theory", cmd_delete_theory))
        
        log.info("[MUC] ✅ Midnight University Chronicles handlers registered successfully")
        
    except Exception as e:
        log.error(f"[MUC] ❌ Failed to register handlers: {e}")
        raise