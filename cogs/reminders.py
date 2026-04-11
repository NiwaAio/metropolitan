import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils import parse_time_duration

class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="remind", description="Установить напоминание о страдании")
    async def remind(self, interaction: discord.Interaction, duration: str, *, text: str):
        seconds = parse_time_duration(duration)
        await interaction.response.send_message(f"Запечатлею в свитках. Напомню через {duration}: {text}", ephemeral=True)
        await asyncio.sleep(seconds)
        try:
            await interaction.user.send(f"⏰ Час страданий настал: {text}")
        except:
            pass

async def setup(bot):
    await bot.add_cog(Reminders(bot))