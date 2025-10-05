
# handlers/fantasy_integration.py
from telegram.ext import CommandHandler, CallbackQueryHandler

from .fantasy_board import cmd_fantasy_board, on_board_callback, ensure_fantasy_board_tables
from .fantasy_requests import on_request_callback, ensure_match_request_table

def setup_fantasy_system(application):
    ensure_fantasy_board_tables()
    ensure_match_request_table()
    # Optional: let /board open the board (you can skip the command if you want only the button)
    application.add_handler(CommandHandler("board", cmd_fantasy_board))

    # Core callbacks
    application.add_handler(CallbackQueryHandler(on_board_callback,  pattern=r"^board:"))
    application.add_handler(CallbackQueryHandler(on_request_callback, pattern=r"^request:"), group=-1)
