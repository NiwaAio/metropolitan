import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Переменная окружения DISCORD_TOKEN не найдена! Убедитесь, что файл .env существует и содержит DISCORD_TOKEN=...")

LOG_CHANNEL_ID = 1490741575431487649  # ID канала для логов
WELCOME_CHANNEL_ID = None
AUTO_ROLE_ID = None

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