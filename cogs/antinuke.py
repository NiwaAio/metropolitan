<<<<<<< HEAD
import discord
from discord.ext import commands
import asyncio

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ban_events = {}  # {guild_id: [(user_id, timestamp)]}
        self.channel_create_events = {}
        self.role_create_events = {}

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Отслеживаем массовые баны"""
        now = asyncio.get_event_loop().time()
        if guild.id not in self.ban_events:
            self.ban_events[guild.id] = []
        # Очищаем старые (последние 10 секунд)
        self.ban_events[guild.id] = [(uid, ts) for uid, ts in self.ban_events[guild.id] if now - ts < 10]
        self.ban_events[guild.id].append((user.id, now))
        if len(self.ban_events[guild.id]) >= 5:
            # Найдём, кто банит (нужно логировать, но нельзя получить виновника в on_member_ban)
            # Защита: временно заблокировать модерацию? Для простоты отправим в лог.
            log_channel = self.bot.get_channel(await self.get_log_channel(guild.id))
            if log_channel:
                await log_channel.send("⚠️ **Обнаружена массовая блокировка!** Возможная атака. Проверьте действия модераторов.")
            self.ban_events[guild.id] = []

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Массовое создание каналов"""
        now = asyncio.get_event_loop().time()
        guild = channel.guild
        if guild.id not in self.channel_create_events:
            self.channel_create_events[guild.id] = []
        self.channel_create_events[guild.id] = [ts for ts in self.channel_create_events[guild.id] if now - ts < 10]
        self.channel_create_events[guild.id].append(now)
        if len(self.channel_create_events[guild.id]) >= 5:
            # Отключаем создание каналов (нужно право manage_channels)
            # Для простоты – предупреждение в лог
            log_channel = self.bot.get_channel(await self.get_log_channel(guild.id))
            if log_channel:
                await log_channel.send("⚠️ **Обнаружено массовое создание каналов!** Возможная атака.")
            self.channel_create_events[guild.id] = []

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Массовое создание ролей"""
        now = asyncio.get_event_loop().time()
        guild = role.guild
        if guild.id not in self.role_create_events:
            self.role_create_events[guild.id] = []
        self.role_create_events[guild.id] = [ts for ts in self.role_create_events[guild.id] if now - ts < 10]
        self.role_create_events[guild.id].append(now)
        if len(self.role_create_events[guild.id]) >= 5:
            log_channel = self.bot.get_channel(await self.get_log_channel(guild.id))
            if log_channel:
                await log_channel.send("⚠️ **Обнаружено массовое создание ролей!** Возможная атака.")
            self.role_create_events[guild.id] = []

    async def get_log_channel(self, guild_id):
        from database import get_guild_setting
        return await get_guild_setting(guild_id, "log_channel_id")

async def setup(bot):
=======
import discord
from discord.ext import commands
import asyncio

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ban_events = {}  # {guild_id: [(user_id, timestamp)]}
        self.channel_create_events = {}
        self.role_create_events = {}

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Отслеживаем массовые баны"""
        now = asyncio.get_event_loop().time()
        if guild.id not in self.ban_events:
            self.ban_events[guild.id] = []
        # Очищаем старые (последние 10 секунд)
        self.ban_events[guild.id] = [(uid, ts) for uid, ts in self.ban_events[guild.id] if now - ts < 10]
        self.ban_events[guild.id].append((user.id, now))
        if len(self.ban_events[guild.id]) >= 5:
            # Найдём, кто банит (нужно логировать, но нельзя получить виновника в on_member_ban)
            # Защита: временно заблокировать модерацию? Для простоты отправим в лог.
            log_channel = self.bot.get_channel(await self.get_log_channel(guild.id))
            if log_channel:
                await log_channel.send("⚠️ **Обнаружена массовая блокировка!** Возможная атака. Проверьте действия модераторов.")
            self.ban_events[guild.id] = []

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Массовое создание каналов"""
        now = asyncio.get_event_loop().time()
        guild = channel.guild
        if guild.id not in self.channel_create_events:
            self.channel_create_events[guild.id] = []
        self.channel_create_events[guild.id] = [ts for ts in self.channel_create_events[guild.id] if now - ts < 10]
        self.channel_create_events[guild.id].append(now)
        if len(self.channel_create_events[guild.id]) >= 5:
            # Отключаем создание каналов (нужно право manage_channels)
            # Для простоты – предупреждение в лог
            log_channel = self.bot.get_channel(await self.get_log_channel(guild.id))
            if log_channel:
                await log_channel.send("⚠️ **Обнаружено массовое создание каналов!** Возможная атака.")
            self.channel_create_events[guild.id] = []

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Массовое создание ролей"""
        now = asyncio.get_event_loop().time()
        guild = role.guild
        if guild.id not in self.role_create_events:
            self.role_create_events[guild.id] = []
        self.role_create_events[guild.id] = [ts for ts in self.role_create_events[guild.id] if now - ts < 10]
        self.role_create_events[guild.id].append(now)
        if len(self.role_create_events[guild.id]) >= 5:
            log_channel = self.bot.get_channel(await self.get_log_channel(guild.id))
            if log_channel:
                await log_channel.send("⚠️ **Обнаружено массовое создание ролей!** Возможная атака.")
            self.role_create_events[guild.id] = []

    async def get_log_channel(self, guild_id):
        from database import get_guild_setting
        return await get_guild_setting(guild_id, "log_channel_id")

async def setup(bot):
>>>>>>> f2b8f40a98b88a1f5d056b8ed5b856bfc8806334
    await bot.add_cog(AntiNuke(bot))