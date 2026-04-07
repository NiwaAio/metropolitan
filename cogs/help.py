<<<<<<< HEAD
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Показать список всех команд бота")
    async def slash_help(self, interaction: discord.Interaction):
        # Собираем все команды бота (глобальные и групповые)
        commands_list = []
        for cmd in self.bot.tree.get_commands():
            # Для групп нужно добавить их подкоманды
            if isinstance(cmd, app_commands.Group):
                for sub in cmd.commands:
                    commands_list.append(f"/{cmd.name} {sub.name} – {sub.description}")
            else:
                commands_list.append(f"/{cmd.name} – {cmd.description}")
        # Сортируем и форматируем
        commands_list.sort()
        help_text = "**Доступные команды:**\n" + "\n".join(commands_list)
        # Отправляем эфемерное сообщение
        await interaction.response.send_message(help_text, ephemeral=True)
        # Через 30 секунд удаляем сообщение
        await asyncio.sleep(30)
        try:
            await interaction.delete_original_response()
        except:
            pass

async def setup(bot):
=======
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Показать список всех команд бота")
    async def slash_help(self, interaction: discord.Interaction):
        # Собираем все команды бота (глобальные и групповые)
        commands_list = []
        for cmd in self.bot.tree.get_commands():
            # Для групп нужно добавить их подкоманды
            if isinstance(cmd, app_commands.Group):
                for sub in cmd.commands:
                    commands_list.append(f"/{cmd.name} {sub.name} – {sub.description}")
            else:
                commands_list.append(f"/{cmd.name} – {cmd.description}")
        # Сортируем и форматируем
        commands_list.sort()
        help_text = "**Доступные команды:**\n" + "\n".join(commands_list)
        # Отправляем эфемерное сообщение
        await interaction.response.send_message(help_text, ephemeral=True)
        # Через 30 секунд удаляем сообщение
        await asyncio.sleep(30)
        try:
            await interaction.delete_original_response()
        except:
            pass

async def setup(bot):
>>>>>>> f2b8f40a98b88a1f5d056b8ed5b856bfc8806334
    await bot.add_cog(Help(bot))