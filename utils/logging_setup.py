import logging
import sys

def setup_logging():
    """Setup centralized logging configuration for the bot."""
    h = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    h.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(h)
    
    # 🔒 SECURITY: Disable httpx INFO logging to prevent bot token exposure
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)  # Only show warnings/errors, not INFO requests