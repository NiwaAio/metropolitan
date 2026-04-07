import discord
from discord.ext import commands
from discord import app_commands
from database import set_guild_setting

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class VerifyButton(discord.ui.View):
        def __init__(self, role_id: int):
            super().__init__(timeout=None)
            self.role_id = role_id

        @discord.ui.button(label="Я человек", style=discord.ButtonStyle.success, custom_id="verify_button")
        async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
            role = interaction.guild.get_role(self.role_id)
            if role:
                if role not in interaction.user.roles:
                    await interaction.user.add_roles(role, reason="Верификация")
                    await interaction.response.send_message("Вы успешно верифицированы!", ephemeral=True)
                else:
                    await interaction.response.send_message("Вы уже верифицированы.", ephemeral=True)
            else:
                await interaction.response.send_message("Ошибка: роль не найдена. Обратитесь к администратору.", ephemeral=True)

    @app_commands.command(name="setup_verify", description="Настроить верификацию (создать сообщение с кнопкой)")
    @app_commands.default_permissions(administrator=True)
    async def setup_verify(self, interaction: discord.Interaction, role: discord.Role, channel: discord.TextChannel, message: str = "Нажмите кнопку ниже, чтобы получить доступ к серверу."):
        view = self.VerifyButton(role.id)
        await channel.send(message, view=view)
        await interaction.response.send_message(f"Сообщение верификации отправлено в {channel.mention} с ролью {role.mention}.", ephemeral=True)
        await set_guild_setting(interaction.guild.id, "verify_role_id", role.id)

    @app_commands.command(name="remove_verify", description="Удалить все сообщения верификации (требуется удалить вручную)")
    @app_commands.default_permissions(administrator=True)
    async def remove_verify(self, interaction: discord.Interaction):
        await interaction.response.send_message("Удалите сообщение с кнопкой вручную. Бот не может автоматически найти и удалить его.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Verification(bot))