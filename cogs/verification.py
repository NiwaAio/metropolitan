import discord
from discord.ext import commands
from discord import app_commands
from database import get_guild_setting, set_guild_setting

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class VerifyButton(discord.ui.View):
        def __init__(self, role_id: int):
            super().__init__(timeout=None)
            self.role_id = role_id

        @discord.ui.button(label="Принять страдание", style=discord.ButtonStyle.success, custom_id="verify_button")
        async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
            role = interaction.guild.get_role(self.role_id)
            if role:
                if role not in interaction.user.roles:
                    await interaction.user.add_roles(role, reason="Верификация")
                    await interaction.response.send_message("Ты принял страдание. Отныне ты с нами.", ephemeral=True)
                else:
                    await interaction.response.send_message("Ты уже принял страдание.", ephemeral=True)
            else:
                await interaction.response.send_message("Сан не найден. Обратись к Митрополиту.", ephemeral=True)

    @app_commands.command(name="setup_verify", description="Настроить верификацию (создать сообщение с кнопкой)")
    @app_commands.default_permissions(administrator=True)
    async def setup_verify(self, interaction: discord.Interaction, role: discord.Role, channel: discord.TextChannel, message: str = "Нажми на кнопку ниже, чтобы принять страдание и получить доступ к святым приделам."):
        view = self.VerifyButton(role.id)
        embed = discord.Embed(
            title="🎭 Испытание верой",
            description=message,
            color=discord.Color.green()
        )
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Сообщение верификации создано в {channel.mention} с саном {role.mention}.", ephemeral=True)
        await set_guild_setting(interaction.guild.id, "verify_role_id", role.id)

    @app_commands.command(name="remove_verify", description="Удалить сообщение верификации")
    @app_commands.default_permissions(administrator=True)
    async def remove_verify(self, interaction: discord.Interaction):
        await interaction.response.send_message("Удали сообщение с кнопкой вручную. Служитель не может сам предать его огню.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Verification(bot))