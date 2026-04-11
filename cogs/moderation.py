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
from utils import contains_bad_words, contains_invite, parse_time_duration
import config

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_tracker = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        filter_enabled = await get_guild_setting(message.guild.id, "filter_enabled")
        if filter_enabled is None:
            filter_enabled = True
        if filter_enabled:
            if contains_bad_words(message.content):
                await message.delete()
                await message.channel.send(f"{message.author.mention}, не сквернословь в святом приделе.", delete_after=5)
                return
            if contains_invite(message.content):
                await message.delete()
                await message.channel.send(f"{message.author.mention}, чужие свитки запрещены.", delete_after=5)
                return
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
            await message.channel.send(f"{message.author.mention}, не искушай Господа своим многословием.", delete_after=5)
            try:
                await message.author.timeout(duration=60, reason="Спам")
            except:
                pass
            self.spam_tracker[channel_id][user_id] = []

    @app_commands.command(name="mute", description="Запечатать уста грешника на время")
    @app_commands.default_permissions(moderate_members=True)
    async def slash_mute(self, interaction: discord.Interaction, member: discord.Member, duration: str = "1h", reason: str = "Не указана"):
        seconds = parse_time_duration(duration)
        if seconds > 28*86400:
            seconds = 28*86400
        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        await member.timeout(until, reason=reason)
        await interaction.response.send_message(f"{member.mention} запечатан на {duration}. Причина: {reason}", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"🔇 {interaction.user} запечатал уста {member} на {duration}. Причина: {reason}")

    @app_commands.command(name="tempban", description="Временно изгнать из братства")
    @app_commands.default_permissions(ban_members=True)
    async def tempban(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "Не указана"):
        seconds = parse_time_duration(duration)
        await member.ban(reason=reason)
        async def unban_task():
            await asyncio.sleep(seconds)
            await interaction.guild.unban(member, reason="Временное изгнание окончено")
        asyncio.create_task(unban_task())
        await interaction.response.send_message(f"{member.mention} изгнан на {duration}. Причина: {reason}", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"⏲️ {interaction.user} изгнал {member} на {duration}. Причина: {reason}")

    @app_commands.command(name="kick", description="Вышвырнуть из придела")
    @app_commands.default_permissions(kick_members=True)
    async def slash_kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Не указана"):
        await member.kick(reason=reason)
        await interaction.response.send_message(f"{member.mention} изгнан. Причина: {reason}", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"👢 {interaction.user} изгнал {member}. Причина: {reason}")

    @app_commands.command(name="ban", description="Предать анафеме (по ID или упоминанию)")
    @app_commands.default_permissions(ban_members=True)
    async def slash_ban(self, interaction: discord.Interaction, member: discord.Member = None, user_id: str = None, reason: str = "Не указана"):
        if member:
            await member.ban(reason=reason)
            await interaction.response.send_message(f"{member.mention} предан анафеме. Причина: {reason}", ephemeral=True)
            await self.log_to_channel(interaction.guild, f"🔨 {interaction.user} предал анафеме {member}. Причина: {reason}")
        elif user_id:
            try:
                user = await self.bot.fetch_user(int(user_id))
                await interaction.guild.ban(user, reason=reason)
                await interaction.response.send_message(f"Грешник {user} (печать {user_id}) предан анафеме. Причина: {reason}", ephemeral=True)
                await self.log_to_channel(interaction.guild, f"🔨 {interaction.user} предал анафеме {user} (печать {user_id}). Причина: {reason}")
            except:
                await interaction.response.send_message("Неверная печать или грешник не найден.", ephemeral=True)
        else:
            await interaction.response.send_message("Укажи грешника или его печать.", ephemeral=True)

    @app_commands.command(name="warn", description="Вынести предостережение")
    @app_commands.default_permissions(kick_members=True)
    async def slash_warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Не указана"):
        new_count = await add_warning(member.id, interaction.guild.id)
        await interaction.channel.send(f"⚠️ {member.mention} получил предостережение #{new_count}. Причина: {reason}")
        await interaction.response.send_message(f"Ты вынес предостережение {member.mention}", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"⚠️ {interaction.user} вынес предостережение #{new_count} {member}. Причина: {reason}")

        if new_count >= config.MAX_WARNINGS:
            if config.BAN_DURATION_WARN is None:
                await member.ban(reason=f"Трижды предостережён")
                await interaction.followup.send(f"{member.mention} предан анафеме за три предостережения.", ephemeral=True)
                await self.log_to_channel(interaction.guild, f"🚫 {member} предан анафеме за три предостережения.")
            else:
                until = discord.utils.utcnow() + datetime.timedelta(seconds=config.MUTE_DURATION_WARN)
                await member.timeout(until, reason=f"Три предостережения")
                await interaction.followup.send(f"{member.mention} запечатан на {config.MUTE_DURATION_WARN//60} минут за три предостережения.", ephemeral=True)
                await self.log_to_channel(interaction.guild, f"🔇 {member} запечатан на {config.MUTE_DURATION_WARN//60} минут за три предостережения.")
            await clear_warnings(member.id, interaction.guild.id)

    @app_commands.command(name="warnings", description="Показать количество предостережений")
    async def slash_warnings(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        count = await get_warnings(member.id, interaction.guild.id)
        await interaction.response.send_message(f"У {member.mention} {count} предостережений из {config.MAX_WARNINGS}. Покайся.", ephemeral=True)

    @app_commands.command(name="clearwarns", description="Снять все предостережения (только служитель)")
    @app_commands.default_permissions(administrator=True)
    async def slash_clearwarns(self, interaction: discord.Interaction, member: discord.Member):
        await clear_warnings(member.id, interaction.guild.id)
        await interaction.response.send_message(f"Предостережения с {member.mention} сняты.", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"🗑️ {interaction.user} снял предостережения с {member}")

    @app_commands.command(name="filter", description="Включить/отключить очищение от скверны")
    @app_commands.default_permissions(administrator=True)
    async def toggle_filter(self, interaction: discord.Interaction, enabled: bool):
        await set_guild_setting(interaction.guild.id, "filter_enabled", enabled)
        status = "включено" if enabled else "выключено"
        await interaction.response.send_message(f"Очищение от скверны {status}.", ephemeral=True)
        await self.log_to_channel(interaction.guild, f"⚙️ {interaction.user} {status} очищение.")

    async def log_to_channel(self, guild, message: str):
        log_channel_id = await get_guild_setting(guild.id, "log_channel_id")
        if log_channel_id:
            channel = guild.get_channel(log_channel_id)
            if channel:
                await channel.send(message)

async def setup(bot):
    await bot.add_cog(Moderation(bot))