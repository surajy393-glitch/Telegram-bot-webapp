# handlers/blur_vault.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest
import registration as reg
import re
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
# optional: bilingual teaser text central file
try:
    from utils.feature_texts import VAULT_TEXT
except ImportError:
    VAULT_TEXT = "😏 **Blur-Reveal Vault**\n\nYour premium content awaits..."

log = logging.getLogger("blur_vault")

# ============ HELPER FUNCTIONS ============

async def _safe_edit_or_send(query, context, text, reply_markup=None, parse_mode="Markdown"):
    """
    Try to edit current message. If it's photo/video (editMessageText will fail),
    send a new text message instead. Optionally delete the old message for clean UI.
    """
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest:
        # Most likely this message is a media (photo/video) -> cannot edit text
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        # Optional: clean up the old media card
        try:
            await query.delete_message()
        except Exception:
            pass

async def _delete_quiet(query):
    """Quietly delete a message without errors"""
    try: 
        await query.delete_message()
    except Exception:
        pass

async def _send_vault_home(context, chat_id: int, user_id: int):
    """
    Send the Vault 'Browse Categories' screen as a NEW message.
    This avoids trying to edit a media message and avoids sending '/vault' text.
    """
    categories = get_vault_categories(user_id)

    text = (
        "😏 **Blur-Reveal Vault** 🌫️\n\n"
        f"💎 **Premium Access** - Unlimited viewing!\n\n"
        "** श्रेणियाँ ब्राउज़ करें:**\n"
    )

    # Create category buttons
    keyboard_rows = []
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                cat = categories[i + j]
                # Show remaining count only if > 0, otherwise show category name without count
                if cat['content_count'] > 0:
                    button_text = f"{cat['emoji']} {cat['name']} ({cat['content_count']})"
                else:
                    button_text = f"{cat['emoji']} {cat['name']}"
                row.append(InlineKeyboardButton(button_text, callback_data=f"vault:cat:{cat['id']}:1"))
        keyboard_rows.append(row)

    # Add action buttons
    keyboard_rows.extend([
        [
            InlineKeyboardButton("📝 Submit Content", callback_data="vault:submit"),
            InlineKeyboardButton("🔍 Search", callback_data="vault:search")
        ],
        [
            InlineKeyboardButton("📊 My Stats", callback_data="vault:stats"),
            InlineKeyboardButton("🎲 Random", callback_data="vault:random")
        ]
    ])

    kb = InlineKeyboardMarkup(keyboard_rows)
    await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="Markdown")

def _back_kb(cat_id: int):
    """Create back navigation buttons"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data=f"vault:cat:{cat_id}:1")],
        [InlineKeyboardButton("📂 Back to Categories", callback_data="vault:main")]
    ])

# ============ DATABASE SCHEMA ============

def ensure_vault_tables():
    """Create vault content system tables"""
    with reg._conn() as con, con.cursor() as cur:
        # Vault categories for organizing content
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vault_categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                emoji TEXT DEFAULT '📝',
                blur_intensity INTEGER DEFAULT 70,
                premium_only BOOLEAN DEFAULT TRUE,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # Main vault content table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vault_content (
                id BIGSERIAL PRIMARY KEY,
                submitter_id BIGINT NOT NULL,
                category_id INTEGER REFERENCES vault_categories(id),
                content_text TEXT,
                blurred_text TEXT,
                blur_level INTEGER DEFAULT 70,
                reveal_cost INTEGER DEFAULT 2,
                status TEXT DEFAULT 'pending',
                approval_status TEXT DEFAULT 'pending',
                approved_by BIGINT,
                approved_at TIMESTAMPTZ,
                view_count INTEGER DEFAULT 0,
                reveal_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # Add new media columns to existing table
        cur.execute("ALTER TABLE vault_content ADD COLUMN IF NOT EXISTS media_type TEXT DEFAULT 'text'")
        cur.execute("ALTER TABLE vault_content ADD COLUMN IF NOT EXISTS file_url TEXT")
        cur.execute("ALTER TABLE vault_content ADD COLUMN IF NOT EXISTS thumbnail_url TEXT")
        cur.execute("ALTER TABLE vault_content ADD COLUMN IF NOT EXISTS blurred_thumbnail_url TEXT")

        # Remove NOT NULL constraint from content_text and blurred_text (for media content)
        try:
            cur.execute("ALTER TABLE vault_content ALTER COLUMN content_text DROP NOT NULL")
            cur.execute("ALTER TABLE vault_content ALTER COLUMN blurred_text DROP NOT NULL") 
        except:
            pass

        # Add constraints (drop if exists first to avoid conflicts)
        try:
            cur.execute("ALTER TABLE vault_content DROP CONSTRAINT IF EXISTS chk_vault_status")
            cur.execute("ALTER TABLE vault_content DROP CONSTRAINT IF EXISTS chk_approval_status") 
            cur.execute("ALTER TABLE vault_content DROP CONSTRAINT IF EXISTS chk_media_type")
            cur.execute("ALTER TABLE vault_content DROP CONSTRAINT IF EXISTS chk_content_requirement")
        except:
            pass

        try:
            cur.execute("ALTER TABLE vault_content ADD CONSTRAINT chk_vault_status CHECK (status IN ('pending', 'approved', 'rejected', 'archived'))")
            cur.execute("ALTER TABLE vault_content ADD CONSTRAINT chk_approval_status CHECK (approval_status IN ('pending', 'approved', 'rejected'))")
            cur.execute("ALTER TABLE vault_content ADD CONSTRAINT chk_media_type CHECK (media_type IN ('text', 'image', 'video'))")
        except:
            pass

        # User interactions with vault content
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vault_interactions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                content_id BIGINT REFERENCES vault_content(id) ON DELETE CASCADE,
                action TEXT NOT NULL,
                tokens_spent INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),

                UNIQUE(user_id, content_id, action),
                CONSTRAINT chk_vault_action CHECK (action IN ('viewed', 'revealed', 'liked', 'reported'))
            );
        """)

        # Daily limits tracking for reveal control
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vault_daily_limits (
                user_id BIGINT PRIMARY KEY,
                reveals_used INTEGER DEFAULT 0,
                media_reveals_used INTEGER DEFAULT 0,
                limit_date DATE DEFAULT CURRENT_DATE,
                premium_status BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # Daily category view limits (10 per category for premium users)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vault_daily_category_views (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                category_id INTEGER REFERENCES vault_categories(id),
                views_today INTEGER DEFAULT 0,
                view_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),

                UNIQUE(user_id, category_id, view_date)
            );
        """)

        # Vault coin system for submissions
        cur.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS vault_coins INTEGER DEFAULT 0;
        """)

        # Token system for reveals
        cur.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS vault_tokens INTEGER DEFAULT 10;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS vault_tokens_last_reset DATE DEFAULT CURRENT_DATE;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS vault_storage_used BIGINT DEFAULT 0;
        """)

        # Insert default categories
        cur.execute("""
            INSERT INTO vault_categories (name, description, emoji, blur_intensity) VALUES 
            ('Romantic Confessions', 'Love stories and romantic secrets', '💖', 75),
            ('Dark Secrets', 'Deep confessions and hidden truths', '🖤', 85),
            ('Midnight Thoughts', 'Late night revelations', '🌙', 60),
            ('Forbidden Dreams', 'Fantasies and desires', '🔥', 90),
            ('Funny Confessions', 'Embarrassing and funny moments', '😂', 50),
            ('Life Lessons', 'Wisdom and experiences', '💡', 40),
            ('Blur Pictures', 'Hidden photos and private moments', '📸', 95),
            ('Blur Videos', 'Secret videos and clips', '🎥', 95)
            ON CONFLICT (name) DO NOTHING;
        """)

        # DISABLED: Sample content creation to prevent auto-entries
        # add_comprehensive_seed_data()

        # DISABLED: No longer create fake placeholder media content
        # Real photos/videos will be submitted by users and have actual file_id values
        # This prevents the bug where users spend tokens on fake placeholder content

        # NOTE: Only user-submitted content with real file_id should exist in vault

        # Create user states table for tracking submission state
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vault_user_states (
                user_id BIGINT PRIMARY KEY,
                category_id INTEGER REFERENCES vault_categories(id),
                state TEXT NOT NULL,
                data TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        con.commit()
        log.info("✅ Vault tables created successfully")

        # DISABLED: Seed data auto-creation to prevent duplicates
        # add_comprehensive_seed_data()

def add_comprehensive_seed_data():
    """Add 50 authentic entries for each content category"""

    # Dark Secrets - genuinely dark, longer, not childish
    dark_secrets = [
        "मैंने अपने best friend की girlfriend को देखकर 3 साल से fantasize किया है। वो नहीं जानता कि मैं हर रात उसके Instagram photos देखकर सोता हूँ। जब भी वो मेरे सामने उसकी तारीफ करता है, मैं मुस्कुराता हूँ लेकिन अंदर से जलता रहता हूँ। सबसे डरावनी बात ये है कि मैंने उनकी शादी में भी यही सोचा था।",
        "मैं अपनी sister-in-law के undergarments चुराता हूँ जब वो घर पर नहीं होती। 2 साल हो गए हैं और उसे पता नहीं चला। मैंने उनसे कई बार intimacy की है अकेले में। सबसे भयानक बात ये है कि मैं family functions में भी उसे देखकर वही सब सोचता रहता हूँ।",
        "मैंने अपने पिता की death की खुशी मनाई थी। वो हमेशा मुझे beat करते थे और मैंने secretly wish किया था कि वो मर जाएं। जब वो heart attack से मरे, मैंने सबके सामने रोया लेकिन अंदर से खुश था। Funeral में भी मैं पूरी तरह fake emotional था।",
        "मैं office की cleaning lady को देखकर sexually attract होता हूँ। वो 45+ की है और मैं 25 का हूँ। मैंने उसे changing room में देखा था और उस दिन से मैं उसके बारे में ही सोचता हूँ। मैंने कई बार उसके साथ conversation बढ़ाने की कोशिश की है।",
        "मैंने अपनी ex के नudes को internet पर upload कर दिया था जब उसने मुझे छोड़ा था। अब वो happily married है लेकिन वो photos अभी भी online हैं। मैं जानता हूँ ये गलत है लेकिन मुझे revenge मिला था और मैं खुश था।"
    ]

    # Forbidden Dreams - impactful and shocking  
    forbidden_dreams = [
        "मैं सपना देखता हूँ कि मैं अपनी teacher के साथ classroom में अकेला हूँ। वो मुझे private lessons देती है और फिर हम दोनों के बीच कुछ होता है। यो मेरा school time का fantasy है जो अब तक continue है। मैंने कई बार उनकी photos भी देखी हैं online।",
        "मेरा सबसे deep fantasy है कि मैं किसी stranger woman को metro में seduce करूं। मैं imagine करता हूँ कि हम दोनों last coach में अकेले हैं और वो मेरी flirting को respond करती है। फिर हम कहीं hotel जाते हैं और पूरी रात together रहते हैं।",
        "मैं सपना देखता हूँ कि मैं time travel करके अपनी college crush के साथ one night spend करूं। वो अब married है लेकिन मैं अभी भी उसे same way देखता हूँ। मैं imagine करता हूँ कि वो भी मुझे miss करती है और हम दोनों एक रात के लिए सब कुछ भूल जाते हैं।",
        "मेरी सबसे dark fantasy है किसी public place में intimacy करना। मैं सोचता हूँ कि कोई हमें देख रहा है लेकिन हम continue करते हैं। यो thrill मुझे बहुत excite करता है। मैंने अपनी girlfriend को भी suggest किया था लेकिन वो shock हो गई थी।",
        "मैं सपना देखता हूँ कि मैं famous actress का personal trainer बनूं और वो मुझसे privately exercise करे। फिर हम दोनों के बीच physical attraction develop होता है और हम secretly relationship शुरू करते हैं। ये मेरा favorite fantasy है जो मैं almost daily सोचता हूँ।"
    ]

    # Funny Confessions - longer, genuinely funny, feel real not AI-generated
    funny_confessions = [
        "मैं अपने बॉस को impress करने के लिए जानबूझकर toilets में उनसे मिलता हूँ। मैं उनका schedule track करता हूँ और जब वो bathroom जाते हैं तो मैं भी जाता हूँ। फिर washbasin पर casually बात करता हूँ work के बारे में। ये strategy actually काम कर रही है और मुझे recent promotion भी मिला है। Office colleagues को लगता है मैं hardworking हूँ लेकिन truth ये है कि मैं bathroom networking expert हूँ।",
        "मैंने अपनी dating profile में 5'8\" height लिखी है जबकि मैं 5'4\" का हूँ। जब भी कोई लड़की मिलने आती है तो मैं secretly thick sole के shoes पहनता हूँ। एक बार date के दौरान beach पर गए और जब shoes निकालने पड़े तो मैंने fake लंगड़ाना शुरू कर दिया कि पैर में चोट है। वो लड़की पूरे time concerned रही मेरे पैर के लिए और मुझे guilt feel हो रही थी।",
        "मैं gym में sirf attractive लड़कियों के सामने workout करता हूँ। मैं सबसे पहले check करता हूँ कि कौन सी लड़कियां हैं और फिर उनके नजदीक के equipment use करता हूँ। एक दिन मैं heavy weights उठाने की कोशिश कर रहा था एक hot girl को impress करने के लिए, लेकिन weight control नहीं हुआ और मेरे पैर पर गिर गया। वो लड़की help करने आई और मुझे hospital भी ले गई। Ironically, यो accident हमारी friendship की शुरुआत बनी।",
        "मैं video calls में sirf waist up decent कपड़े पहनता हूँ। नीचे हमेशा shorts या कभी कभी sirf underwear होता है। एक दिन important client meeting में मुझे अचानक खड़ा होना पड़ा कुछ documents लेने के लिए। पूरी team ने मेरे Mickey Mouse boxers देखे। सबसे funny बात ये है कि client को लगा ये मेरी fun personality है और उन्होंने immediately deal sign कर दी।",
        "मैं अपने roommate को impress करने के लिए fake cooking videos देखता हूँ। मैं YouTube पर chef बनने का नाटक करता हूँ जब वो घर में होता है। Actually मैं sirf maggi और basic pasta बना सकता हूँ लेकिन मैं complex dishes के bare में बात करता हूँ। एक दिन उसने मुझसे dinner बनाने को कहा guests के लिए। मैंने panic में food delivery order की और secretly containers में transfer किया। Sab log मेरी cooking की तारीफ कर रहे थे और मैं smile कर रहा था।"
    ]

    # Life Lessons - longer with stories, compelling to follow
    life_lessons = [
        "मैंने 25 साल तक people को please करने में अपनी पूरी energy waste की। हर किसी को खुश रखने के चक्कर में मैं अपनी happiness भूल गया। जब मेरी girlfriend ने मुझे छोड़ा क्योंकि मैं 'boring' था, तब realize हुआ कि authentic बनना ज्यादा important है। अब मैं clearly 'no' कहता हूँ जब कुछ नहीं करना चाहता। Result? कम friends हैं लेकिन जो हैं वो genuine हैं। Lesson: अपने लिए खड़े होना सीखो, वरना सब आपको doormat की तरह treat करेंगे।",
        "College में मैं हमेशा shortcuts ढूंढता था। Assignments copy करता, exams में cheating करता, presentations में internet से copy-paste करता था। First job मिलने पर realize हुआ कि actual skill नहीं है कोई। 6 महीने में fire हो गया क्योंकि कुछ deliver नहीं कर पा रहा था। फिर मैंने ground up से everything सीखा, proper way से। अब successful हूँ लेकिन struggle बहुत करना पड़ा। Lesson: कोई shortcut नहीं है success का, जो आज बचाओगे time वो कल double wastage बनेगा।",
        "मैं 5 साल तक toxic job में stuck रहा क्योंकि 'stable income' के डर से निकल नहीं रहा था। हर रोज mentally torture होता था, boss abusive था, work meaningless लगता था। Health problems शुरू हुईं - anxiety, depression, insomnia। जब doctor ने warning दी तब हिम्मत करके resign किया। Initially financial struggle हुआ लेकिन freelancing में बहुत बेहतर life मिली। Lesson: कभी भी security के नाम पर अपनी mental health को compromise मत करो।",
        "मैंने पूरे teens और early twenties में अपने parents को बहुत hurt किया। मैं समझता था कि वो मुझे restrict करते हैं सिर्फ। Rebellious phase में गलत friends बनाए, पढ़ाई ignore की, family functions avoid करता था। जब papa ko heart attack आया और hospital में admit हुए, तब realize हुआ कि वो कितना care करते थे। अब मैं weekly call करता हूँ, festivals पर जाता हूँ। Lesson: Parents को granted मत लो, वो हमेशा नहीं रहेंगे।",
        "Comparison trap में पड़ा था। Social media पर सबके life perfect लगते थे - better jobs, relationships, lifestyle। मैं constantly देखता रहता था कि दूसरे क्या कर रहे हैं और अपने आप को fail feel करता था। यो habit depression तक ले गई। Therapy लेने के बाद समझा कि हर कोई sirf अपने highlights share करता है। अब मैं अपनी journey पर focus करता हूँ। Lesson: अपने chapter 1 को किसी और के chapter 20 से compare मत करो।"
    ]

    # Midnight Thoughts - thoughts everyone has but doesn't speak, longer
    midnight_thoughts = [
        "क्या मैं अपनी zindagi waste कर रहा हूँ same routine में? हर दिन वही office, वही काम, वही लोग। कभी कभी लगता है कि मैं robot की तरह जी रहा हूँ। सब कुछ mechanical हो गया है - उठना, नहाना, office जाना, खाना, सोना। Weekend भी यही सोचकर बीतता है कि Monday फिर आ जाएगा। क्या यही life है? क्या यही सब कुछ है? कभी कभी सोचता हूँ कि everything छोड़कर कहीं चला जाऊं लेकिन फिर practical problems सोचकर डर जाता हूँ।",
        "अगर मैं कल मर जाऊं तो कोई actually miss करेगा? मतलब genuinely miss करेगा, या बस formality में sad feel करेगा कुछ दिन? Friends हैं लेकिन हम सिर्फ plans बनाने के लिए बात करते हैं। Family है लेकिन हम rarely deep conversations करते हैं। Office colleagues हैं लेकिन वो professional relationship है। Actually कोई नहीं जानता कि मैं वास्तव में कैसा हूँ। यो लगता है कि मैं बहुत सारे लोगों के साथ हूँ लेकिन actually मैं completely alone हूँ।",
        "मैं कितना fake हूँ daily life में? Office में professional, friends के साथ funny, family के सामने responsible - लेकिन actually मैं कौन हूँ? Sometimes लगता है कि मैं सिर्फ different masks पहनता रहता हूँ। Real personality क्या है मेरी? कभी कभी mirror में देखकर लगता है कि यो person कौन है? क्या मैं भी उन लोगों की तरह हूँ जिन्हें मैं fake कहता हूँ? क्या authenticity भी एक mask है?",
        "क्या मेरे सारे achievements actually luck हैं? Job, education, relationships - क्या मैं deserve करता हूँ या सिर्फ coincidence है? Imposter syndrome हमेशा पीछे छुपा रहता है। जब कोई मेरी तारीफ करता है तो लगता है कि अगर उन्हें pता चल जाए कि मैं actually कितना confused और insecure हूँ तो वो shock हो जाएंगे। क्या हर कोई ऐसा feel करता है या सिर्फ मैं ही इतना unsure हूँ अपने बारे में?",
        "Time कितनी fast बीत रहा है और मैं कुछ meaningful नहीं कर रहा। Childhood memories अभी भी fresh हैं लेकिन 10 साल बीत गए। अगले 10 साल भी यूंही बीत जाएंगे क्या? क्या मैं 40 की age में भी यही regrets feel करूंगा? मैं constantly plan करता रहता हूँ - जब यो होगा तो खुश रहूंगा, जब वो achieve करूंगा तो satisfied feel करूंगा। लेकिन यो 'जब' कभी नहीं आता। Present में खुश रहना क्यों इतना मुश्किल है?"
    ]

    # Romantic Confessions - romantic + sensual, longer, natural not AI-generated
    romantic_confessions = [
        "मेरी first love आज भी मेरे दिल में बसी है। College में उसके साथ जो feelings थे, वो कभी completely go नहीं हुईं। अब मैं committed relationship में हूँ और मेरी girlfriend बहुत sweet है, लेकिन physically intimate moments में भी कभी कभी उसी का face याद आ जाता है। वो way जिससे वो हंसती थी, जिस तरह वो मेरे कंधे पर head रखती थी, वो सब अभी भी feel कर सकता हूँ। यो guilt भी है क्योंकि मैं जानता हूँ यो fair नहीं है मेरी current girlfriend के साथ।",
        "मैं अपनी office colleague को secretly देखता रहता हूँ। वो married है और मैं भी, लेकिन जब वो meeting room में presentation देती है तो मैं उसकी lips को देखता रहता हूँ। एक दिन lift में अकेले थे और accidentally हमारी hands touch हो गईं। वो moment इतना intense था कि मैं पूरी रात सो नहीं सका। Imagine करता रहा कि क्या होता अगर हम दोनों single होते। यो wrong है लेकिन यो attraction control नहीं होता।",
        "मेरी best friend को propose करने से 3 साल पहले डर लग रहा था। हम childhood से together हैं और मैं जानता था कि अगर उसने 'no' कहा तो friendship भी खत्म हो जाएगी। जब finally मैंने कहा तो उसने admit किया कि वो भी same feel करती थी लेकिन यो डर लग रहा था कि कहीं हमारी bond disturb न हो जाए। अब हम together हैं और physical intimacy बहुत natural और beautiful है क्योंकि emotional connection पहले से था।",
        "मैं एक bar में stranger girl से मिला था। Conversation में पता चला कि वो city से बाहर से आई है सिर्फ one day के लिए। हम पूरी रात together घूमे - beaches, late night cafes, empty roads पर bike ride। जब morning हुई तो उसकी train थी। Station पर goodbye इतना emotional था कि दोनों रो पड़े। यो one night connection इतना deep था कि मैं महीनों तक उसे miss करता रहा। Sometimes perfect moments सिर्फ memories के लिए होते हैं।",
        "मेरी long distance girlfriend के साथ video calls during intimate moments बहुत special हैं। Physical distance होने के बावजूद emotional और mental connection इतना strong है कि कभी कभी लगता है जैसे वो exactly मेरे साथ हो। आवाज़ सुनना, उसकी eyes देखना screen पर, और वो way जिससे वो मेरा name लेती है - यो सब मिलकर physical presence से भी ज्यादा intimate feel होता है। हम एक साथ सोते हैं video call पर और morning उसका face देखना perfect way है दिन शुरू करने का।"
    ]

    # Combine all data for insertion
    categories_data = {
        'Dark Secrets': dark_secrets[:50],
        'Forbidden Dreams': forbidden_dreams[:50], 
        'Funny Confessions': funny_confessions[:50],
        'Life Lessons': life_lessons[:50],
        'Midnight Thoughts': midnight_thoughts[:50],
        'Romantic Confessions': romantic_confessions[:50]
    }

    with reg._conn() as con, con.cursor() as cur:
        for category_name, contents in categories_data.items():
            # Get category ID
            cur.execute("SELECT id FROM vault_categories WHERE name = %s", (category_name,))
            result = cur.fetchone()
            if not result:
                continue

            category_id = result[0]

            # Check how many entries already exist
            cur.execute("SELECT COUNT(*) FROM vault_content WHERE category_id = %s", (category_id,))
            existing_count = cur.fetchone()[0]

            if existing_count >= 50:
                continue  # Skip if already has enough content

            # Add content entries
            for i, content in enumerate(contents):
                # Check if similar content already exists
                cur.execute("""
                    SELECT id FROM vault_content 
                    WHERE category_id = %s AND content_text LIKE %s
                """, (category_id, f"%{content[:30]}%"))

                if cur.fetchone():
                    continue  # Skip if similar content exists

                # Create blurred version
                blurred = create_smart_blur(content, 75)

                # Insert new content
                cur.execute("""
                    INSERT INTO vault_content 
                    (submitter_id, category_id, content_text, blurred_text, media_type, blur_level, reveal_cost, approval_status, approved_at, approved_by)
                    VALUES (8482725798, %s, %s, %s, 'text', 75, 2, 'approved', NOW(), 647778438)
                """, (category_id, content, blurred))

        con.commit()
        print("✅ Comprehensive seed data added to vault categories")

# ============ BLUR SYSTEM ============

def create_smart_blur(text: str, blur_level: int = 70) -> str:
    """Smart blurring algorithm that preserves readability while hiding sensitive content"""
    # Words to always blur (sensitive content)
    sensitive_words = [
        'love', 'kiss', 'sex', 'naked', 'orgasm', 'desire', 'fantasy', 'secret',
        'affair', 'cheat', 'crush', 'masturbate', 'porn', 'virgin', 'hook',
        'date', 'boyfriend', 'girlfriend', 'husband', 'wife', 'marriage',
        'pregnant', 'drugs', 'alcohol', 'drunk', 'money', 'steal', 'lie'
    ]

    words = text.split()
    blurred_words = []

    for i, word in enumerate(words):
        # Clean word for checking
        clean_word = re.sub(r'[^\w]', '', word.lower())

        # Calculate blur probability
        should_blur = False

        if clean_word in sensitive_words:
            should_blur = True
        elif len(clean_word) > 6:
            # Longer words more likely to be blurred
            should_blur = (hash(word) % 100) < (blur_level + 20)
        elif len(clean_word) > 3:
            # Medium words
            should_blur = (hash(word) % 100) < blur_level
        else:
            # Short words (articles, etc.) rarely blurred
            should_blur = (hash(word) % 100) < (blur_level - 30)

        if should_blur and len(clean_word) > 2:
            # Create blur pattern
            if len(word) <= 3:
                blurred = '█' * len(word)
            elif len(word) <= 5:
                blurred = word[0] + '█' * (len(word) - 2) + word[-1]
            else:
                visible_chars = max(1, len(word) // 3)
                blurred = word[:visible_chars] + '█' * (len(word) - 2 * visible_chars) + word[-visible_chars:]

            # Preserve punctuation
            punct = ''.join(c for c in word if not c.isalnum())
            blurred_words.append(blurred + punct.replace(word.translate(str.maketrans('', '', ''.join(c for c in word if c.isalnum()))), ''))
        else:
            blurred_words.append(word)

    return ' '.join(blurred_words)

# ============ TOKEN SYSTEM ============

def get_daily_reveal_limits(user_id: int) -> dict:
    """Get user's daily reveal limits and current usage - PREMIUM ONLY"""
    is_premium = reg.has_active_premium(user_id)

    # Admin bypass: Admin ID 647778438 gets unlimited access
    if user_id == 647778438:
        is_premium = True

    # Only premium users can access vault
    if not is_premium:
        return {'access_denied': True, 'message': 'Premium membership required'}

    # Daily limits configuration - PREMIUM ONLY - UNLIMITED ACCESS
    limits = {
        'premium_text_reveals': 999999,   # Premium users: UNLIMITED text reveals
        'premium_media_reveals': 999999,  # Premium users: UNLIMITED media reveals  
        'max_storage_mb': 999999          # Premium storage limit: UNLIMITED
    }

    with reg._conn() as con, con.cursor() as cur:
        # Get or create daily limit record
        cur.execute("""
            INSERT INTO vault_daily_limits (user_id, premium_status, limit_date) 
            VALUES (%s, %s, CURRENT_DATE)
            ON CONFLICT (user_id) DO UPDATE SET
                premium_status = %s,
                limit_date = CASE 
                    WHEN vault_daily_limits.limit_date < CURRENT_DATE THEN CURRENT_DATE
                    ELSE vault_daily_limits.limit_date
                END,
                reveals_used = CASE 
                    WHEN vault_daily_limits.limit_date < CURRENT_DATE THEN 0
                    ELSE vault_daily_limits.reveals_used
                END,
                media_reveals_used = CASE 
                    WHEN vault_daily_limits.limit_date < CURRENT_DATE THEN 0
                    ELSE vault_daily_limits.media_reveals_used
                END,
                updated_at = NOW()
            RETURNING reveals_used, media_reveals_used
        """, (user_id, is_premium, is_premium))

        result = cur.fetchone()
        reveals_used, media_reveals_used = result if result else (0, 0)
        con.commit()

    max_text = limits['premium_text_reveals']
    max_media = limits['premium_media_reveals']

    return {
        'is_premium': True,
        'text_reveals_used': reveals_used,
        'text_reveals_max': max_text,
        'text_reveals_remaining': max(0, max_text - reveals_used),
        'media_reveals_used': media_reveals_used,
        'media_reveals_max': max_media,
        'media_reveals_remaining': max(0, max_media - media_reveals_used),
        'storage_limit_mb': limits['max_storage_mb']
    }

def can_user_reveal_content(user_id: int, content_type: str) -> tuple[bool, str]:
    """Check if user can reveal content based on daily limits - PREMIUM ONLY"""
    # Admin bypass: Admin ID 647778438 gets unlimited access
    if user_id == 647778438:
        return True, "OK"

    # First check premium access
    if not reg.has_active_premium(user_id):
        return False, "🔒 **Premium Membership Required**\n\nThe vault is exclusively for premium members only!"

    limits = get_daily_reveal_limits(user_id)

    # Check if premium access was denied
    if limits.get('access_denied'):
        return False, limits.get('message', 'Access denied')

    if content_type in ['image', 'video']:
        if limits['media_reveals_remaining'] <= 0:
            return False, f"🚫 **Daily Media Limit Reached**\n\nYou've used {limits['media_reveals_used']}/{limits['media_reveals_max']} media reveals today.\n\n⏰ **Resets at midnight** - preserving content scarcity!"
    else:
        if limits['text_reveals_remaining'] <= 0:
            return False, f"🚫 **Daily Text Limit Reached**\n\nYou've used {limits['text_reveals_used']}/{limits['text_reveals_max']} text reveals today.\n\n⏰ **Resets at midnight** - preserving content scarcity!"

    return True, "OK"

def increment_reveal_usage(user_id: int, content_type: str):
    """Increment user's daily reveal usage"""
    with reg._conn() as con, con.cursor() as cur:
        if content_type in ['image', 'video']:
            cur.execute("""
                UPDATE vault_daily_limits 
                SET media_reveals_used = media_reveals_used + 1, updated_at = NOW()
                WHERE user_id = %s
            """, (user_id,))
        else:
            cur.execute("""
                UPDATE vault_daily_limits 
                SET reveals_used = reveals_used + 1, updated_at = NOW()
                WHERE user_id = %s
            """, (user_id,))
        con.commit()

def get_user_vault_tokens_REMOVED(user_id: int) -> int:
    """Get user's current vault tokens with daily reset"""
    with reg._conn() as con, con.cursor() as cur:
        # Check if we need to reset tokens (daily reset)
        cur.execute("""
            UPDATE users 
            SET vault_tokens = 10, vault_tokens_last_reset = CURRENT_DATE
            WHERE tg_user_id = %s 
            AND (vault_tokens_last_reset < CURRENT_DATE OR vault_tokens_last_reset IS NULL)
        """, (user_id,))

        # Get current tokens
        cur.execute("SELECT COALESCE(vault_tokens, 10) FROM users WHERE tg_user_id = %s", (user_id,))
        result = cur.fetchone()
        return result[0] if result else 10

def spend_vault_tokens_REMOVED(user_id: int, amount: int) -> bool:
    """Spend vault tokens if user has enough"""
    with reg._conn() as con, con.cursor() as cur:
        # First ensure user has vault_tokens column initialized
        cur.execute("""
            UPDATE users 
            SET vault_tokens = COALESCE(vault_tokens, 10)
            WHERE tg_user_id = %s AND vault_tokens IS NULL
        """, (user_id,))

        # Then check if user has enough tokens and spend them
        cur.execute("""
            SELECT COALESCE(vault_tokens, 10) FROM users WHERE tg_user_id = %s
        """, (user_id,))

        current_tokens = cur.fetchone()
        if not current_tokens or current_tokens[0] < amount:
            return False

        # Deduct tokens
        cur.execute("""
            UPDATE users 
            SET vault_tokens = vault_tokens - %s
            WHERE tg_user_id = %s
            RETURNING vault_tokens
        """, (amount, user_id))

        result = cur.fetchone()
        con.commit()
        log.info(f"💰 User {user_id} spent {amount} tokens, remaining: {result[0] if result else 'unknown'}")
        return result is not None

LOCK_TEXT = (
    "🚨🔥 **VAULT LOCKED - MISSING THE GOOD STUFF!** 🔥🚨\n\n"
    "😈 **You're missing out on:**\n"
    "🔥 600+ steamy photos & hot videos\n"
    "💋 Sensual selfies from real users\n"
    "📱 Private video messages & confessions\n"
    "🌶️ Spicy content updated daily\n"
    "🔞 Adult-only exclusive uploads\n\n"

    "😭 **FREE = Permanent Frustration Zone**\n"
    "• Only blurred previews (torture!)\n"
    "• Can't see who's behind the content\n"
    "• Missing the hottest uploads\n"
    "• No access to video reveals\n\n"

    "💎 **PREMIUM = INSTANT SATISFACTION:**\n"
    "✅ Crystal clear reveals of EVERYTHING\n"
    "✅ Unlimited browsing of sensual content\n"
    "✅ Upload your own hot pics/videos\n"  
    "✅ Advanced filters (Wild/Naughty/Extreme)\n"
    "✅ Private messaging with uploaders\n"
    "✅ VIP access to exclusive content\n\n"

    "🔥 **WHAT PREMIUM USERS SAY:**\n"
    "💬 \"Finally! No more frustrating blurs!\"\n"
    "💬 \"The content is actually worth it\"\n"
    "💬 \"Can't believe what I was missing\"\n\n"

    "⚡ **UNLOCK NOW & START BROWSING IMMEDIATELY**\n"
    "🎯 **No waiting, no limits, no regrets!**"
)

def _upgrade_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium:open")],
    ])

# ============ DAILY LIMITS SYSTEM ============

def check_daily_category_limit(user_id: int, category_id: int) -> bool:
    """Check if user has reached daily limit for this category (10 views per category)"""

    # UNLIMITED ACCESS FOR ALL PREMIUM USERS
    return True  # All premium users get unlimited access to all categories

def increment_daily_category_view(user_id: int, category_id: int):
    """Increment daily view count for category"""
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO vault_daily_category_views (user_id, category_id, views_today, view_date)
            VALUES (%s, %s, 1, CURRENT_DATE)
            ON CONFLICT (user_id, category_id, view_date)
            DO UPDATE SET 
                views_today = vault_daily_category_views.views_today + 1,
                updated_at = NOW()
        """, (user_id, category_id))
        con.commit()

def get_daily_limit_message() -> str:
    """Message shown when user hits daily limit"""
    return """🚨 **You've reached today's limit!** 🚨

🎯 **You are done for today** - Come again tomorrow to watch more!

💰 **Want more content?** Submit your own and earn coins!
• 📤 Each submission = 1 coin earned
• 🎁 Help us grow with new content daily
• 🔄 More submissions = More variety for everyone

🔥 **Submit now and help the community grow:**
📸 Upload Photos: /vault → Submit Content
🎥 Upload Videos: /vault → Submit Content  
💭 Share Secrets: /vault → Submit Content

**Together we can create the hottest content library!** 🚀"""

def award_submission_coin(user_id: int) -> int:
    """Award 1 coin for content submission and return new total"""
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            UPDATE users 
            SET vault_coins = COALESCE(vault_coins, 0) + 1
            WHERE tg_user_id = %s
            RETURNING vault_coins
        """, (user_id,))

        result = cur.fetchone()
        con.commit()
        return result[0] if result else 1

def get_user_vault_coins(user_id: int) -> int:
    """Get user's current vault coin balance"""
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(vault_coins, 0) FROM users WHERE tg_user_id = %s
        """, (user_id,))

        result = cur.fetchone()
        return result[0] if result else 0

async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check vault coin balance"""
    user_id = update.effective_user.id
    coins = get_user_vault_coins(user_id)

    await update.message.reply_text(
        f"💰 **Your Vault Coin Balance** 💰\n\n"
        f"🪙 **Current Coins:** {coins}\n\n"
        f"💡 **How to earn more coins:**\n"
        f"• 📤 Submit content to vault (+1 coin)\n"
        f"• ✅ Get submissions approved (+1 bonus coin)\n"
        f"• 🔥 Help grow the community daily\n\n"
        f"🎯 **Use coins for:** Future premium features coming soon!",
        parse_mode="Markdown"
    )

# ============ CONTENT BROWSING ============

def get_vault_categories(user_id: int = None) -> List[Dict[str, Any]]:
    """Get active vault categories with remaining content counts for user"""
    with reg._conn() as con, con.cursor() as cur:
        if user_id is None:
            # Original behavior for admin/general use
            cur.execute("""
                SELECT 
                    vc.id, vc.name, vc.description, vc.emoji, vc.blur_intensity,
                    COUNT(vco.id) as content_count
                FROM vault_categories vc
                LEFT JOIN vault_content vco ON vc.id = vco.category_id 
                    AND vco.approval_status = 'approved'
                WHERE vc.active = TRUE
                GROUP BY vc.id, vc.name, vc.description, vc.emoji, vc.blur_intensity
                ORDER BY content_count DESC, vc.name
            """)
        else:
            # Calculate remaining content per user (total - viewed)
            cur.execute("""
                SELECT 
                    vc.id, vc.name, vc.description, vc.emoji, vc.blur_intensity,
                    (
                        SELECT COUNT(*) 
                        FROM vault_content vco 
                        WHERE vco.category_id = vc.id 
                        AND vco.approval_status = 'approved'
                        AND vco.id NOT IN (
                            SELECT vi.content_id 
                            FROM vault_interactions vi 
                            WHERE vi.user_id = %s 
                            AND vi.action IN ('viewed', 'revealed')
                            AND vi.content_id IS NOT NULL
                        )
                    ) as remaining_count
                FROM vault_categories vc
                WHERE vc.active = TRUE
                ORDER BY remaining_count DESC, vc.name
            """, (user_id,))

        return [
            {
                'id': row[0], 'name': row[1], 'description': row[2],
                'emoji': row[3], 'blur_intensity': row[4], 'content_count': row[5]
            }
            for row in cur.fetchall()
        ]

def get_vault_content_by_category(category_id: int, user_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """Get vault content for a category - filters out already revealed content for normal users"""
    with reg._conn() as con, con.cursor() as cur:
        # Admin ko sab dikhna chahiye (unseen filter hata ke)
        if user_id in [647778438, 1437934486]:  # Admin IDs
            cur.execute("""
                SELECT 
                    vc.id, vc.content_text, vc.blurred_text, vc.reveal_cost,
                    vc.view_count, vc.reveal_count, vc.created_at, vc.media_type,
                    vc.file_url, vc.thumbnail_url, vc.blurred_thumbnail_url,
                    CASE WHEN vi.action = 'revealed' THEN TRUE ELSE FALSE END as already_revealed
                FROM vault_content vc
                LEFT JOIN vault_interactions vi
                  ON vc.id = vi.content_id
                 AND vi.user_id = %s
                 AND vi.action = 'revealed'
                WHERE vc.category_id = %s
                  AND vc.approval_status = 'approved'
                ORDER BY vc.created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, category_id, limit, offset))
        else:
            # Normal users ke liye sirf unseen
            cur.execute("""
                SELECT 
                    vc.id, vc.content_text, vc.blurred_text, vc.reveal_cost,
                    vc.view_count, vc.reveal_count, vc.created_at, vc.media_type,
                    vc.file_url, vc.thumbnail_url, vc.blurred_thumbnail_url,
                    FALSE as already_revealed
                FROM vault_content vc
                WHERE vc.category_id = %s
                  AND vc.approval_status = 'approved'
                  AND vc.id NOT IN (
                      SELECT content_id
                      FROM vault_interactions
                      WHERE user_id = %s
                        AND action = 'revealed'
                  )
                ORDER BY vc.created_at DESC
                LIMIT %s OFFSET %s
            """, (category_id, user_id, limit, offset))

        rows = cur.fetchall()

    # Map results to dict
    content_list = []
    for row in rows:
        content_list.append({
            "id": row[0],
            "content_text": row[1],
            "blurred_text": row[2],
            "reveal_cost": row[3],
            "view_count": row[4],
            "reveal_count": row[5],
            "created_at": row[6],
            "media_type": row[7],
            "file_url": row[8],
            "thumbnail_url": row[9],
            "blurred_thumbnail_url": row[10],
            "user_revealed": row[11],  # Keep consistent naming with rest of code
        })
    return content_list

def get_vault_content_total_count(category_id: int, user_id: int) -> int:
    """Get total count of vault content for a category (for pagination)"""
    with reg._conn() as con, con.cursor() as cur:
        # Admin can see all content
        if user_id in [647778438, 1437934486]:  # Admin IDs
            cur.execute("""
                SELECT COUNT(*)
                FROM vault_content vc
                WHERE vc.category_id = %s
                  AND vc.approval_status = 'approved'
            """, (category_id,))
        else:
            # Normal users can only see unrevealed content
            cur.execute("""
                SELECT COUNT(*)
                FROM vault_content vc
                WHERE vc.category_id = %s
                  AND vc.approval_status = 'approved'
                  AND vc.id NOT IN (
                      SELECT content_id
                      FROM vault_interactions
                      WHERE user_id = %s
                        AND action = 'revealed'
                  )
            """, (category_id, user_id))
        
        result = cur.fetchone()
        return result[0] if result else 0

async def cmd_vault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main vault command - shows categories or content based on premium status"""
    uid = update.effective_user.id

    # Initialize vault tables on first run
    ensure_vault_tables()

    # Admin bypass - Allow admin access even without premium
    if uid != 647778438 and not reg.has_active_premium(uid):
        # Show lock screen to free users (except admin)
        await update.message.reply_text(LOCK_TEXT, reply_markup=_upgrade_kb(), parse_mode="Markdown")
        return

    # PREMIUM: Show vault browser
    await show_vault_main_menu(uid, update.message.reply_text)


# --- ONE-TIME MIGRATION: ensure file_id column exists ---
async def cmd_vault_migrate(update, context):
    admin_ids = [647778438]  # Add your admin IDs
    if update.effective_user.id not in admin_ids:
        return await update.message.reply_text("⛔ Admin only.")
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("ALTER TABLE vault_content ADD COLUMN IF NOT EXISTS file_id TEXT;")
            con.commit()
        await update.message.reply_text("✅ vault_content.file_id ensured.")
    except Exception as e:
        await update.message.reply_text(f"❌ Migration failed: {e}")


# /vault_backfill (admins only)
async def cmd_vault_backfill(update, context):
    admin_ids = [647778438]  # Add your admin IDs
    if update.effective_user.id not in admin_ids:
        return await update.message.reply_text("⛔ Admin only.")

    fixed = 0; failed = 0
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT id, media_type, file_url
            FROM vault_content
            WHERE file_id IS NULL AND file_url IS NOT NULL
            ORDER BY id DESC
            LIMIT 50
        """)
        rows = cur.fetchall()

    for content_id, media_type, file_url in rows:
        try:
            if media_type == "image":
                msg = await context.bot.send_photo(chat_id=update.effective_user.id, photo=file_url, disable_notification=True)
                fid = msg.photo[-1].file_id if msg.photo else None
            elif media_type == "video":
                msg = await context.bot.send_video(chat_id=update.effective_user.id, video=file_url, disable_notification=True)
                fid = msg.video.file_id if msg.video else None
            else:
                fid = None

            if fid:
                with reg._conn() as con, con.cursor() as cur:
                    cur.execute("UPDATE vault_content SET file_id=%s WHERE id=%s", (fid, content_id))
                    con.commit()
                fixed += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"Backfill done. Fixed={fixed}, Failed={failed}")

async def show_vault_main_menu(user_id: int, reply_func):
    """Show main vault browsing interface"""
    categories = get_vault_categories(user_id)

    text = (
        "😏 **Blur-Reveal Vault** 🌫️\n\n"
        f"💎 **Premium Access** - Unlimited viewing!\n\n"
        "** श्रेणियाँ ब्राउज़ करें:**\n"
    )

    # Create category buttons
    keyboard_rows = []
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                cat = categories[i + j]
                # Show remaining count only if > 0, otherwise show category name without count
                if cat['content_count'] > 0:
                    button_text = f"{cat['emoji']} {cat['name']} ({cat['content_count']})"
                else:
                    button_text = f"{cat['emoji']} {cat['name']}"
                row.append(InlineKeyboardButton(button_text, callback_data=f"vault:cat:{cat['id']}:1"))
        keyboard_rows.append(row)

    # Add action buttons
    keyboard_rows.extend([
        [
            InlineKeyboardButton("📝 Submit Content", callback_data="vault:submit"),
            InlineKeyboardButton("🔍 Search", callback_data="vault:search")
        ],
        [
            InlineKeyboardButton("📊 My Stats", callback_data="vault:stats"),
            InlineKeyboardButton("🎲 Random", callback_data="vault:random")
        ]
    ])

    kb = InlineKeyboardMarkup(keyboard_rows)
    await reply_func(text, reply_markup=kb, parse_mode="Markdown")

async def show_category_content(query, category_id: int, user_id: int):
    """Show content for a specific category"""
    # Check if user is premium (admin bypass)
    is_premium = reg.has_active_premium(user_id)
    is_admin = user_id == 647778438  # Admin bypass

    if not is_premium and not is_admin:
        # Show non-premium message (except for admin)
        await query.edit_message_text(
            LOCK_TEXT,
            reply_markup=_upgrade_kb(),
            parse_mode="Markdown"
        )
        return

    # REMOVED: Daily limits for premium users - they can see all content

    # Get category info
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT name, emoji, description FROM vault_categories WHERE id = %s", (category_id,))
        cat_info = cur.fetchone()

        if not cat_info:
            await query.answer("❌ Category not found")
            return

    cat_name, cat_emoji, cat_desc = cat_info
    # Premium users and admin get unlimited content
    limit = 1000  # Show all content for premium users and admin
    content_list = get_vault_content_by_category(category_id, user_id, limit)

    # YOUR EXACT PATCH C - Proper counts (no more "1 item" confusion)
    with reg._conn() as con, con.cursor() as cur:
        # total approved in this category (for everyone)
        cur.execute("""
            SELECT COUNT(*) FROM vault_content
             WHERE category_id=%s AND approval_status='approved'
        """, (category_id,))
        total_cat = cur.fetchone()[0] or 0

        # total items available to THIS user (everyone sees all now)
        cur.execute("""
            SELECT COUNT(*) FROM vault_content
             WHERE category_id=%s AND approval_status='approved'
        """, (category_id,))
        total_for_you = cur.fetchone()[0] or 0

    if not content_list:
        text = (
            f"{cat_emoji} **{cat_name}**\n\n"
            f"_{cat_desc}_\n\n"
            "🤷‍♀️ No content available yet.\n"
            "Be the first to submit something!"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Submit to this Category", callback_data=f"vault:submit:{category_id}")],
            [InlineKeyboardButton("🔙 Back to Categories", callback_data="vault:main")]
        ])
    else:
        text = (
            f"{cat_emoji} **{cat_name}**\n\n"
            f"_{cat_desc}_\n\n"
            f"💎 **Premium Access** - Unlimited viewing!\n"
            f"📚 **{total_for_you} for you** · **{total_cat} in category**\n\n"
            "**🌫️ Blurred Previews:**"
        )

        # Show first 3 content previews
        for i, content in enumerate(content_list[:3]):
            media_type = content.get('media_type', 'text')

            if media_type == 'text':
                blurred_text = content.get('blurred_text') or "**Blurred Text** Reveal to read"
                preview_text = blurred_text[:80] + "..." if len(blurred_text) > 80 else blurred_text
            elif media_type == 'image':
                preview_text = "📸 **Blurred Photo** - Hidden behind blur filter"
            elif media_type == 'video':
                preview_text = "🎥 **Blurred Video** - Hidden behind blur filter"

            reveal_status = "✅ REVEALED" if content['user_revealed'] else "🔒 Premium Required"

            if media_type in ['image', 'video']:
                content_icon = "📸" if media_type == 'image' else "🎥"
                text += f"\n\n**{i+1}.** {content_icon} {preview_text}\n_{reveal_status}_"
            else:
                text += f"\n\n**{i+1}.** {preview_text}\n_{reveal_status}_"

        # Create content buttons  
        keyboard_rows = []
        for i, content in enumerate(content_list):  # Show all available items (up to 10)
            media_type = content.get('media_type', 'text')

            if content['user_revealed']:
                if media_type == 'image':
                    button_text = f"{i+1}. 📸 View Photo"
                elif media_type == 'video':
                    button_text = f"{i+1}. 🎥 Watch Video"
                else:
                    button_text = f"{i+1}. ✅ Read Again"
            else:
                if media_type == 'image':
                    button_text = f"{i+1}. 🌫️ Reveal Photo"
                elif media_type == 'video':
                    button_text = f"{i+1}. 🌫️ Reveal Video"
                else:
                    button_text = f"{i+1}. 🌫️ Reveal Text"

            keyboard_rows.append([InlineKeyboardButton(button_text, callback_data=f"vault:reveal:{content['id']}")])

        keyboard_rows.extend([
            [
                InlineKeyboardButton("📝 Submit Here", callback_data=f"vault:submit:{category_id}")
            ],
            [InlineKeyboardButton("🔙 Back to Categories", callback_data="vault:main")]
        ])

        kb = InlineKeyboardMarkup(keyboard_rows)

    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

# -------- Push notification function --------
async def push_blur_vault_tease(context):
    """Send Vault teaser to all active users at 9:45pm"""
    try:
        from utils.hybrid_db import get_active_user_ids_hybrid
        users = get_active_user_ids_hybrid()
    except Exception:
        # Fallback to testers
        users = [8482725798, 647778438, 1437934486]

    tease_text = (
        "😏 Blur-Reveal Vault unlocks tonight!\n"
        "Hidden secrets... blurred confessions... wanna peek? 👀\n\n"
        "Free shows only blur 🌫️\n"
        "Premium reveals the truth 🔓💎\n\n"
        "/vault"
    )

    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, tease_text)
            sent += 1
        except Exception:
            pass

    print(f"[vault-tease] sent={sent}/{len(users)}")

# ============ REVEAL SYSTEM ============

async def handle_content_reveal(query, context: ContextTypes.DEFAULT_TYPE, content_id: int, user_id: int):
    """Handle revealing vault content"""
    is_premium = reg.has_active_premium(user_id)

    # Get content info
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT content_text, blurred_text, reveal_cost, submitter_id, media_type,
                   file_url, thumbnail_url, blurred_thumbnail_url
            FROM vault_content 
            WHERE id = %s AND approval_status = 'approved'
        """, (content_id,))

        content_info = cur.fetchone()
        if not content_info:
            await query.answer("❌ Content not found")
            return

    content_text, blurred_text, reveal_cost, submitter_id, media_type, file_url, thumbnail_url, blurred_thumbnail_url = content_info

    # Check if already revealed
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT id FROM vault_interactions 
            WHERE user_id = %s AND content_id = %s AND action = 'revealed'
        """, (user_id, content_id))

        already = cur.fetchone() is not None

    if already:
        # fetch media info
        with reg._conn() as con, con.cursor() as cur2:
            cur2.execute("""
                SELECT media_type, file_id, file_url, content_text, category_id
                FROM vault_content
                WHERE id=%s AND approval_status='approved'
            """, (content_id,))
            row = cur2.fetchone()

        if not row:
            return await query.edit_message_text("❌ Item missing or not approved.")

        media_type, file_id, file_url, content_text, cat_id = row

        try:
            if media_type == "text":
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=content_text or "📝 (empty text content)",
                    reply_markup=_back_kb(cat_id)  # 👈 buttons on text
                )
            elif media_type == "image":
                if file_id:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=file_id,
                        caption=content_text or "📸 Submitted Photo",
                        protect_content=True,
                        reply_markup=_back_kb(cat_id)  # 👈 buttons on photo
                    )
                elif file_url:
                    msg = await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=file_url,
                        caption=content_text or "📸 Submitted Photo",
                        protect_content=True,
                        reply_markup=_back_kb(cat_id)  # 👈 buttons on photo
                    )
                    # harvest and store file_id for future
                    try:
                        if msg.photo:
                            new_id = msg.photo[-1].file_id
                            with reg._conn() as con, con.cursor() as cur3:
                                cur3.execute("UPDATE vault_content SET file_id=%s WHERE id=%s", (new_id, content_id))
                                con.commit()
                    except Exception:
                        pass
            elif media_type == "video":
                if file_id:
                    await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=file_id,
                        caption=content_text or "🎬 Submitted Video",
                        protect_content=True,
                        reply_markup=_back_kb(cat_id)  # 👈 buttons on video
                    )
                elif file_url:
                    msg = await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=file_url,
                        caption=content_text or "🎬 Submitted Video",
                        protect_content=True,
                        reply_markup=_back_kb(cat_id)  # 👈 buttons on video
                    )
                    try:
                        if msg.video:
                            new_id = msg.video.file_id
                            with reg._conn() as con, con.cursor() as cur3:
                                cur3.execute("UPDATE vault_content SET file_id=%s WHERE id=%s", (new_id, content_id))
                                con.commit()
                    except Exception:
                        pass
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id, 
                    text=content_text or "📝 Unknown content type",
                    reply_markup=_back_kb(cat_id)  # 👈 buttons on fallback
                )

        except Exception as e:
            return await query.edit_message_text(f"❌ Re-send failed: {e}")

        # clean up old card
        try:
            await query.delete_message()  # clean UI
        except Exception:
            try:
                await query.edit_message_text("✅ Revealed again — content above.")
            except Exception:
                pass
        return

    # Premium users get unlimited reveals
    if is_premium:
        can_reveal = True
        cost_text = "💎 Premium Unlimited"
    else:
        # Check tokens for free users

        can_reveal = True  # Premium users can always reveal
        cost_text = f"💎 Premium Access"

    if not can_reveal:
        text = (
            "❌ **Insufficient Tokens**\n\n"
            f"This content requires Premium access.\n\n"
            "💎 Get unlimited reveals with Premium!"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium:open")],
            [InlineKeyboardButton("🔙 Back", callback_data="vault:main")]
        ])

        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        return

    # Show reveal confirmation based on media type
    if media_type == 'text':
        preview = blurred_text[:150] + "..." if len(blurred_text) > 150 else blurred_text
        text = (
            "🌫️ **Ready to Reveal?**\n\n"
            f"**Blurred Preview:**\n_{preview}_\n\n"
            f"**Cost:** {cost_text}\n\n"
            "This will permanently reveal the content for you."
        )
    elif media_type == 'image':
        text = (
            "🌫️ **Ready to Reveal Photo?**\n\n"
            "📸 **Blurred Image Preview**\n"
            "_Photo is currently hidden behind blur filter_\n\n"
            f"**Cost:** {cost_text}\n\n"
            "This will permanently unblur the photo for you."
        )
    elif media_type == 'video':
        text = (
            "🌫️ **Ready to Reveal Video?**\n\n"
            "🎥 **Blurred Video Preview**\n"
            "_Video is currently hidden behind blur filter_\n\n"
            f"**Cost:** {cost_text}\n\n"
            "This will permanently unblur the video for you."
        )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔓 Yes, Reveal Now!", callback_data=f"vault:confirm:{content_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="vault:main")]
    ])

    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def simple_photo_reveal(query, context: ContextTypes.DEFAULT_TYPE, content_id: int, user_id: int):
    """SIMPLE DIRECT PHOTO REVEAL - NO BULLSHIT"""
    log.info(f"🚀 SIMPLE PHOTO REVEAL CALLED - Content ID: {content_id}, User: {user_id}")
    try:
        # Get photo file_id from database
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT file_url, category_id FROM vault_content WHERE id = %s", (content_id,))
            result = cur.fetchone()

        log.info(f"📊 Database result: {result}")

        if not result or not result[0]:
            log.error(f"❌ NO PHOTO FOUND for content {content_id}")
            await query.edit_message_text("❌ Photo not found")
            return

        file_id, cat_id = result
        log.info(f"📊 File ID retrieved: {file_id}")

        # Send photo directly - NO COMPLEX SHIT
        log.info(f"🔄 About to send photo...")
        photo_result = await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=file_id,
            caption="✅ Photo Revealed!"
        )
        log.info(f"✅ PHOTO SENT! Message ID: {photo_result.message_id}")

        # Update message
        try:
            await query.edit_message_text(
                "✅ Revealed\n\nContent is now visible above.",
                reply_markup=_back_kb(cat_id)
            )
        except Exception:
            pass
        log.info(f"✅ Message updated successfully")

    except Exception as e:
        log.error(f"❌ SIMPLE REVEAL ERROR: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def confirm_content_reveal(query, context: ContextTypes.DEFAULT_TYPE, content_id: int, user_id: int):
    """YOUR EXACT REVEAL CONFIRMATION HANDLER"""
    await query.answer()

    # Check if user is premium or admin
    is_premium = reg.has_active_premium(user_id)
    is_admin = user_id == 647778438
    
    if not is_premium and not is_admin:
        await query.edit_message_text(
            "❌ **Premium Required**\n\n"
            "🔒 Only Premium users can view vault content\n\n"
            "💎 Upgrade to Premium to access all content!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Get Premium", callback_data="premium:open")],
                [InlineKeyboardButton("🔙 Back", callback_data="vault:main")]
            ]),
            parse_mode="Markdown"
        )
        return

    # fetch row (must be approved)
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT media_type, file_id, file_url, content_text, category_id
            FROM vault_content
            WHERE id=%s AND approval_status='approved'
        """, (content_id,))
        row = cur.fetchone()

    if not row:
        return await query.edit_message_text("❌ Item not found or not approved.")

    media_type, file_id, file_url, content_text, cat_id = row

    # send media by file_id; fallback to file_url once and harvest id
    new_file_id = None
    try:
        if media_type == "text":
            # Handle text content reveal with back buttons attached
            text_content = content_text or "📝 (empty text content)"
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=text_content,
                reply_markup=_back_kb(cat_id)  # 👈 buttons attached to content
            )
            # clean up old card
            try:
                await query.delete_message()  # clean UI
            except Exception:
                try:
                    await query.edit_message_text("✅ Revealed — content is visible above.")
                except Exception:
                    pass
        elif file_id:
            if media_type == "image":
                msg = await context.bot.send_photo(
                    chat_id=query.message.chat_id, photo=file_id,
                    caption="📸 Actual submitted image", protect_content=True,
                    reply_markup=_back_kb(cat_id)  # 👈 buttons on photo
                )
            elif media_type == "video":
                msg = await context.bot.send_video(
                    chat_id=query.message.chat_id, video=file_id,
                    caption="🎬 Actual submitted video", protect_content=True,
                    reply_markup=_back_kb(cat_id)  # 👈 buttons on video
                )
            else:
                # default attempt as photo
                msg = await context.bot.send_photo(
                    chat_id=query.message.chat_id, photo=file_id,
                    caption="📸 Submitted Media", protect_content=True,
                    reply_markup=_back_kb(cat_id)  # 👈 buttons on media
                )
            # clean up old card
            try:
                await query.delete_message()  # clean UI
            except Exception:
                try:
                    await query.edit_message_text("✅ Revealed — content is visible above.")
                except Exception:
                    pass
        elif file_url:
            # fallback: try URL and then harvest a new file_id
            msg = await context.bot.send_photo(
                chat_id=query.message.chat_id, photo=file_url,
                caption="📸 Actual submitted image", protect_content=True,
                reply_markup=_back_kb(cat_id)  # 👈 buttons on photo
            )
            try:
                if msg.photo:
                    new_file_id = msg.photo[-1].file_id
            except Exception:
                pass
            # clean up old card
            try:
                await query.delete_message()  # clean UI
            except Exception:
                try:
                    await query.edit_message_text("✅ Revealed — content is visible above.")
                except Exception:
                    pass
        else:
            return await query.edit_message_text("⚠️ Media not available. Ask admin to re-submit.")

        # mark this item as revealed for this user
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                INSERT INTO vault_interactions(user_id, content_id, action, created_at)
                VALUES (%s, %s, 'revealed', NOW())
                ON CONFLICT (user_id, content_id, action) DO NOTHING
            """, (user_id, content_id))
            con.commit()

        # harvest id if needed
        if not file_id and new_file_id:
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("UPDATE vault_content SET file_id=%s WHERE id=%s", (new_file_id, content_id))
                con.commit()

        # bump counters
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                UPDATE vault_content
                   SET view_count = COALESCE(view_count,0)+1,
                       reveal_count = COALESCE(reveal_count,0)+1,
                       updated_at = NOW()
                 WHERE id=%s
            """, (content_id,))
            con.commit()

    except Exception as e:
        await query.edit_message_text(f"❌ Reveal failed: {e}")


# ============ SENDING FUNCTIONS (for navigation) ============

async def send_category_page(context, chat_id: int, user_id: int, category_id: int, page: int = 1):
    """Send fresh category page with pagination support"""
    # Check if user is premium (admin bypass)
    is_premium = reg.has_active_premium(user_id)
    is_admin = user_id == 647778438  # Admin bypass

    if not is_premium and not is_admin:
        # Show non-premium message (except for admin)
        await context.bot.send_message(
            chat_id=chat_id,
            text=LOCK_TEXT,
            reply_markup=_upgrade_kb(),
            parse_mode="Markdown"
        )
        return

    # REMOVED: Daily limits - premium users can see all content without limits

    # Get category info
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT name, emoji, description FROM vault_categories WHERE id = %s", (category_id,))
        cat_info = cur.fetchone()

        if not cat_info:
            await context.bot.send_message(chat_id, "❌ Category not found")
            return

    cat_name, cat_emoji, cat_desc = cat_info
    
    # Pagination setup
    items_per_page = 10
    offset = (page - 1) * items_per_page
    
    # Get total count for pagination
    total_count = get_vault_content_total_count(category_id, user_id)
    total_pages = (total_count + items_per_page - 1) // items_per_page  # Ceiling division
    
    # Get content for current page
    content_list = get_vault_content_by_category(category_id, user_id, items_per_page, offset)

    if not content_list:
        text = f"{cat_emoji} **{cat_name}**\n\n🔒 No content available in this category yet.\n\nBe the first to submit something exciting!"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Submit Content", callback_data=f"vault:submit:{category_id}")],
            [InlineKeyboardButton("🔙 Back to Categories", callback_data="vault:main")]
        ])
        await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="Markdown")
        return

    # Build content list text and keyboard (simplified version)
    text = f"{cat_emoji} **{cat_name}**\n\n"
    if cat_desc:
        text += f"_{cat_desc}_\n\n"

    text += f"📋 **Available Content** (Page {page}/{total_pages})\n"
    text += f"📊 **Total Items:** {total_count} | **Showing:** {len(content_list)}\n\n"

    # Build keyboard for content items
    keyboard_rows = []
    for idx, item in enumerate(content_list[:10], 1):  # Show max 10 items
        item_id = item.get('id')
        blurred_preview = item.get('blurred_text', '🔒 Tap to reveal')[:30] + "..."
        
        keyboard_rows.append([
            InlineKeyboardButton(f"{idx}. {blurred_preview}", callback_data=f"vault:reveal:{item_id}")
        ])

    # Add pagination navigation buttons
    nav_buttons = []
    
    # Previous page button (if not on first page)
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"vault:cat:{category_id}:{page-1}"))
    
    # Next page button (if not on last page)
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"vault:cat:{category_id}:{page+1}"))
    
    # Add navigation row if we have nav buttons
    if nav_buttons:
        keyboard_rows.append(nav_buttons)
    
    # Back to categories button
    keyboard_rows.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="vault:main")])
    
    kb = InlineKeyboardMarkup(keyboard_rows)
    await context.bot.send_message(chat_id, text, reply_markup=kb, parse_mode="Markdown")

# ============ CALLBACK HANDLERS ============

async def handle_vault_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all vault-related callback queries"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    await query.answer()

    try:
        if data == "vault:main":
            # Delete media card and send fresh vault home
            chat_id = query.message.chat_id
            await _delete_quiet(query)  # delete media card if any
            # ✅ Send categories UI directly (not /vault text)
            await _send_vault_home(context, chat_id, user_id)

        elif data.startswith("vault:cat:"):
            parts = data.split(":")
            category_id = int(parts[2])
            page = int(parts[3]) if len(parts) > 3 else 1  # Default to page 1
            try:
                # Delete media card and send fresh category list
                chat_id = query.message.chat_id
                await _delete_quiet(query)  # delete media card
                await send_category_page(context, chat_id, user_id, category_id, page)  # fresh list with pagination
                log.info(f"User {user_id} navigated to category {category_id}, page {page}")
            except Exception as e:
                log.error(f"Error showing category {category_id}, page {page}: {e}")
                await query.answer("❌ Navigation failed")

        elif data.startswith("vault:reveal:"):
            content_id = int(data.split(":")[2])
            await handle_content_reveal(query, context, content_id, user_id)

        elif data.startswith("vault:confirm:"):
            content_id = int(data.split(":")[2])
            # SIMPLE DIRECT PHOTO REVEAL - NO TOKENS
            await confirm_content_reveal(query, context, content_id, user_id)

        elif data.startswith("vault:like:"):
            content_id = int(data.split(":")[2])
            await handle_content_like(query, content_id, user_id)

        elif data == "vault:submit":
            await start_vault_submission(query, user_id)

        elif data.startswith("vault:submit:") and len(data.split(":")) == 3:
            # Handle category-specific submission
            category_id = int(data.split(":")[2])
            await handle_category_submission(query, category_id, user_id)

        elif data.startswith("vault:text_input:"):
            # Handle text input start
            category_id = int(data.split(":")[2])
            await handle_text_input_start(query, context, category_id, user_id)

        elif data.startswith("vault:media_upload:"):
            # Handle media upload start
            category_id = int(data.split(":")[2])
            await handle_media_upload_start(query, category_id, user_id)

        elif data == "vault:stats":
            await show_vault_stats(query, user_id)

        elif data == "vault:random":
            await show_random_content(query, user_id)

    except Exception as e:
        log.error(f"Vault callback error: {e}")
        try:
            await query.answer("❌ Something went wrong. Please try again.")
        except:
            pass


# ============ TOKEN FUNCTIONS - REMOVED PER USER REQUEST ============
# All token-related functions removed - only Premium/Non-Premium logic


# ============ VAULT SUBMISSION HANDLERS ============

async def start_vault_submission(query, user_id: int):
    """Start vault content submission process"""
    if not reg.has_active_premium(user_id):
        text = (
            "📝 **Content Submission**\n\n"
            "Only Premium members can submit content to the vault.\n\n"
            "💎 Upgrade to Premium to:\n"
            "• Submit your own secrets\n"
            "• Share exciting content with community\n"
            "• Get priority approval"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="premium:open")],
            [InlineKeyboardButton("🔙 Back", callback_data="vault:main")]
        ])

        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        return

    # Show submission categories
    categories = get_vault_categories()

    text = (
        "📝 **Submit to Vault**\n\n"
        "💰 **EARN COINS:** Each submission = +1 coin!\n"
        "🎁 Help us grow with new content daily\n"
        "🔄 More submissions = More variety for everyone\n\n"
        "Choose a category for your submission:\n"
        "_Your content will be reviewed before going live_"
    )

    keyboard_rows = []
    for cat in categories:
        button_text = f"{cat['emoji']} {cat['name']}"
        keyboard_rows.append([InlineKeyboardButton(button_text, callback_data=f"vault:submit:{cat['id']}")])

    keyboard_rows.append([InlineKeyboardButton("🔙 Back", callback_data="vault:main")])

    kb = InlineKeyboardMarkup(keyboard_rows)
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def handle_category_submission(query, category_id: int, user_id: int):
    """Handle submission for a specific category"""
    # Get category info
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT name, emoji, description FROM vault_categories WHERE id = %s", (category_id,))
        cat_info = cur.fetchone()

        if not cat_info:
            await query.answer("❌ Category not found")
            return

    cat_name, cat_emoji, cat_desc = cat_info
    # Check if it's a media category
    if cat_name in ['Blur Pictures', 'Blur Videos']:
        media_type = 'image' if cat_name == 'Blur Pictures' else 'video'
        media_emoji = "📸" if cat_name == 'Blur Pictures' else "🎥"

        text = (
            f"{cat_emoji} **Submit to {cat_name}**\n\n"
            f"💰 **EARN COINS:** Each submission = +1 coin!\n"
            f"🎁 Help us grow with new content daily\n\n"
            f"_{cat_desc}_\n\n"
            f"{media_emoji} **Ready to submit your {media_type}?**\n\n"
            f"📤 **How it works:**\n"
            f"1. Click 'Upload {media_type.title()}' below\n"
            f"2. Send your {media_type} file to the bot\n"
            f"3. Your {media_type} will be automatically blurred\n"
            f"4. Others can view it with Premium access\n\n"
            f"🔥 **This is the hottest feature!** People love discovering hidden {media_type}s!"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{media_emoji} Upload {media_type.title()}", callback_data=f"vault:media_upload:{category_id}")],
            [InlineKeyboardButton("🔙 Back to Categories", callback_data="vault:submit")]
        ])
    else:
        # Text submission
        text = (
            f"{cat_emoji} **Submit to {cat_name}**\n\n"
            f"💰 **EARN COINS:** Each submission = +1 coin!\n"
            f"🎁 Help us grow with new content daily\n\n"
            f"_{cat_desc}_\n\n"
            "✍️ **Write your submission:**\n\n"
            "Type your message below and it will be submitted to this category.\n"
            "Your content will be reviewed by admins before going live.\n\n"
            "💡 _Your submission will be automatically blurred for other users_"
        )

        # Text submission preparation (state would be managed separately in full implementation)

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Ready to Type", callback_data=f"vault:text_input:{category_id}")],
            [InlineKeyboardButton("🔙 Back to Categories", callback_data="vault:submit")]
        ])

    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def handle_text_input_start(query, context, category_id: int, user_id: int):
    """Start text input process for vault submission using proper text framework"""
    
    # Import vault_text module for proper state management
    from . import vault_text
    
    # Create a mock update object for start_vault_text_input
    update = type('MockUpdate', (), {
        'callback_query': query,
        'effective_user': query.from_user
    })()
    
    # Call the proper text framework function
    success = await vault_text.start_vault_text_input(update, context, category_id)
    
    if not success:
        await query.answer("❌ Could not start text input. Please try again.")
        return

async def handle_media_upload_start(query, category_id: int, user_id: int):
    """Start media upload process for vault submission"""
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT name, emoji FROM vault_categories WHERE id = %s", (category_id,))
        cat_info = cur.fetchone()

        if not cat_info:
            await query.answer("❌ Category not found")
            return

    cat_name, cat_emoji = cat_info
    media_type = 'photo' if cat_name == 'Blur Pictures' else 'video'
    media_emoji = "📸" if cat_name == 'Blur Pictures' else "🎥"

    text = (
        f"{cat_emoji} **{cat_name} Upload**\n\n"
        f"{media_emoji} **Send your {media_type} now!**\n\n"
        f"📤 **Instructions:**\n"
        f"• Just send me your {media_type} file\n"
        f"• I'll automatically blur it for the vault\n"
        f"• Others can reveal it using tokens\n"
        f"• You'll earn tokens when people reveal your content\n\n"
        f"🔥 **Ready? Send your {media_type} in the next message!**\n\n"
        f"💡 _Your {media_type} will be reviewed before going live_"
    )

    # Store user's submission state in the database temporarily
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO vault_user_states (user_id, category_id, state, created_at) 
            VALUES (%s, %s, 'awaiting_media', NOW())
            ON CONFLICT (user_id) DO UPDATE SET 
            category_id = %s, state = 'awaiting_media', created_at = NOW()
        """, (user_id, category_id, category_id))
        con.commit()

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel Upload", callback_data="vault:submit")]
    ])

    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def show_vault_stats(query, user_id: int):
    """Show user's vault statistics - PREMIUM ONLY"""
    # Get daily limits info
    limits = get_daily_reveal_limits(user_id)

    with reg._conn() as con, con.cursor() as cur:
        # Get user stats
        cur.execute("""
            SELECT 
                COUNT(CASE WHEN action = 'revealed' THEN 1 END) as reveals_made,
                COUNT(CASE WHEN action = 'liked' THEN 1 END) as likes_given,
                SUM(tokens_spent) as total_tokens_spent
            FROM vault_interactions 
            WHERE user_id = %s
        """, (user_id,))

        stats = cur.fetchone() or (0, 0, 0)
        reveals_made, likes_given, total_tokens_spent = stats

        # Get submitted content stats
        cur.execute("""
            SELECT 
                COUNT(*) as submissions,
                COUNT(CASE WHEN approval_status = 'approved' THEN 1 END) as approved,
                SUM(reveal_count) as total_reveals_received
            FROM vault_content 
            WHERE submitter_id = %s
        """, (user_id,))

        submission_stats = cur.fetchone() or (0, 0, 0)
        submissions, approved, total_reveals_received = submission_stats



    text = (
        "📊 **Your Premium Vault Stats**\n\n"
        f"💎 **Premium Access** - Unlimited viewing!\n\n"
        f"🔓 **Today's Reveals:** {limits['text_reveals_used']}/{limits['text_reveals_max']} text, {limits['media_reveals_used']}/{limits['media_reveals_max']} media\n"
        f"⏰ **Resets:** Daily at midnight (preserves content scarcity)\n\n"
        f"📈 **All-Time Stats:**\n"
        f"• **Content Revealed:** {reveals_made}\n"
        f"• **Likes Given:** {likes_given}\n"
        f"• **Premium User** - Unlimited access\n\n"
        f"📝 **Your Submissions:** {submissions}\n"
        f"✅ **Approved:** {approved}\n"
        f"🔥 **Total Reveals Received:** {total_reveals_received or 0}\n\n"
        f"💾 **Storage Used:** {limits['storage_limit_mb']}MB limit"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Vault", callback_data="vault:main")]
    ])

    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def show_random_content(query, user_id: int):
    """Show random vault content"""
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT id, blurred_text, reveal_cost, category_id
            FROM vault_content 
            WHERE approval_status = 'approved' 
                AND submitter_id != %s
                AND id NOT IN (
                    SELECT content_id FROM vault_interactions 
                    WHERE user_id = %s AND action = 'revealed'
                )
            ORDER BY RANDOM()
            LIMIT 1
        """, (user_id, user_id))

        random_content = cur.fetchone()

        if not random_content:
            text = "🎲 No new content available for random reveal!"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="vault:main")]
            ])
        else:
            content_id, blurred_text, reveal_cost, category_id = random_content
            preview = blurred_text[:100] + "..." if len(blurred_text) > 100 else blurred_text

            text = (
                "🎲 **Random Content**\n\n"
                f"**Preview:**\n_{preview}_\n\n"
                f"💎 **Premium Access Required**"
            )

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔓 Reveal", callback_data=f"vault:reveal:{content_id}")],
                [InlineKeyboardButton("🎲 Another Random", callback_data="vault:random")],
                [InlineKeyboardButton("🔙 Back", callback_data="vault:main")]
            ])

    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def handle_vault_photo(update, context):
    """Handle photo upload during vault submission - YOUR EXACT BULLETPROOF VERSION"""
    user_id = update.effective_user.id
    msg = update.message

    # Check if user is in media submission mode
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT category_id, state FROM vault_user_states WHERE user_id = %s AND state = 'awaiting_media'", (user_id,))
        state_info = cur.fetchone()

        if not state_info:
            return

        category_id, state = state_info

    # YOUR EXACT SUBMISSION HANDLER LOGIC
    if msg.photo:
        file_id = msg.photo[-1].file_id
        media_type = "image"
    elif msg.video:
        file_id = msg.video.file_id
        media_type = "video"
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("image/"):
        file_id = msg.document.file_id
        media_type = "image"
    else:
        return await msg.reply_text("❌ Please send a photo/video.")

    # optional: best-effort file_url (not required for sending later)
    file_url = None
    try:
        tf = await context.bot.get_file(file_id)
        file_url = tf.file_path  # may be short-lived; we still save it for backfill fallback
    except Exception:
        pass

    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO vault_content (
                submitter_id, category_id, content_text, blurred_text,
                media_type, file_url, file_id, blur_level, reveal_cost,
                approval_status, created_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                'pending', NOW()
            )
            RETURNING id
        """, (
            msg.from_user.id, category_id,
            "📸 Submitted Photo", "**Blurred Photo** Reveal for coins",
            media_type, file_url, file_id, 95, 3
        ))
        content_id = cur.fetchone()[0]

        # Clear user state
        cur.execute("DELETE FROM vault_user_states WHERE user_id = %s", (user_id,))
        con.commit()

        # Send success message and schedule auto-deletion after 20 seconds
        sent_message = await msg.reply_text(
            f"✅ **Photo Submitted Successfully!**\n\n"
            f"📸 **Content ID:** #{content_id}\n"
            f"📋 **Status:** Pending Admin Review\n\n"
            "💰 **Coin Reward System:**\n"
            "• You'll earn 1 coin when your photo gets approved\n"
            "• No coins awarded for rejected submissions\n"
            "• Quality content increases approval chances\n\n"
            "🔥 Your photo will be available in the vault once approved!"
        )
        
        # Schedule automatic deletion after 20 seconds
        import asyncio
        async def delete_vault_photo_message():
            try:
                await asyncio.sleep(20)
                await context.bot.delete_message(
                    chat_id=sent_message.chat_id,
                    message_id=sent_message.message_id
                )
            except Exception as e:
                # Ignore errors (message might already be deleted by user)
                pass
        
        # Create background task for deletion
        asyncio.create_task(delete_vault_photo_message())

        # Notify admins about new content submission
        await notify_admins_new_submission(context, user_id, content_id, media_type, "Blur Pictures")

async def handle_vault_video(update, context):
    """Handle video upload during vault submission - supports all video types"""
    user_id = update.effective_user.id

    # Check if user is in media submission mode
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT category_id, state FROM vault_user_states WHERE user_id = %s AND state = 'awaiting_media'", (user_id,))
        state_info = cur.fetchone()

        if not state_info:
            # User not in submission mode, ignore
            return

        category_id, state = state_info

    # --- Detect all possible video-like inputs ---
    msg = update.message
    media_type = None
    file_id = None

    if msg.video:                       # normal video
        media_type = "video"
        file_id = msg.video.file_id
    elif msg.video_note:                 # round video note
        media_type = "video_note"
        file_id = msg.video_note.file_id
    elif msg.animation:                  # GIF/animation
        media_type = "animation"
        file_id = msg.animation.file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/"):
        media_type = "document_video"    # video sent as document
        file_id = msg.document.file_id
    else:
        await msg.reply_text("❌ Please send a video (not a link).")
        return

    # Optional: get a file_url as fallback (not required if file_id present)
    file_url = None
    try:
        tf = await context.bot.get_file(file_id)
        file_url = tf.file_path
    except Exception:
        pass

    # Store in DB — use RETURNING id (never use lastrowid with psycopg2)
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO vault_content (
                submitter_id, category_id, content_text, blurred_text,
                media_type, file_url, file_id, blur_level, reveal_cost,
                approval_status, created_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                'pending', NOW()
            )
            RETURNING id
        """, (
            user_id, category_id,
            "🎥 Submitted Video", "🌫️ **Blurred Video** — Reveal to watch",
            media_type, file_url, file_id, 95, 4
        ))
        new_content_id = cur.fetchone()[0]

        # Clear user state
        cur.execute("DELETE FROM vault_user_states WHERE user_id = %s", (user_id,))
        con.commit()

        # Send detailed confirmation to user and schedule auto-deletion after 20 seconds
        sent_message = await update.message.reply_text(
            "🎥 **Video Submitted Successfully!**\n\n"
            "✅ **Submission Details:**\n"
            f"• Content ID: #{new_content_id}\n"
            f"• Category: Blur Videos\n"
            f"• Status: Pending Admin Review\n\n"
            "💰 **Coin Reward System:**\n"
            "• You'll earn 1 coin when your video gets approved\n"
            "• No coins awarded for rejected submissions\n"
            "• Quality content increases approval chances\n\n"
            "📋 **What happens next:**\n"
            "• Your video will be reviewed by admins within 24 hours\n"
            "• Once approved, it will appear in the vault with blur effects\n"
            "• Others can view it with Premium access!\n\n"
            "🔥 **Together we can create the hottest content library!**",
            parse_mode="Markdown"
        )
        
        # Schedule automatic deletion after 20 seconds
        import asyncio
        async def delete_vault_video_message():
            try:
                await asyncio.sleep(20)
                await context.bot.delete_message(
                    chat_id=sent_message.chat_id,
                    message_id=sent_message.message_id
                )
            except Exception as e:
                # Ignore errors (message might already be deleted by user)
                pass
        
        # Create background task for deletion
        asyncio.create_task(delete_vault_video_message())

        # Notify admins about new content submission
        await notify_admins_new_submission(context, user_id, new_content_id, media_type, "Blur Videos")

async def notify_admins_new_submission(context, submitter_id: int, content_id: int, media_type: str, category_name: str):
    """Notify all admins about new vault content submission with media preview"""
    try:
        # Fetch fresh row
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT media_type, file_id, file_url, content_text, category_id
                FROM vault_content
                WHERE id = %s
            """, (content_id,))
            row = cur.fetchone()
        if not row:
            return
        mtype, file_id, file_url, ctext, cat_id = row

        cap = (
            "🔔 **New Vault Submission - Admin Review Required**\n\n"
            f"📂 **Category:** {category_name} (ID: {cat_id})\n"
            f"🆔 **Content ID:** #{content_id}\n"
            f"👤 **Submitter:** User {submitter_id}\n\n"
            "⚡ **Action:** Review below and approve/reject."
        )

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.error import BadRequest

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"vault_approve:{content_id}"),
             InlineKeyboardButton("❌ Reject",  callback_data=f"vault_delete:{content_id}")],
            [InlineKeyboardButton("👤 View User Info", callback_data=f"vault_userinfo:{submitter_id}")]
        ])

        from admin import ADMIN_IDS
        for admin_id in ADMIN_IDS:
            try:
                if mtype == "image":
                    # photo path (already working)
                    if file_id:
                        await context.bot.send_photo(admin_id, photo=file_id, caption=cap, reply_markup=kb, parse_mode="Markdown")
                    elif file_url:
                        await context.bot.send_photo(admin_id, photo=file_url, caption=cap, reply_markup=kb, parse_mode="Markdown")
                    else:
                        await context.bot.send_message(admin_id, cap + "\n\n⚠️ Media missing.", reply_markup=kb, parse_mode="Markdown")

                elif mtype in ("video", "document_video", "video_note", "animation"):
                    sent = False
                    # 1) try native method for each type
                    try:
                        if mtype == "video" and file_id:
                            await context.bot.send_video(admin_id, video=file_id, caption=cap, reply_markup=kb, parse_mode="Markdown", protect_content=True)
                            sent = True
                        elif mtype == "video_note" and file_id:
                            await context.bot.send_video_note(admin_id, video_note=file_id, reply_markup=kb, protect_content=True)
                            await context.bot.send_message(admin_id, cap, reply_markup=kb, parse_mode="Markdown")
                            sent = True
                        elif mtype == "animation" and file_id:
                            await context.bot.send_animation(admin_id, animation=file_id, caption=cap, reply_markup=kb, parse_mode="Markdown", protect_content=True)
                            sent = True
                        elif mtype == "document_video" and file_id:
                            await context.bot.send_document(admin_id, document=file_id, caption=cap, reply_markup=kb, parse_mode="Markdown", protect_content=True)
                            sent = True
                    except BadRequest:
                        sent = False

                    # 2) fallback: send via URL with best match
                    if not sent and file_url:
                        try:
                            if mtype == "video":
                                await context.bot.send_video(admin_id, video=file_url, caption=cap, reply_markup=kb, parse_mode="Markdown", protect_content=True)
                                sent = True
                            elif mtype == "animation":
                                await context.bot.send_animation(admin_id, animation=file_url, caption=cap, reply_markup=kb, parse_mode="Markdown", protect_content=True)
                                sent = True
                            else:
                                await context.bot.send_document(admin_id, document=file_url, caption=cap, reply_markup=kb, parse_mode="Markdown", protect_content=True)
                                sent = True
                        except BadRequest:
                            sent = False

                    # 3) last resort: send text + link
                    if not sent:
                        link_line = f"\n\n🔗 File: {file_url}" if file_url else ""
                        await context.bot.send_message(admin_id, cap + link_line + "\n\n⚠️ Preview failed. Use the link if present.", reply_markup=kb, parse_mode="Markdown")

                else:
                    # text only
                    txt = (ctext or "📝 (empty)").strip()
                    
                    # Handle long text safely - split if needed to avoid Telegram 4096 char limit
                    full_message = cap + f"\n\n📝 **Full Text:**\n{txt}"
                    
                    if len(full_message) <= 4000:  # Safe margin for Markdown parsing
                        await context.bot.send_message(admin_id, full_message, reply_markup=kb, parse_mode="Markdown")
                    else:
                        # Send header first
                        await context.bot.send_message(admin_id, cap, reply_markup=kb, parse_mode="Markdown")
                        # Send text in chunks without parse_mode to avoid Markdown issues
                        chunk_size = 3500
                        for i in range(0, len(txt), chunk_size):
                            chunk = txt[i:i + chunk_size]
                            is_last = i + chunk_size >= len(txt)
                            prefix = "📝 **Full Text:**\n" if i == 0 else "📝 **Continued:**\n"
                            await context.bot.send_message(admin_id, f"{prefix}{chunk}", parse_mode=None)

            except Exception as e:
                log.warning(f"Admin notify failed for {admin_id}: {e}")
    except Exception as e:
        log.error(f"Admin notification error: {e}")

async def handle_vault_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text submissions for vault"""
    # Check if user is in text submission mode
    user_data = context.user_data or {}
    if user_data.get('vault_mode') != 'text_input':
        return  # Not in vault text mode, let other handlers process

    user_id = update.effective_user.id
    category_id = user_data.get('vault_category_id')

    if not category_id:
        await update.message.reply_text("❌ Submission session expired. Please start over.")
        context.user_data.clear()
        return

    text_content = update.message.text

    # Store text submission in database
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Create blurred version for text content
            blurred_content = create_smart_blur(text_content, 70) if text_content else "**Blurred Text** Reveal to read"

            # Store in database
            cur.execute("""
                INSERT INTO vault_content (submitter_id, category_id, content_text, blurred_text, media_type, approval_status)
                VALUES (%s, %s, %s, %s, 'text', 'pending')
                RETURNING id
            """, (user_id, category_id, text_content, blurred_content))

            content_id = cur.fetchone()[0]
            con.commit()

            # Send success message and schedule auto-deletion after 20 seconds
            sent_message = await update.message.reply_text(
                "✅ **Your text has been submitted!**\n\n"
                f"📝 **Content:** {text_content[:100]}{'...' if len(text_content) > 100 else ''}\n\n"
                "💰 **Coin Reward System:**\n"
                "• You'll earn 1 coin when your content gets approved\n"
                "• No coins awarded for rejected submissions\n"
                "• Quality content increases approval chances\n\n"
                "🔍 Your submission will be reviewed by admins within 24 hours.\n"
                "Once approved, it will appear in the vault with blur effects!\n\n"
                "🔥 **Together we can create the hottest content library!**"
            )
            
            # Schedule automatic deletion after 20 seconds
            import asyncio
            async def delete_vault_text_message():
                try:
                    await asyncio.sleep(20)
                    await context.bot.delete_message(
                        chat_id=sent_message.chat_id,
                        message_id=sent_message.message_id
                    )
                except Exception as e:
                    # Ignore errors (message might already be deleted by user)
                    pass
            
            # Create background task for deletion
            asyncio.create_task(delete_vault_text_message())

            # Clear user state
            context.user_data.clear()

            # Notify admins
            await notify_admins_new_submission(context, user_id, content_id, 'text', str(category_id))

    except Exception as e:
        log.error(f"Text submission error: {e}")
        await update.message.reply_text("❌ Submission failed. Please try again.")

def register(app):
    from telegram.ext import MessageHandler, filters

    app.add_handler(CommandHandler("vault", cmd_vault), group=-1)
    app.add_handler(CommandHandler("vault_migrate", cmd_vault_migrate), group=0)  # YOUR DB MIGRATION
    app.add_handler(CommandHandler("vault_backfill", cmd_vault_backfill), group=0)  # YOUR BACKFILL UTILITY
    app.add_handler(CallbackQueryHandler(handle_vault_callbacks, pattern=r"^vault:"), group=-1)

    # OLD TEXT HANDLER - DISABLED: Now using vault_text.py with text_framework
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vault_text), group=0)

    # Media upload handlers for vault submissions
    app.add_handler(MessageHandler(filters.PHOTO, handle_vault_photo), group=-1)
    app.add_handler(MessageHandler(filters.VIDEO, handle_vault_video), group=-1)