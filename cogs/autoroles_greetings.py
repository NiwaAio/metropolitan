<<<<<<< HEAD
import discord
from discord.ext import commands
from discord import app_commands
from database import get_guild_setting, set_guild_setting

class AutoRolesGreetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        auto_role_id = await get_guild_setting(member.guild.id, "auto_role_id")
        if auto_role_id:
            role = member.guild.get_role(auto_role_id)
            if role:
                await member.add_roles(role, reason="Автороль")
        welcome_channel_id = await get_guild_setting(member.guild.id, "welcome_channel_id")
        if welcome_channel_id:
            channel = member.guild.get_channel(welcome_channel_id)
            if channel:
                await channel.send(f"🎉 Встречайте, {member.mention}! Добро пожаловать на сервер!")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        goodbye_channel_id = await get_guild_setting(member.guild.id, "welcome_channel_id")
        if goodbye_channel_id:
            channel = member.guild.get_channel(goodbye_channel_id)
            if channel:
                await channel.send(f"👋 Заглядывай, {member.display_name} покинул сервер.")

    @app_commands.command(name="setautorole", description="Установить роль для новичков")
    @app_commands.default_permissions(administrator=True)
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        await set_guild_setting(interaction.guild.id, "auto_role_id", role.id)
        await interaction.response.send_message(f"Автороль установлена: {role.mention}", ephemeral=True)

    @app_commands.command(name="setwelcomechannel", description="Установить канал для приветствий")
    @app_commands.default_permissions(administrator=True)
    async def set_welcomechannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_guild_setting(interaction.guild.id, "welcome_channel_id", channel.id)
        await interaction.response.send_message(f"Канал приветствий: {channel.mention}", ephemeral=True)

async def setup(bot):
=======
import discord
from discord.ext import commands
from discord import app_commands
from database import get_guild_setting, set_guild_setting

class AutoRolesGreetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        auto_role_id = await get_guild_setting(member.guild.id, "auto_role_id")
        if auto_role_id:
            role = member.guild.get_role(auto_role_id)
            if role:
                await member.add_roles(role, reason="Автороль")
        welcome_channel_id = await get_guild_setting(member.guild.id, "welcome_channel_id")
        if welcome_channel_id:
            channel = member.guild.get_channel(welcome_channel_id)
            if channel:
                await channel.send(f"🎉 Встречайте, {member.mention}! Добро пожаловать на сервер!")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        goodbye_channel_id = await get_guild_setting(member.guild.id, "welcome_channel_id")
        if goodbye_channel_id:
            channel = member.guild.get_channel(goodbye_channel_id)
            if channel:
                await channel.send(f"👋 Заглядывай, {member.display_name} покинул сервер.")

    @app_commands.command(name="setautorole", description="Установить роль для новичков")
    @app_commands.default_permissions(administrator=True)
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        await set_guild_setting(interaction.guild.id, "auto_role_id", role.id)
        await interaction.response.send_message(f"Автороль установлена: {role.mention}", ephemeral=True)

    @app_commands.command(name="setwelcomechannel", description="Установить канал для приветствий")
    @app_commands.default_permissions(administrator=True)
    async def set_welcomechannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_guild_setting(interaction.guild.id, "welcome_channel_id", channel.id)
        await interaction.response.send_message(f"Канал приветствий: {channel.mention}", ephemeral=True)

async def setup(bot):
>>>>>>> f2b8f40a98b88a1f5d056b8ed5b856bfc8806334
    await bot.add_cog(AutoRolesGreetings(bot))