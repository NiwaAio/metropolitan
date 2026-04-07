import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Показать список всех команд бота")
    async def slash_help(self, interaction: discord.Interaction):
        commands_list = []
        for cmd in self.bot.tree.get_commands():
            if isinstance(cmd, app_commands.Group):
                for sub in cmd.commands:
                    commands_list.append(f"/{cmd.name} {sub.name} – {sub.description}")
            else:
                commands_list.append(f"/{cmd.name} – {cmd.description}")
        commands_list.sort()
        help_text = "**Доступные команды:**\n" + "\n".join(commands_list)
        await interaction.response.send_message(help_text, ephemeral=True)
        await asyncio.sleep(30)
        try:
            await interaction.delete_original_response()
        except:
            pass

async def setup(bot):
    await bot.add_cog(Help(bot))