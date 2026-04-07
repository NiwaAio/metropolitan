<<<<<<< HEAD
import discord
from discord.ext import commands
from discord import app_commands
import random
import os

class Images(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    IMAGES_PATH = "assets/images/"

    @app_commands.command(name="meme", description="Случайный мем")
    async def meme(self, interaction: discord.Interaction):
        await self.send_random_image(interaction, "meme")

    async def send_random_image(self, interaction: discord.Interaction, folder: str):
        path = os.path.join(self.IMAGES_PATH, folder)
        if not os.path.exists(path):
            await interaction.response.send_message("Папка с картинками не найдена. Обратитесь к администратору.", ephemeral=True)
            return
        files = [f for f in os.listdir(path) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        if not files:
            await interaction.response.send_message("В этой категории пока нет картинок.", ephemeral=True)
            return
        chosen = random.choice(files)
        file = discord.File(os.path.join(path, chosen), filename=chosen)
        await interaction.response.send_message(file=file)

async def setup(bot):
=======
import discord
from discord.ext import commands
from discord import app_commands
import random
import os

class Images(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    IMAGES_PATH = "assets/images/"

    @app_commands.command(name="meme", description="Случайный мем")
    async def meme(self, interaction: discord.Interaction):
        await self.send_random_image(interaction, "meme")

    async def send_random_image(self, interaction: discord.Interaction, folder: str):
        path = os.path.join(self.IMAGES_PATH, folder)
        if not os.path.exists(path):
            await interaction.response.send_message("Папка с картинками не найдена. Обратитесь к администратору.", ephemeral=True)
            return
        files = [f for f in os.listdir(path) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        if not files:
            await interaction.response.send_message("В этой категории пока нет картинок.", ephemeral=True)
            return
        chosen = random.choice(files)
        file = discord.File(os.path.join(path, chosen), filename=chosen)
        await interaction.response.send_message(file=file)

async def setup(bot):
>>>>>>> f2b8f40a98b88a1f5d056b8ed5b856bfc8806334
    await bot.add_cog(Images(bot))