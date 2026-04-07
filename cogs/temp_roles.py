import discord
from discord.ext import commands
from discord import app_commands
import time
from database import add_temp_role, remove_temp_role
from utils import parse_time_duration

class TempRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="temprole", description="Выдать роль на определённое время")
    @app_commands.default_permissions(manage_roles=True)
    async def slash_temprole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role, duration: str, reason: str = "Временная роль"):
        """/temprole @User @Роль 1h"""
        seconds = parse_time_duration(duration)
        until = time.time() + seconds
        await member.add_roles(role, reason=reason)
        await add_temp_role(member.id, interaction.guild.id, role.id, until)
        await interaction.response.send_message(f"{member.mention} получил роль {role.mention} на {duration}.", ephemeral=True)

    @app_commands.command(name="removetemp", description="Принудительно снять временную роль")
    @app_commands.default_permissions(manage_roles=True)
    async def slash_removetemp(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if role in member.roles:
            await member.remove_roles(role, reason="Принудительное снятие")
        await remove_temp_role(member.id, interaction.guild.id, role.id)
        await interaction.response.send_message(f"Роль {role.mention} снята с {member.mention} и запись удалена.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TempRoles(bot))