# handlers/sensual_stories.py - Sensual Stories feature for premium content
import os
import logging
from datetime import datetime, timedelta

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.helpers import escape_markdown

import registration as reg
from handlers.text_framework import claim_or_reject, requires_state, clear_state

log = logging.getLogger(__name__)

# Get admin IDs from environment
def get_admin_ids():
    admin_str = os.getenv("ADMIN_IDS", "647778434")  # fallback to default
    # Clean up quotes and other characters
    admin_str = admin_str.replace('"', '').replace("'", "").replace(",", " ")
    try:
        return {int(x.strip()) for x in admin_str.split() if x.strip().isdigit()}
    except ValueError:
        # Fallback to default if parsing fails
        return {647778434}

# ---- Database Setup ----
def ensure_sensual_table():
    """Create sensual_stories table if it doesn't exist"""
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sensual_stories (
                    id BIGSERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    is_featured BOOLEAN DEFAULT FALSE
                );
            """)
            
            # Create reactions table for engagement tracking
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sensual_reactions (
                    id BIGSERIAL PRIMARY KEY,
                    story_id BIGINT REFERENCES sensual_stories(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    reaction TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(story_id, user_id)
                );
            """)
            con.commit()
            log.info("✅ Sensual stories tables created successfully")
    except Exception as e:
        log.error(f"Failed to create sensual stories tables: {e}")

# ---- Helper Functions ----
def format_story_preview(content, is_premium, max_chars=800):
    """Format story content - everyone gets full access for now"""
    # Everyone gets full content for 1 month free period
    return content

def _story_author(story_id: int):
    """Get story author ID"""
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT 1 FROM sensual_stories WHERE id=%s", (story_id,))
            row = cur.fetchone()
            return row is not None
    except Exception:
        return False

def _can_delete_story(story_id: int, user_id: int) -> bool:
    """Check if user can delete story (admin only for now)"""
    if not user_id:
        return False
    admin_ids = get_admin_ids()
    return user_id in admin_ids

def _create_pagination_kb(current_index: int, total_stories: int, viewer_id: int, stories: list) -> InlineKeyboardMarkup:
    """Create pagination keyboard for story navigation"""
    admin_ids = get_admin_ids()
    is_admin = viewer_id in admin_ids
    rows = []
    
    # Get current story info for delete button
    current_story_id = stories[current_index][0]
    
    # Delete Story button (only for admin)
    if _can_delete_story(current_story_id, viewer_id):
        rows.append([InlineKeyboardButton("🗑 Delete Story", callback_data=f"sensual:del:{current_story_id}")])
    
    # Navigation buttons
    nav_buttons = []
    
    # Previous button (if not first story)
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ Previous", callback_data=f"sensual:nav:{current_index-1}"))
    
    # Next button (if not last story)
    if current_index < total_stories - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡", callback_data=f"sensual:nav:{current_index+1}"))
    
    # Add navigation row if we have navigation buttons
    if nav_buttons:
        rows.append(nav_buttons)
    
    # Smart back button - admin goes to admin panel, regular users go to public feed
    if is_admin:
        rows.append([InlineKeyboardButton("⬅ Back to Admin", callback_data="sensual:admin:back")])
    else:
        rows.append([InlineKeyboardButton("⬅ Back to Feed", callback_data="pf:menu")])
    
    return InlineKeyboardMarkup(rows)


def _story_kb(story_id: int, viewer_id: int) -> InlineKeyboardMarkup:
    """Create keyboard for stories - free access for everyone (legacy, for admin view)"""
    admin_ids = get_admin_ids()
    is_admin = viewer_id in admin_ids
    rows = []
    
    # Delete Story button (only for admin)
    if _can_delete_story(story_id, viewer_id):
        rows.append([InlineKeyboardButton("🗑 Delete Story", callback_data=f"sensual:del:{story_id}")])
    
    # Smart back button - admin goes to admin panel, regular users go to public feed
    if is_admin:
        rows.append([InlineKeyboardButton("⬅ Back to Admin", callback_data="sensual:admin:back")])
    else:
        rows.append([InlineKeyboardButton("⬅ Back to Feed", callback_data="pf:menu")])
    
    return InlineKeyboardMarkup(rows)


async def _show_story_by_index(update, context, story_index: int, stories: list, user_id: int):
    """Show a specific story by index with appropriate navigation"""
    if not stories or story_index < 0 or story_index >= len(stories):
        await update.effective_message.reply_text(
            "📭 **No stories available right now!**\n\n"
            "🔥 **New stories every weekend!**\n"
            "📅 Fresh content drops every Friday, Saturday & Sunday\n"
            "💫 Enjoy your weekend with sensual stories!\n\n"
            "🌟 Check back this weekend for exciting new content...",
            parse_mode='Markdown'
        )
        return
    
    story_id, title, content, created_at = stories[story_index]
    formatted_date = created_at.strftime('%d %b %Y')
    
    # Header for first story only
    if story_index == 0:
        header = (
            "🔥 *SENSUAL STORIES \- FREE FOR EVERYONE* 🔥\n\n"
            "💫 *Enjoy your weekend with sensual stories\!*\n"
            "📅 New stories uploaded every Friday, Saturday & Sunday\n"
            "🌟 Fresh content to make your weekends more exciting\n\n"
            f"📖 *Story {story_index + 1} of {len(stories)}:*\n\n"
        )
    else:
        header = f"📖 *Story {story_index + 1} of {len(stories)}:*\n\n"
    
    # Full story content (escape markdown to prevent formatting errors)
    safe_title = escape_markdown(title, version=2)
    safe_content = escape_markdown(content, version=2)
    full_text = f"{header}📖 *{safe_title}*\n_{formatted_date}_\n\n{safe_content}"
    
    # Create navigation keyboard
    keyboard = _create_pagination_kb(story_index, len(stories), user_id, stories)
    
    await update.effective_message.reply_text(
        full_text,
        parse_mode='MarkdownV2',
        reply_markup=keyboard
    )


async def _show_story_by_index_admin(query, story_index: int, stories: list, user_id: int):
    """Show a specific story by index for admin view with pagination"""
    if not stories or story_index < 0 or story_index >= len(stories):
        await query.edit_message_text(
            "📭 **No Stories Available**\n\n"
            "No stories have been posted yet.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="sensual:admin:back")
            ]])
        )
        return
    
    story_id, title, content, created_at = stories[story_index]
    formatted_date = created_at.strftime('%d %b %Y')
    
    # Admin header with story counter
    header = f"📖 **Admin View - Story {story_index + 1} of {len(stories)}:**\n\n"
    
    # Full story content (no limits for admin)
    safe_title = escape_markdown(title, version=2)
    safe_content = escape_markdown(content, version=2)
    full_text = f"{header}📖 *{safe_title}*\n_{formatted_date}_\n\n{safe_content}"
    
    # Create admin navigation keyboard
    keyboard = _create_admin_pagination_kb(story_index, len(stories), user_id, stories)
    
    await query.edit_message_text(
        full_text,
        parse_mode='MarkdownV2',
        reply_markup=keyboard
    )


def _create_admin_pagination_kb(current_index: int, total_stories: int, viewer_id: int, stories: list) -> InlineKeyboardMarkup:
    """Create pagination keyboard for admin story navigation"""
    rows = []
    
    # Get current story info for delete button
    current_story_id = stories[current_index][0]
    
    # Delete Story button (admin only)
    if _can_delete_story(current_story_id, viewer_id):
        rows.append([InlineKeyboardButton("🗑 Delete Story", callback_data=f"sensual:del:{current_story_id}")])
    
    # Navigation buttons
    nav_buttons = []
    
    # Previous button (if not first story)
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ Previous", callback_data=f"sensual:admin:nav:{current_index-1}"))
    
    # Next button (if not last story)
    if current_index < total_stories - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡", callback_data=f"sensual:admin:nav:{current_index+1}"))
    
    # Add navigation row if we have navigation buttons
    if nav_buttons:
        rows.append(nav_buttons)
    
    # Back to admin panel
    rows.append([InlineKeyboardButton("⬅ Back to Admin Panel", callback_data="sensual:admin:back")])
    
    return InlineKeyboardMarkup(rows)


async def _show_story_by_index_public(query, story_index: int, stories: list, user_id: int):
    """Show a specific story by index for public feed access with pagination"""
    if not stories or story_index < 0 or story_index >= len(stories):
        await query.edit_message_text(
            "📭 **No stories available right now!**\n\n"
            "🔥 **New stories every weekend!**\n"
            "📅 Fresh content drops every Friday, Saturday & Sunday\n"
            "💫 Enjoy your weekend with sensual stories!\n\n"
            "🌟 Check back this weekend for exciting new content...",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Feed", callback_data="pf:menu")
            ]])
        )
        return
    
    story_id, title, content, created_at = stories[story_index]
    formatted_date = created_at.strftime('%d %b %Y')
    
    # Header for first story only (public feed version)
    if story_index == 0:
        header = (
            "🔥 *SENSUAL STORIES \- FREE FOR EVERYONE* 🔥\n\n"
            "💫 *Enjoy your weekend with sensual stories\!*\n"
            "📅 New stories uploaded every Friday, Saturday & Sunday\n"
            "🌟 Fresh content to make your weekends more exciting\n\n"
            f"📖 *Story {story_index + 1} of {len(stories)}:*\n\n"
        )
    else:
        header = f"📖 *Story {story_index + 1} of {len(stories)}:*\n\n"
    
    # Full story content (no limits - supports 100,000+ words)
    safe_title = escape_markdown(title, version=2)
    safe_content = escape_markdown(content, version=2)
    full_text = f"{header}📖 *{safe_title}*\n_{formatted_date}_\n\n{safe_content}"
    
    # Create public navigation keyboard
    keyboard = _create_public_pagination_kb(story_index, len(stories), user_id, stories)
    
    await query.edit_message_text(
        full_text,
        parse_mode='MarkdownV2',
        reply_markup=keyboard
    )


def _create_public_pagination_kb(current_index: int, total_stories: int, viewer_id: int, stories: list) -> InlineKeyboardMarkup:
    """Create pagination keyboard for public feed story navigation"""
    rows = []
    
    # Navigation buttons
    nav_buttons = []
    
    # Previous button (if not first story)
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ Previous", callback_data=f"sensual:public:nav:{current_index-1}"))
    
    # Next button (if not last story)
    if current_index < total_stories - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡", callback_data=f"sensual:public:nav:{current_index+1}"))
    
    # Add navigation row if we have navigation buttons
    if nav_buttons:
        rows.append(nav_buttons)
    
    # Back to feed button
    rows.append([InlineKeyboardButton("⬅ Back to Feed", callback_data="pf:menu")])
    
    return InlineKeyboardMarkup(rows)

# ---- Admin Commands ----
async def cmd_post_sensual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to post new sensual story"""
    user_id = update.effective_user.id
    admin_ids = get_admin_ids()

    if user_id not in admin_ids:
        return await update.message.reply_text("❌ You are not authorized to post sensual stories.")

    if len(context.args) < 2:
        return await update.message.reply_text(
            "📝 Usage: `/post_sensual <title> <content>`\n\n"
            "Example: `/post_sensual \"Midnight Encounter\" Once upon a time in Paris...`\n\n"
            "📚 **No word limit!** Stories can be as long as you want (100,000+ words supported)",
            parse_mode='Markdown'
        )

    title = context.args[0].strip('"\'')  # Remove quotes if present
    content = " ".join(context.args[1:])

    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                "INSERT INTO sensual_stories (title, content) VALUES (%s, %s) RETURNING id",
                (title, content)
            )
            story_id = cur.fetchone()[0]
            con.commit()

        await update.message.reply_text(
            f"✅ Sensual story posted successfully!\n\n"
            f"📖 **{title}**\n"
            f"🆔 Story ID: {story_id}\n"
            f"📅 Published: {datetime.now().strftime('%d %b %Y')}\n\n"
            f"Users can now read it via the Sensual Stories section!",
            parse_mode='Markdown'
        )
        
        log.info(f"Admin {user_id} posted sensual story: {title}")
        
    except Exception as e:
        log.error(f"Error posting sensual story: {e}")
        await update.message.reply_text(
            "❌ Failed to post story. Please try again or contact support."
        )

# ---- User Commands ----
async def cmd_sensual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sensual stories feed"""
    user_id = update.effective_user.id
    admin_ids = get_admin_ids()
    is_admin = user_id in admin_ids
    is_premium = reg.is_premium_user(user_id)

    # Show admin panel for admins
    if is_admin:
        admin_menu = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Post New Story", callback_data="sensual:admin:new")],
            [InlineKeyboardButton("📋 Manage Stories", callback_data="sensual:admin:manage")],
            [InlineKeyboardButton("📖 View Stories", callback_data="sensual:admin:view")]
        ])
        await update.message.reply_text(
            "🔧 **Admin Panel - Sensual Stories**\n\n"
            "Choose an action:",
            parse_mode='Markdown',
            reply_markup=admin_menu
        )
        return

    try:
        with reg._conn() as con, con.cursor() as cur:
            # COMPLETELY FREE ACCESS - No restrictions, no limits!
            cur.execute("""
                SELECT id, title, content, created_at 
                FROM sensual_stories 
                ORDER BY created_at DESC
            """)
            
            stories = cur.fetchall()

        if not stories:
            return await update.message.reply_text(
                "📭 **No stories available right now!**\n\n"
                "🔥 **New stories every weekend!**\n"
                "📅 Fresh content drops every Friday, Saturday & Sunday\n"
                "💫 Enjoy your weekend with sensual stories!\n\n"
                "🌟 Check back this weekend for exciting new content...",
                parse_mode='Markdown'
            )

        # Show first story with pagination
        await _show_story_by_index(update, context, 0, stories, user_id)

        log.info(f"User {user_id} viewed sensual stories (premium: {is_premium})")
        
    except Exception as e:
        log.error(f"Error showing sensual stories: {e}")
        await update.message.reply_text(
            "❌ Unable to load stories right now. Please try again later."
        )

# ---- Callback Handlers ----
async def cb_sensual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all sensual stories callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    try:
        if data == "sensual:upgrade":
            # Redirect to premium purchase
            from premium import premium_text, premium_kb
            await query.edit_message_text(
                premium_text(),
                parse_mode='Markdown',
                reply_markup=premium_kb()
            )
            
        elif data.startswith("sensual:admin:"):
            # Handle admin actions - verify admin access
            admin_ids = get_admin_ids()
            if user_id not in admin_ids:
                await query.answer("❌ Admin access required", show_alert=True)
                return
                
            action = data.split(":")[-1]
            if action == "new":
                await query.edit_message_text(
                    "📝 **Post New Sensual Story**\n\n"
                    "Use this command:\n"
                    "`/post_sensual \"Title\" Story content goes here...`\n\n"
                    "Example:\n"
                    "`/post_sensual \"Midnight in Paris\" Once upon a time in the city of love...`",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="sensual:admin:back")
                    ]])
                )
            elif action == "manage":
                # Show list of recent stories for management
                with reg._conn() as con, con.cursor() as cur:
                    cur.execute("""
                        SELECT id, title, created_at, 
                        (SELECT COUNT(*) FROM sensual_reactions WHERE story_id = sensual_stories.id) as reactions
                        FROM sensual_stories 
                        ORDER BY created_at DESC 
                        LIMIT 10
                    """)
                    stories = cur.fetchall()
                
                if not stories:
                    text = "📋 **Story Management**\n\nNo stories available to manage."
                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="sensual:admin:back")
                    ]])
                else:
                    text = "📋 **Story Management**\n\nRecent stories:\n\n"
                    buttons = []
                    for story_id, title, created_at, reactions in stories:
                        date_str = created_at.strftime('%d %b')
                        text += f"• **{title}** ({date_str}) - {reactions} reactions\n"
                        buttons.append([
                            InlineKeyboardButton(f"🗑️ Delete: {title[:20]}...", callback_data=f"sensual:del:{story_id}")
                        ])
                    
                    buttons.append([InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="sensual:admin:back")])
                    keyboard = InlineKeyboardMarkup(buttons)
                
                await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
                
            elif action == "view":
                # Show stories like a regular user would see them - WITH PAGINATION
                with reg._conn() as con, con.cursor() as cur:
                    cur.execute("""
                        SELECT id, title, content, created_at 
                        FROM sensual_stories 
                        ORDER BY created_at DESC 
                    """)
                    stories = cur.fetchall()

                if not stories:
                    await query.edit_message_text(
                        "📭 **No Stories Available**\n\n"
                        "No stories have been posted yet.",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="sensual:admin:back")
                        ]])
                    )
                    return

                # Show first story with pagination (admin view)
                await _show_story_by_index_admin(query, 0, stories, user_id)
                    
            elif action == "back":
                # Show admin panel again
                admin_menu = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Post New Story", callback_data="sensual:admin:new")],
                    [InlineKeyboardButton("📋 Manage Stories", callback_data="sensual:admin:manage")],
                    [InlineKeyboardButton("📖 View Stories", callback_data="sensual:admin:view")]
                ])
                await query.edit_message_text(
                    "🔧 **Admin Panel - Sensual Stories**\n\n"
                    "Choose an action:",
                    parse_mode='Markdown',
                    reply_markup=admin_menu
                )
                
        elif data.startswith("sensual:nav:"):
            # Handle regular user story navigation
            story_index = int(data.split(":")[-1])
            
            # Get stories again for navigation (no limit for long stories)
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT id, title, content, created_at 
                    FROM sensual_stories 
                    ORDER BY created_at DESC
                """)
                stories = cur.fetchall()
            
            if stories and 0 <= story_index < len(stories):
                # Show requested story
                story_id, title, content, created_at = stories[story_index]
                formatted_date = created_at.strftime('%d %b %Y')
                
                header = f"📖 *Story {story_index + 1} of {len(stories)}:*\n\n"
                safe_title = escape_markdown(title, version=2)
                safe_content = escape_markdown(content, version=2)
                full_text = f"{header}📖 *{safe_title}*\n_{formatted_date}_\n\n{safe_content}"
                
                # Create navigation keyboard
                keyboard = _create_pagination_kb(story_index, len(stories), user_id, stories)
                
                await query.edit_message_text(
                    full_text,
                    parse_mode='MarkdownV2',
                    reply_markup=keyboard
                )
            else:
                await query.answer("⚠️ Story not found", show_alert=True)
                
        elif data.startswith("sensual:admin:nav:"):
            # Handle admin story navigation
            admin_ids = get_admin_ids()
            if user_id not in admin_ids:
                await query.answer("❌ Admin access required", show_alert=True)
                return
                
            story_index = int(data.split(":")[-1])
            
            # Get stories again for admin navigation (no limits)
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT id, title, content, created_at 
                    FROM sensual_stories 
                    ORDER BY created_at DESC
                """)
                stories = cur.fetchall()
            
            if stories and 0 <= story_index < len(stories):
                await _show_story_by_index_admin(query, story_index, stories, user_id)
            else:
                await query.answer("⚠️ Story not found", show_alert=True)
                
        elif data.startswith("sensual:public:nav:"):
            # Handle public feed story navigation
            story_index = int(data.split(":")[-1])
            
            # Get stories again for public navigation (no limits)
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT id, title, content, created_at 
                    FROM sensual_stories 
                    ORDER BY created_at DESC
                """)
                stories = cur.fetchall()
            
            if stories and 0 <= story_index < len(stories):
                await _show_story_by_index_public(query, story_index, stories, user_id)
            else:
                await query.answer("⚠️ Story not found", show_alert=True)
                
        elif data.startswith("sensual:del:"):
            # Handle story deletion confirmation
            if not data.startswith("sensual:del:yes:"):
                # Show confirmation dialog
                story_id = int(data.split(":")[-1])
                
                if not _can_delete_story(story_id, user_id):
                    await query.answer("❌ You're not allowed to delete this story.", show_alert=True)
                    return
                
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Yes, delete", callback_data=f"sensual:del:yes:{story_id}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="sensual:admin:back")],
                ])
                await query.message.reply_text(f"⚠️ Delete story #{story_id}?", reply_markup=kb)
                
            else:
                # Execute deletion
                story_id = int(data.split(":")[-1])
                
                with reg._conn() as con, con.cursor() as cur:
                    # Get story title for confirmation
                    cur.execute("SELECT title FROM sensual_stories WHERE id = %s", (story_id,))
                    story = cur.fetchone()
                    
                    if story:
                        # Delete the story and its reactions
                        cur.execute("DELETE FROM sensual_reactions WHERE story_id = %s", (story_id,))
                        cur.execute("DELETE FROM sensual_stories WHERE id = %s", (story_id,))
                        con.commit()
                        
                        await query.edit_message_text(f"🗑 Story '{story[0]}' deleted successfully!")
                        log.info(f"Admin {user_id} deleted sensual story: {story[0]}")
                    else:
                        await query.edit_message_text("⚠️ Story not found or already deleted.")
            
    except Exception as e:
        log.error(f"Error handling sensual callback: {e}")
        await query.answer("❌ Something went wrong. Please try again.", show_alert=True)

# ---- Registration Function ----
async def story_submit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start story submission flow"""
    from handlers.text_framework import claim_or_reject
    
    if not await claim_or_reject(update, context, "stories", "submit", ttl_minutes=5):
        return
    await update.message.reply_text("📝 Send your sensual story (≤1000 chars):")

@requires_state("stories", "submit")
async def story_submit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle story submission text"""
    body = (update.message.text or "").strip()
    if not body:
        return await update.message.reply_text("❌ Empty story. Try again.")
    
    # No length limit - support very long stories (100,000+ words)
    
    # TODO: save story to database
    clear_state(context)
    await update.message.reply_text("✅ Story submitted.")

def register(app):
    """Register all sensual stories handlers"""
    # Ensure database tables exist
    ensure_sensual_table()
    
    # Register command handlers
    app.add_handler(CommandHandler("post_sensual", cmd_post_sensual), group=-4)
    app.add_handler(CommandHandler("sensual", cmd_sensual), group=-4)
    app.add_handler(CommandHandler("story_submit", story_submit_start), group=-4)
    
    # Register text handler for story submission
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, story_submit_text), group=-4)
    
    # Register callback handlers
    app.add_handler(CallbackQueryHandler(cb_sensual, pattern="^sensual:"), group=-4)
    
    log.info("✅ Sensual stories handlers registered successfully")