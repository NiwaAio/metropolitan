import discord
from discord.ext import commands
from discord import app_commands
from database import get_guild_setting, set_guild_setting

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def send_log(guild, message: str):
        """Отправляет сообщение в канал логов, если он установлен"""
        if not guild:
            return
        log_channel_id = await get_guild_setting(guild.id, "log_channel_id")
        if log_channel_id:
            channel = guild.get_channel(log_channel_id)
            if channel and channel.permissions_for(guild.me).send_messages:
                await channel.send(message)

    # ---------- Команда для установки канала логов ----------
    @app_commands.command(name="setlogchannel", description="Установить канал для логов")
    @app_commands.default_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_guild_setting(interaction.guild.id, "log_channel_id", channel.id)
        await interaction.response.send_message(f"Канал логов установлен: {channel.mention}", ephemeral=True)

    # ---------- События логов ----------
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        content = message.content[:1000] if message.content else "[Пустое сообщение]"
        await self.send_log(message.guild, f"🗑️ **{message.author}** удалил сообщение в {message.channel.mention}:\n{content}")

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        await self.send_log(before.guild, f"✏️ **{before.author}** изменил сообщение в {before.channel.mention}\n**Было:** {before.content[:500]}\n**Стало:** {after.content[:500]}")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await self.send_log(role.guild, f"🆕 Создана роль: {role.mention} (ID: {role.id})")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        await self.send_log(role.guild, f"❌ Удалена роль: {role.name} (ID: {role.id})")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick != after.nick:
            old = before.nick or before.name
            new = after.nick or after.name
            await self.send_log(before.guild, f"📝 **{before}** изменил ник: `{old}` → `{new}`")

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        await self.send_log(guild, f"🔨 **{user}** был забанен (кем-то)")

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        await self.send_log(guild, f"✅ **{user}** был разбанен")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Логирование всех слеш-команд"""
        if not interaction.guild or interaction.type != discord.InteractionType.application_command:
            return
        if interaction.user == self.bot.user:
            return
        command_name = interaction.command.name if interaction.command else "unknown"
        args = []
        if interaction.data and "options" in interaction.data:
            for opt in interaction.data["options"]:
                args.append(f"{opt['name']}={opt['value']}")
        args_str = " ".join(args) if args else ""
        await self.send_log(interaction.guild, f"💻 **{interaction.user}** использовал команду `/{command_name} {args_str}` в {interaction.channel.mention}")

async def setup(bot):
    await bot.add_cog(Logging(bot))