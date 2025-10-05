
from telegram.ext import CallbackQueryHandler, MessageHandler, filters
import registration as reg

def register(app):
    # Callbacks used only by onboarding:
    #  - gender_male / gender_female
    #  - int:<key>, act:all/none, save, back
    app.add_handler(
        CallbackQueryHandler(
            reg.on_callback,
            pattern=r"^(gender_(male|female)|int:[^:]+|act:(all|none)|save|back)$"
        ),
        group=-10,    # MUST be earliest
    )

    # Text answers during registration (age / country / city):
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, reg.on_text),
        group=5,    # Lower priority than poll handlers (group=2)
    )
