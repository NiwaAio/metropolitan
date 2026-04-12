import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import re
from database import (
    get_ticket_config,
    set_ticket_config,
    create_reg_ticket,
    get_reg_ticket_by_user,
    get_reg_ticket_by_channel,
    delete_reg_ticket,
    set_ign_link,
    get_ign_by_user
)

class RegistrationTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📜 Создать свиток покаяния", style=discord.ButtonStyle.primary, custom_id="create_reg_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        active = await get_reg_ticket_by_user(interaction.guild.id, interaction.user.id)
        if active:
            channel = interaction.guild.get_channel(active["channel_id"])
            if channel:
                await interaction.response.send_message("❌ У тебя уже есть открытый свиток покаяния! Закрой его прежде, чем создавать новый.", ephemeral=True)
                return
            else:
                await delete_reg_ticket(active["channel_id"])

        ticket_config = await get_ticket_config(interaction.guild.id)
        if not ticket_config:
            await set_ticket_config(interaction.guild.id)
            ticket_config = await get_ticket_config(interaction.guild.id)

        category = None
        if ticket_config and ticket_config.get("category_id"):
            category = interaction.guild.get_channel(ticket_config["category_id"])
            if not category:
                await interaction.response.send_message("❌ Святая категория не найдена. Обратись к Митрополиту.", ephemeral=True)
                return

        ticket_number = random.randint(1000, 9999)
        channel_name = f"исповедь-{ticket_number}"

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, manage_channels=True)
        }
        if ticket_config.get("admin_role_id"):
            admin_role = interaction.guild.get_role(ticket_config["admin_role_id"])
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

        try:
            if category:
                channel = await category.create_text_channel(name=channel_name, overwrites=overwrites)
            else:
                channel = await interaction.guild.create_text_channel(name=channel_name, overwrites=overwrites)
        except Exception as e:
            await interaction.response.send_message(f"❌ Не удалось создать канал: {e}", ephemeral=True)
            return

        await create_reg_ticket(interaction.guild.id, interaction.user.id, channel.id)

        embed = discord.Embed(
            title="📜 Свиток покаяния",
            description=(
                "**И прогневался Господь, увидев, как человечество погрязло во грехе...**\n\n"
                "Если ты желаешь вступить в братство, заполни анкету:\n\n"
                "1. Напиши свой игровой никнейм (без ошибок! это важно).\n"
                "   **Никнейм может содержать только буквы и символ подчёркивания `_`. Цифры запрещены.**\n"
                "2. Количество часов в игре.\n"
                "3. Сколько КВ в неделю ты готов страдать.\n"
                "4. Возраст.\n"
                "5. Прикрепи скриншот со всем снаряжением, включая сборку.\n\n"
                "**После того как напишешь никнейм, нажми кнопку «Отправить никнейм».**\n"
                "Кнопка активна только один раз. Если ошибёшься, создай новый свиток."
            ),
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="Господь видит каждое твоё слово. Не лги.")
        view = TicketActionView(interaction.user.id)
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Свиток покаяния создан: {channel.mention}", ephemeral=True)

class TicketActionView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.used = False

    @discord.ui.button(label="✍️ Отправить никнейм", style=discord.ButtonStyle.success, custom_id="submit_nickname")
    async def submit_nickname(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Этот свиток не твой. Не прикасайся к чужой исповеди.", ephemeral=True)
            return

        if self.used:
            await interaction.response.send_message("❌ Кнопка уже была использована. Создай новый свиток, если хочешь изменить никнейм.", ephemeral=True)
            return

        self.used = True
        button.disabled = True
        await interaction.message.edit(view=self)

        existing = await get_ign_by_user(self.user_id)
        if existing:
            await interaction.response.send_message("❌ Твой никнейм уже привязан. Если хочешь сменить имя, обратись к niwaaio.", ephemeral=True)
            return

        async for msg in interaction.channel.history(limit=20):
            if msg.author.id == self.user_id and not msg.content.startswith('/') and msg.content.strip():
                raw = msg.content.strip()
                lines = [l.strip() for l in raw.split('\n') if l.strip()]
                if not lines:
                    continue
                first_line = lines[0]
                cleaned = re.sub(r'^\s*\d+[\.\)\-]\s*', '', first_line)
                cleaned = re.sub(r'[*`~]', '', cleaned)
                if not cleaned:
                    await interaction.response.send_message("❌ Не удалось распознать никнейм. Напиши его отдельной строкой без цифр в начале.", ephemeral=True)
                    return
                if re.search(r'\d', cleaned):
                    await interaction.response.send_message("❌ Никнейм не может содержать цифры. Напиши никнейм без цифр.", ephemeral=True)
                    return
                if not re.fullmatch(r'^[A-Za-zА-Яа-яёЁ_]+$', cleaned):
                    await interaction.response.send_message("❌ Никнейм может содержать только буквы и символ подчёркивания `_`. Исправь и нажми кнопку снова (кнопка активна один раз, создай новый свиток).", ephemeral=True)
                    return
                await set_ign_link(self.user_id, interaction.guild.id, cleaned)
                await interaction.response.send_message(f"✅ Господь принял твой никнейм: `{cleaned}`. Теперь жди решения Митрополита.", ephemeral=False)
                return
        await interaction.response.send_message("❌ Я не нашёл твоего сообщения с никнеймом. Напиши никнейм в чате (первой строкой, без нумерации) и нажми кнопку ещё раз (кнопка активна один раз, возможно, придётся создать новый свиток).", ephemeral=True)

    @discord.ui.button(label="🔒 Закрыть свиток", style=discord.ButtonStyle.danger, custom_id="close_ticket_admin")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_config = await get_ticket_config(interaction.guild.id)
        is_admin = False
        if ticket_config and ticket_config.get("admin_role_id"):
            admin_role = interaction.guild.get_role(ticket_config["admin_role_id"])
            if admin_role and admin_role in interaction.user.roles:
                is_admin = True
        if not is_admin and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Только Митрополит или его слуги могут закрыть этот свиток.", ephemeral=True)
            return

        ticket_data = await get_reg_ticket_by_channel(interaction.channel.id)
        if not ticket_data:
            await interaction.response.send_message("❌ Этот свиток уже закрыт.", ephemeral=True)
            return

        await delete_reg_ticket(interaction.channel.id)
        overwrites = interaction.channel.overwrites
        for target, perms in overwrites.items():
            if isinstance(target, discord.Member) and target.id == ticket_data["user_id"]:
                perms.send_messages = False
                break
        await interaction.channel.edit(overwrites=overwrites)

        embed = discord.Embed(
            title="🔒 Свиток запечатан",
            description="Исповедь принята. Канал будет предан огню служителем.",
            color=discord.Color.dark_red()
        )
        view = DeleteTicketView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Свиток закрыт.", ephemeral=False)

class DeleteTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🗑️ Уничтожить свиток", style=discord.ButtonStyle.danger, custom_id="delete_ticket_admin")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_config = await get_ticket_config(interaction.guild.id)
        is_admin = False
        if ticket_config and ticket_config.get("admin_role_id"):
            admin_role = interaction.guild.get_role(ticket_config["admin_role_id"])
            if admin_role and admin_role in interaction.user.roles:
                is_admin = True
        if not is_admin and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Только служители могут уничтожать свитки.", ephemeral=True)
            return
        await interaction.response.send_message("🗑️ Свиток будет предан огню через 5 секунд...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketRegistration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reg_setup", description="Создать священное послание с кнопкой для создания свитков")
    @app_commands.default_permissions(administrator=True)
    async def setup_message(self, interaction: discord.Interaction, channel: discord.TextChannel):
        embed = discord.Embed(
            title="📜 Откровение",
            description=(
                "**И прогневался Господь, увидев, как человечество погрязло во грехе...**\n\n"
                "Если ты желаешь вступить в братство и разделить страдание, нажми на кнопку ниже и создай свиток покаяния.\n"
                "Господь видит каждого. Не лги."
            ),
            color=discord.Color.dark_red()
        )
        view = RegistrationTicketView()
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Священное послание создано в {channel.mention}.", ephemeral=True)

    @app_commands.command(name="reg_stats", description="Показать количество принятых душ")
    @app_commands.default_permissions(administrator=True)
    async def reg_stats(self, interaction: discord.Interaction):
        from database import get_all_ign_links
        links = await get_all_ign_links(interaction.guild.id)
        await interaction.response.send_message(f"📊 В братство вписано душ: {len(links)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketRegistration(bot))