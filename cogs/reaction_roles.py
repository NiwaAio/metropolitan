import discord
from discord.ext import commands
from discord import app_commands
from database import add_reaction_role, get_role_for_reaction, get_all_reaction_roles, remove_reaction_role

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Создаём группу команд /rr
    rr_group = app_commands.Group(name="rr", description="Управление реакционными ролями")

    @rr_group.command(name="add", description="Привязать эмодзи к роли для сообщения")
    @app_commands.default_permissions(administrator=True)
    async def rr_add(self, interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
        try:
            msg_id = int(message_id)
        except ValueError:
            await interaction.response.send_message("Неверный ID сообщения.", ephemeral=True)
            return
        await add_reaction_role(msg_id, emoji, role.id)
        try:
            channel = interaction.channel
            msg = await channel.fetch_message(msg_id)
            await msg.add_reaction(emoji)
            await interaction.response.send_message(f"✅ Реакция {emoji} -> {role.mention} добавлена к сообщению {msg_id}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Не удалось добавить реакцию: {e}", ephemeral=True)

    @rr_group.command(name="remove", description="Удалить привязку эмодзи к роли")
    @app_commands.default_permissions(administrator=True)
    async def rr_remove(self, interaction: discord.Interaction, message_id: str, emoji: str):
        try:
            msg_id = int(message_id)
        except ValueError:
            await interaction.response.send_message("Неверный ID сообщения.", ephemeral=True)
            return
        await remove_reaction_role(msg_id, emoji)
        await interaction.response.send_message("Привязка удалена.", ephemeral=True)

    @rr_group.command(name="list", description="Показать все привязки для сообщения")
    @app_commands.default_permissions(administrator=True)
    async def rr_list(self, interaction: discord.Interaction, message_id: str):
        try:
            msg_id = int(message_id)
        except ValueError:
            await interaction.response.send_message("Неверный ID сообщения.", ephemeral=True)
            return
        rows = await get_all_reaction_roles(msg_id)
        if not rows:
            await interaction.response.send_message("Для этого сообщения нет настроенных ролей.", ephemeral=True)
        else:
            text = "\n".join([f"{emoji} -> <@&{role_id}>" for emoji, role_id in rows])
            await interaction.response.send_message(f"Привязки:\n{text}", ephemeral=True)

    # Слушатели реакций
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        role_id = await get_role_for_reaction(payload.message_id, str(payload.emoji))
        if role_id:
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
                member = guild.get_member(payload.user_id)
                role = guild.get_role(role_id)
                if member and role:
                    await member.add_roles(role, reason="Reaction role")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        role_id = await get_role_for_reaction(payload.message_id, str(payload.emoji))
        if role_id:
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
                member = guild.get_member(payload.user_id)
                if member:
                    role = guild.get_role(role_id)
                    if role and role in member.roles:
                        await member.remove_roles(role, reason="Reaction role removed")

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
    # Добавляем группу в дерево команд, если она ещё не зарегистрирована
    if not bot.tree.get_command("rr"):
        bot.tree.add_command(ReactionRoles.rr_group)