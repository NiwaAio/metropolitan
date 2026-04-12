import re
from config import BAD_WORDS, WHITELIST_USER_IDS
import discord
import config

def is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    if member.id in config.ADMIN_USER_IDS:
        return True
    for role_id in config.ADMIN_ROLE_IDS:
        if member.get_role(role_id):
            return True
    return False

def is_whitelisted(user_id: int) -> bool:
    return user_id in WHITELIST_USER_IDS

def contains_bad_words(text: str) -> bool:
    text_lower = text.lower()
    for word in BAD_WORDS:
        pattern = r'\b' + re.escape(word.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return True
    return False

def contains_invite(text: str) -> bool:
    patterns = [
        r"(?:https?://)?(?:www\.)?discord(?:app)?\.(?:com|gg)/[a-zA-Z0-9]+",
        r"discord\.gg/[a-zA-Z0-9]+"
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def parse_time_duration(arg: str) -> int:
    arg = arg.lower()
    if arg.endswith('s'):
        return int(arg[:-1])
    if arg.endswith('m'):
        return int(arg[:-1]) * 60
    if arg.endswith('h'):
        return int(arg[:-1]) * 3600
    if arg.endswith('d'):
        return int(arg[:-1]) * 86400
    try:
        return int(arg)
    except:
        return 60