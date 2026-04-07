import discord
from discord.ext import commands
from discord import app_commands
import random

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Бросить кубик (1-6)")
    async def roll(self, interaction: discord.Interaction):
        result = random.randint(1, 6)
        await interaction.response.send_message(f"🎲 **{interaction.user.display_name}** выбросил {result}!", ephemeral=False)

    @app_commands.command(name="coinflip", description="Орёл или решка")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Орёл", "Решка"])
        await interaction.response.send_message(f"🪙 Монета показала: **{result}**", ephemeral=False)

    @app_commands.command(name="roulette", description="Рулетка (красное/чёрное)")
    async def roulette(self, interaction: discord.Interaction):
        colors = ["красный", "чёрный"]
        result = random.choice(colors)
        await interaction.response.send_message(f"🎰 Выпал **{result}**!", ephemeral=False)

async def setup(bot):
    await bot.add_cog(Gambling(bot))