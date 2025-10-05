import re

def safe_display_name(uid: int) -> str:
    """
    Returns the bot-profile display name (no '@', no UID).
    Priority: profile.username -> profile.first_name -> 'User'
    """
    try:
        import registration as reg
        profile = reg.get_profile(uid)
        name = None
        if profile:
            # prefer feed username, else generic username, else first_name
            name = (profile.get("feed_username")
                    or profile.get("username")
                    or profile.get("first_name"))

        raw = (name or "User").strip()
    except Exception:
        raw = "User"

    # Clean up the name
    raw = re.sub(r"^@+", "", raw)  # Remove leading @
    raw = re.sub(r"\s+", " ", raw)  # Collapse spaces
    raw = raw.replace("@", "").replace("<", "").replace(">", "")  # Remove problematic chars
    return raw[:32]  # Keep it reasonable length