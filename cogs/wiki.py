import discord
from discord.ext import commands
from discord import app_commands
from database import add_wiki_entry, get_wiki_entry, delete_wiki_entry

class Wiki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="wiki", description="Обрести знание о предмете из свитков")
    async def wiki(self, interaction: discord.Interaction, item_id: str):
        info = await get_wiki_entry(interaction.guild.id, item_id)
        if info:
            embed = discord.Embed(
                title=f"📜 Свиток о {item_id}",
                description=info,
                color=discord.Color.dark_red()
            )
            embed.set_footer(text="Да пребудет с тобой страдание.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                f"❌ Свиток о `{item_id}` не найден в хранилище. Возможно, он ещё не освящён Митрополитом.",
                ephemeral=True
            )

    @app_commands.command(name="wiki_add", description="Добавить или обновить запись в свитках (только для служителей)")
    @app_commands.default_permissions(administrator=True)
    async def wiki_add(self, interaction: discord.Interaction, item_id: str, info: str):
        await add_wiki_entry(interaction.guild.id, item_id, info)
        await interaction.response.send_message(
            f"✅ Свиток `{item_id}` освящён и добавлен в хранилище.",
            ephemeral=True
        )

    @app_commands.command(name="wiki_remove", description="Удалить запись из свитков (только для служителей)")
    @app_commands.default_permissions(administrator=True)
    async def wiki_remove(self, interaction: discord.Interaction, item_id: str):
        await delete_wiki_entry(interaction.guild.id, item_id)
        await interaction.response.send_message(
            f"🗑️ Свиток `{item_id}` предан огню и удалён из хранилища.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Wiki(bot))