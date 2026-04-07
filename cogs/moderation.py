import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import time
import datetime
from database import (
    add_warning, get_warnings, clear_warnings,
    get_guild_setting, set_guild_setting
)
from utils import contains_bad_words, contains_invite, parse_time_duration, is_whitelisted
import config

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_tracker = {}

    # Авто-модерация (без изменений)
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # Если пользователь в белом списке – пропускаем проверки мата и инвайтов
        if is_whitelisted(message.author.id):
            # Всё равно проверим спам (защита от флуда) – можно оставить
            # (код спам-защиты идёт ниже, не прерываем)
            pass  # просто идём дальше, не удаляя сообщение

        else:
            # Проверка включён ли фильтр
            filter_enabled = await get_guild_setting(message.guild.id, "filter_enabled")
            if filter_enabled is None:
                filter_enabled = True

            if filter_enabled:
                # мат
                if contains_bad_words(message.content):
                    await message.delete()
                    await message.channel.send(f"{message.author.mention}, не используйте нецензурную лексику.",
                                               delete_after=5)
                    return
                # инвайты
                if contains_invite(message.content):
                    await message.delete()
                    await message.channel.send(f"{message.author.mention}, приглашения на другие сервера запрещены.",
                                               delete_after=5)
                    return

        # Спам-защита (работает для всех, включая белый список)
        channel_id = message.channel.id
        user_id = message.author.id
        now = time.time()
        if channel_id not in self.spam_tracker:
            self.spam_tracker[channel_id] = {}
        if user_id not in self.spam_tracker[channel_id]:
            self.spam_tracker[channel_id][user_id] = []
        self.spam_tracker[channel_id][user_id] = [t for t in self.spam_tracker[channel_id][user_id] if now - t < 10]
        self.spam_tracker[channel_id][user_id].append(now)
        if len(self.spam_tracker[channel_id][user_id]) > 5:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, не спамьте.", delete_after=5)
            try:
                await message.author.timeout(duration=60, reason="Спам")
            except:
                pass
            self.spam_tracker[channel_id][user_id] = []

    # ---------- Команды модерации (требуют прав) ----------
    @app_commands.command(name="mute", description="Замутить участника на указанное время")
    @app_commands.default_permissions(moderate_members=True)
    async def slash_mute(self, interaction: discord.Interaction, member: discord.Member, duration: str = "1h", reason: str = "Не указана"):
        seconds = parse_time_duration(duration)
        if seconds > 28*86400:
            seconds = 28*86400
        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        await member.timeout(until, reason=reason)
        await interaction.response.send_message(f"{member.mention} замучен на {duration}. Причина: {reason}", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"🔇 {interaction.user} замутил {member} на {duration}. Причина: {reason}")

    @app_commands.command(name="tempban", description="Временно заблокировать участника")
    @app_commands.default_permissions(ban_members=True)
    async def tempban(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "Не указана"):
        seconds = parse_time_duration(duration)
        await member.ban(reason=reason)
        async def unban_task():
            await asyncio.sleep(seconds)
            await interaction.guild.unban(member, reason="Временный бан истёк")
        asyncio.create_task(unban_task())
        await interaction.response.send_message(f"{member.mention} забанен на {duration}. Причина: {reason}", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"⏲️ {interaction.user} временно заблокировал {member} на {duration}. Причина: {reason}")

    @app_commands.command(name="kick", description="Выгнать участника с сервера")
    @app_commands.default_permissions(kick_members=True)
    async def slash_kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Не указана"):
        await member.kick(reason=reason)
        await interaction.response.send_message(f"{member.mention} кикнут. Причина: {reason}", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"👢 {interaction.user} кикнул {member}. Причина: {reason}")

    @app_commands.command(name="ban", description="Забанить участника (по ID или упоминанию)")
    @app_commands.default_permissions(ban_members=True)
    async def slash_ban(self, interaction: discord.Interaction, member: discord.Member = None, user_id: str = None, reason: str = "Не указана"):
        if member:
            await member.ban(reason=reason)
            await interaction.response.send_message(f"{member.mention} забанен. Причина: {reason}", ephemeral=True)
            await self.log_to_channel(interaction.guild, f"🔨 {interaction.user} забанил {member}. Причина: {reason}")
        elif user_id:
            try:
                user = await self.bot.fetch_user(int(user_id))
                await interaction.guild.ban(user, reason=reason)
                await interaction.response.send_message(f"Пользователь {user} (ID {user_id}) забанен. Причина: {reason}", ephemeral=True)
                await self.log_to_channel(interaction.guild, f"🔨 {interaction.user} забанил {user} (ID {user_id}). Причина: {reason}")
            except:
                await interaction.response.send_message("Неверный ID или пользователь не найден.", ephemeral=True)
        else:
            await interaction.response.send_message("Укажите пользователя или ID.", ephemeral=True)

    @app_commands.command(name="warn", description="Выдать предупреждение участнику")
    @app_commands.default_permissions(kick_members=True)
    async def slash_warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Не указана"):
        new_count = await add_warning(member.id, interaction.guild.id)
        await interaction.channel.send(f"⚠️ {member.mention} получил предупреждение #{new_count}. Причина: {reason}")
        await interaction.response.send_message(f"Вы выдали предупреждение {member.mention}", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"⚠️ {interaction.user} выдал предупреждение #{new_count} {member}. Причина: {reason}")
        if new_count >= config.MAX_WARNINGS:
            if config.BAN_DURATION_WARN is None:
                await member.ban(reason=f"Достигнуто {config.MAX_WARNINGS} предупреждений")
                await interaction.followup.send(f"{member.mention} забанен за {config.MAX_WARNINGS} предупреждения.", ephemeral=True)
                await self.log_to_channel(interaction.guild, f"🚫 {member} забанен за {config.MAX_WARNINGS} предупреждений.")
            else:
                until = discord.utils.utcnow() + datetime.timedelta(seconds=config.MUTE_DURATION_WARN)
                await member.timeout(until, reason=f"{config.MAX_WARNINGS} предупреждений")
                await interaction.followup.send(f"{member.mention} замучен на {config.MUTE_DURATION_WARN//60} минут.", ephemeral=True)
                await self.log_to_channel(interaction.guild, f"🔇 {member} замучен на {config.MUTE_DURATION_WARN//60} минут за {config.MAX_WARNINGS} предупреждений.")
            await clear_warnings(member.id, interaction.guild.id)

    @app_commands.command(name="warnings", description="Показать количество предупреждений участника")
    async def slash_warnings(self, interaction: discord.Interaction, member: discord.Member = None):
        """Доступно всем"""
        member = member or interaction.user
        count = await get_warnings(member.id, interaction.guild.id)
        await interaction.response.send_message(f"У {member.mention} {count} предупреждений из {config.MAX_WARNINGS}.", ephemeral=True)

    @app_commands.command(name="clearwarns", description="Сбросить предупреждения участника")
    @app_commands.default_permissions(administrator=True)
    async def slash_clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        await clear_warnings(member.id, interaction.guild.id)
        await interaction.response.send_message(f"Предупреждения {member.mention} сброшены.", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"🗑️ {interaction.user} сбросил предупреждения {member}")

    @app_commands.command(name="filter", description="Включить/отключить фильтр нецензурных слов")
    @app_commands.default_permissions(administrator=True)
    async def toggle_filter(self, interaction: discord.Interaction, enabled: bool):
        await set_guild_setting(interaction.guild.id, "filter_enabled", enabled)
        status = "включён" if enabled else "выключен"
        await interaction.response.send_message(f"Фильтр нецензурных слов {status}.", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"⚙️ {interaction.user} {status} фильтр мата.")

    async def log_to_channel(self, guild, message: str):
        log_channel_id = await get_guild_setting(guild.id, "log_channel_id")
        if log_channel_id:
            channel = guild.get_channel(log_channel_id)
            if channel:
                await channel.send(message)

async def setup(bot):
    await bot.add_cog(Moderation(bot))