import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Переменная окружения DISCORD_TOKEN не найдена! Убедитесь, что файл .env существует и содержит DISCORD_TOKEN=...")

OWNER_IDS = [928223250255863848]
ADMIN_ROLE_IDS = [
    1492250367638110369,
    987654321098765432,
]
ADMIN_USER_IDS = [
    928223250255863848,
]

ROLE_COLORS = {
    "Лидер": 1487123965880041612,
    "Полковник": 1487125416463569017,
    "Офицер": 1487125669036167258,
    "Сержант": 1487126005759086782,
    "Боец": 1487126430444949634,
}

LOG_CHANNEL_ID = None
WELCOME_CHANNEL_ID = None
AUTO_ROLE_ID = None
EXCOMMUNICATED_ROLE_ID = None
APPEAL_CHANNEL_ID = 1492812233103638638

GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GOOGLE_SHEET_ID = "1mu6DcLXfK_9uWOgYS7ccJefozJfbx8yXAbSHXze8yLc"

MAX_WARNINGS = 3
MUTE_DURATION_WARN = 3600
BAN_DURATION_WARN = None

FILTER_ENABLED = True
WHITELIST_USER_IDS = [
    928223250255863848,
]
FILTER_IGNORE_CHANNELS = []
BAD_WORDS = ["хуй", "пизда", "лох", "бля", "хуйня", "нахуй", "ебать", "блядь", "мудила", "говно", "залупа", "пидор", "гандон", "отсосать", "выебать", "еблан", "уёбок", "долбоёб", "манда", "сперма", "очко", "жопа", "тварь", "сука", "шалава", "шлюха", "проститутка", "давалка", "елда", "хохол", "нигер", "чмо"]
INVITE_PATTERNS = [
    r"(?:https?://)?(?:www\.)?discord(?:app)?\.(?:com|gg)/[a-zA-Z0-9]+",
    r"discord\.gg/[a-zA-Z0-9]+"
]

import discord
INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True
INTENTS.reactions = True
INTENTS.guilds = True