import discord
from discord.ext import commands
from discord import app_commands
import datetime

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="userinfo", description="Показать страдания прихожанина")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = discord.Embed(title=f"Страдания {member.display_name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Печать", value=member.id, inline=False)
        embed.add_field(name="Принял страдание", value=f"<t:{int(member.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="Вступил в братство", value=f"<t:{int(member.joined_at.timestamp())}:D>", inline=True)
        embed.add_field(name="Лик", value=f"[Созерцать]({member.display_avatar.url})", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="serverinfo", description="Сведения о братстве")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=guild.name, color=discord.Color.blue())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Митрополит", value=guild.owner.mention, inline=True)
        embed.add_field(name="День сотворения", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="Душ в братстве", value=guild.member_count, inline=True)
        embed.add_field(name="Приделов", value=len(guild.channels), inline=True)
        embed.add_field(name="Санов", value=len(guild.roles), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Info(bot))