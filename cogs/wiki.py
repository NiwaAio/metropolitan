import discord
from discord.ext import commands
from discord import app_commands
from database import add_wiki_entry, get_wiki_entry, delete_wiki_entry

class Wiki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="wiki", description="Получить информацию по ID предмета")
    async def wiki(self, interaction: discord.Interaction, item_id: str):
        info = await get_wiki_entry(interaction.guild.id, item_id)
        if info:
            embed = discord.Embed(title=f"📖 {item_id}", description=info, color=discord.Color.blue())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"Информация по `{item_id}` не найдена.", ephemeral=True)

    @app_commands.command(name="wiki_add", description="Добавить или обновить запись в вики")
    @app_commands.default_permissions(administrator=True)
    async def wiki_add(self, interaction: discord.Interaction, item_id: str, info: str):
        await add_wiki_entry(interaction.guild.id, item_id, info)
        await interaction.response.send_message(f"Запись `{item_id}` добавлена/обновлена.", ephemeral=True)

    @app_commands.command(name="wiki_remove", description="Удалить запись из вики")
    @app_commands.default_permissions(administrator=True)
    async def wiki_remove(self, interaction: discord.Interaction, item_id: str):
        await delete_wiki_entry(interaction.guild.id, item_id)
        await interaction.response.send_message(f"Запись `{item_id}` удалена.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Wiki(bot))