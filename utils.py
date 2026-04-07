import re
from config import BAD_WORDS, WHITELIST_USER_IDS

def is_whitelisted(user_id: int) -> bool:
    """Проверяет, находится ли пользователь в белом списке (фильтр мата не применяется)"""
    return user_id in WHITELIST_USER_IDS

def contains_bad_words(text: str) -> bool:
    """Проверяет, содержит ли текст целое слово из списка BAD_WORDS"""
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
    """Переводит '15m', '2h', '1d' в секунды"""
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