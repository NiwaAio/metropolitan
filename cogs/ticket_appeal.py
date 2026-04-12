import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from utils import is_admin
from database import (
    create_appeal_ticket,
    get_appeal_ticket_by_user,
    get_appeal_ticket_by_channel,
    close_appeal_ticket,
    delete_appeal_ticket,
    clear_warnings
)
import config

class AppealTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📜 Создать свиток покаяния", style=discord.ButtonStyle.primary, custom_id="create_appeal")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild:
            return
        active = await get_appeal_ticket_by_user(interaction.guild.id, interaction.user.id)
        if active:
            channel = interaction.guild.get_channel(active["channel_id"])
            if channel:
                await interaction.response.send_message("❌ У тебя уже есть открытый свиток покаяния. Дождись решения Митрополита.", ephemeral=True)
                return
            else:
                await delete_appeal_ticket(active["channel_id"])

        category = interaction.guild.get_channel(config.APPEAL_CHANNEL_ID).category
        if not category:
            await interaction.response.send_message("❌ Место для покаяния не освящено. Обратись к Митрополиту.", ephemeral=True)
            return

        ticket_number = random.randint(1000, 9999)
        channel_name = f"покаяние-{ticket_number}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, manage_channels=True)
        }
        admin_role = discord.utils.get(interaction.guild.roles, name="Митрополит")  # или ID роли админов
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

        channel = await category.create_text_channel(name=channel_name, overwrites=overwrites)
        await create_appeal_ticket(interaction.guild.id, interaction.user.id, channel.id)

        embed = discord.Embed(
            title="📜 Свиток покаяния",
            description=(
                "**И прогневался Господь, увидев, как ты впал в ересь.**\n\n"
                "Ты был отлучён от братства за свои прегрешения. Если желаешь оспорить это решение, напиши своё оправдание в этом канале.\n"
                "**Митрополит или его слуги рассмотрят твою исповедь.**"
            ),
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="Господь видит истину. Не лги.")
        view = AdminActionView(interaction.user.id, interaction.guild.id)
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Свиток покаяния создан: {channel.mention}", ephemeral=True)

class AdminActionView(discord.ui.View):
    def __init__(self, user_id, guild_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.guild_id = guild_id
        self.resolved = False

    @discord.ui.button(label="✝️ Даровать прощение", style=discord.ButtonStyle.success, custom_id="forgive")
    async def forgive(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Только служители могут даровать прощение.", ephemeral=True)
            return
        if self.resolved:
            await interaction.response.send_message("❌ Решение уже принято.", ephemeral=True)
            return
        self.resolved = True
        member = interaction.guild.get_member(self.user_id)
        if member:
            excommunicated_role = interaction.guild.get_role(config.EXCOMMUNICATED_ROLE_ID)
            if excommunicated_role and excommunicated_role in member.roles:
                await member.remove_roles(excommunicated_role, reason="Прощение получено")
                await clear_warnings(self.user_id, self.guild_id)
                await interaction.channel.send(f"🙏 {member.mention} получил прощение и возвращён в братство.")
        await interaction.response.send_message("✅ Прощение даровано.", ephemeral=False)
        await self.close_ticket(interaction)

    @discord.ui.button(label="⛔ Отказать в прощении", style=discord.ButtonStyle.danger, custom_id="deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction):
            await interaction.response.send_message("❌ Только служители могут отказывать в прощении.", ephemeral=True)
            return
        if self.resolved:
            await interaction.response.send_message("❌ Решение уже принято.", ephemeral=True)
            return
        self.resolved = True
        member = interaction.guild.get_member(self.user_id)
        if member:
            await interaction.channel.send(f"⛔ {member.mention}, твоё покаяние не принято. Ты остаёшься отлучённым.")
        await interaction.response.send_message("❌ Прощение отказано.", ephemeral=False)
        await self.close_ticket(interaction)

    async def close_ticket(self, interaction: discord.Interaction):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await close_appeal_ticket(interaction.channel.id)
        embed = discord.Embed(
            title="🔒 Свиток запечатан",
            description="Решение вынесено. Канал будет предан огню служителем.",
            color=discord.Color.dark_red()
        )
        view = DeleteTicketView()
        await interaction.channel.send(embed=embed, view=view)

    def is_admin(self, interaction: discord.Interaction) -> bool:
        admin_role = discord.utils.get(interaction.guild.roles, name="Митрополит")
        return admin_role and admin_role in interaction.user.roles

class DeleteTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🗑️ Предать огню", style=discord.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        admin_role = discord.utils.get(interaction.guild.roles, name="Митрополит")
        if not (admin_role and admin_role in interaction.user.roles):
            await interaction.response.send_message("❌ Только служители могут уничтожать свитки.", ephemeral=True)
            return
        await interaction.response.send_message("🗑️ Свиток будет предан огню через 5 секунд...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketAppeal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="appeal_setup", description="Создать священное послание для покаяния")
    @app_commands.default_permissions(administrator=True)
    async def setup_appeal(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(config.APPEAL_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("❌ Канал для покаяния не указан в config.APPEAL_CHANNEL_ID", ephemeral=True)
            return
        embed = discord.Embed(
            title="📜 Покаяние",
            description=(
                "**Если тебя отлучили от братства и ты желаешь оспорить это решение, нажми на кнопку ниже.**\n"
                "Создай свиток покаяния и изложи свою исповедь. Митрополит рассмотрит твоё дело."
            ),
            color=discord.Color.dark_red()
        )
        view = AppealTicketView()
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Священное послание создано в {channel.mention}.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketAppeal(bot))