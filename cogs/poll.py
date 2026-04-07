import discord
from discord.ext import commands
from discord import app_commands

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="poll", description="Создать опрос с реакциями 👍/👎")
    async def poll(self, interaction: discord.Interaction, question: str):
        embed = discord.Embed(title="📊 Опрос", description=question, color=discord.Color.green())
        embed.set_footer(text=f"Автор: {interaction.user.display_name}")
        message = await interaction.channel.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await interaction.response.send_message("Опрос создан!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Poll(bot))