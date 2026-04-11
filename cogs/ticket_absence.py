import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import re
import datetime
import pytz
from database import (
    get_ticket_config, set_ticket_config,
    create_active_ticket, get_active_ticket_by_user, get_active_ticket_by_channel, delete_active_ticket,
    add_excused_absence, get_excused_absences, delete_excused_absence, delete_excused_absences_by_user
)

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📜 Создать свиток покаяния", style=discord.ButtonStyle.primary, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        active = await get_active_ticket_by_user(interaction.guild.id, interaction.user.id)
        if active:
            await interaction.response.send_message("❌ У тебя уже есть открытый свиток покаяния! Запечатай его прежде, чем создавать новый.", ephemeral=True)
            return
        config = await get_ticket_config(interaction.guild.id)
        if not config or not config["category_id"]:
            await interaction.response.send_message("❌ Место для свитков не освящено. Обратись к Митрополиту.", ephemeral=True)
            return
        category = interaction.guild.get_channel(config["category_id"])
        if not category:
            await interaction.response.send_message("❌ Святая категория не найдена.", ephemeral=True)
            return
        ticket_number = random.randint(1000, 9999)
        channel_name = f"исповедь-{ticket_number}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, manage_channels=True)
        }
        if config["admin_role_id"]:
            admin_role = interaction.guild.get_role(config["admin_role_id"])
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
        try:
            channel = await category.create_text_channel(name=channel_name, overwrites=overwrites)
        except Exception as e:
            await interaction.response.send_message(f"❌ Не удалось создать канал: {e}", ephemeral=True)
            return
        await create_active_ticket(interaction.guild.id, interaction.user.id, channel.id)
        embed = discord.Embed(
            title="📜 Свиток покаяния",
            description=(
                "**И прогневался Господь, увидев, как человечество погрязло во грехе...**\n\n"
                "Если ты желаешь оправдать своё отсутствие на Зове, напиши причину.\n\n"
                "**Инструкция:**\n"
                "• Если ты хочешь оправдать отсутствие **только на сегодня**, просто напиши причину одним сообщением.\n"
                "• Если ты хочешь оправдать отсутствие **на конкретную дату**, начни сообщение с даты в формате `ДД.ММ.ГГГГ` (например, `02.07.2026`).\n"
                "• Если ты хочешь оправдать отсутствие **на диапазон дат**, используй формат `ДД.ММ.ГГГГ-ДД.ММ.ГГГГ` (например, `02.07.2026-06.07.2026`).\n"
                "• Максимальный срок отсрочки — **7 дней**. Если нужно больше — обратись к **Митрополиту**.\n\n"
                "После отправки сообщения свиток запечатается, и ты будешь отмечен как отсутствующий по уважительной причине на указанные даты."
            ),
            color=discord.Color.dark_red()
        )
        view = CloseTicketView()
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Свиток покаяния создан: {channel.mention}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Запечатать свиток", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_data = await get_active_ticket_by_channel(interaction.channel.id)
        if not ticket_data:
            await interaction.response.send_message("❌ Этот свиток уже запечатан.", ephemeral=True)
            return
        config = await get_ticket_config(interaction.guild.id)
        is_admin = False
        if config and config["admin_role_id"]:
            admin_role = interaction.guild.get_role(config["admin_role_id"])
            if admin_role and admin_role in interaction.user.roles:
                is_admin = True
        if interaction.user.id != ticket_data["user_id"] and not is_admin:
            await interaction.response.send_message("❌ Ты не можешь запечатать этот свиток.", ephemeral=True)
            return
        await delete_active_ticket(interaction.channel.id)
        await interaction.response.send_message("🔒 Свиток запечатан. Теперь только служители могут писать здесь.", ephemeral=False)
        overwrites = interaction.channel.overwrites
        for target, perms in overwrites.items():
            if isinstance(target, discord.Member) and target.id == ticket_data["user_id"]:
                perms.send_messages = False
                perms.read_messages = True
                break
        await interaction.channel.edit(overwrites=overwrites)
        view = DeleteTicketView()
        await interaction.channel.send("🛠️ Свиток запечатан. Нажми кнопку ниже, чтобы предать его огню.", view=view)

class DeleteTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🗑️ Предать огню", style=discord.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = await get_ticket_config(interaction.guild.id)
        is_admin = False
        if config and config["admin_role_id"]:
            admin_role = interaction.guild.get_role(config["admin_role_id"])
            if admin_role and admin_role in interaction.user.roles:
                is_admin = True
        if not is_admin:
            await interaction.response.send_message("❌ Только служители могут предавать свитки огню.", ephemeral=True)
            return
        await interaction.response.send_message("🗑️ Свиток будет предан огню через 5 секунд...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketAbsence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket_setup_channel", description="Установить канал, где будет кнопка создания свитков")
    @app_commands.default_permissions(administrator=True)
    async def setup_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_ticket_config(interaction.guild.id, channel_id=channel.id)
        await interaction.response.send_message(f"✅ Канал для кнопки свитков: {channel.mention}", ephemeral=True)

    @app_commands.command(name="ticket_setup_category", description="Установить категорию для создания каналов свитков")
    @app_commands.default_permissions(administrator=True)
    async def setup_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        await set_ticket_config(interaction.guild.id, category_id=category.id)
        await interaction.response.send_message(f"✅ Категория для свитков: {category.name}", ephemeral=True)

    @app_commands.command(name="ticket_admin_role", description="Установить роль служителя, который может управлять свитками")
    @app_commands.default_permissions(administrator=True)
    async def setup_admin_role(self, interaction: discord.Interaction, role: discord.Role):
        await set_ticket_config(interaction.guild.id, admin_role_id=role.id)
        await interaction.response.send_message(f"✅ Роль служителя свитков: {role.mention}", ephemeral=True)

    @app_commands.command(name="ticket_create_message", description="Создать сообщение с кнопкой создания свитка")
    @app_commands.default_permissions(administrator=True)
    async def create_message(self, interaction: discord.Interaction):
        config = await get_ticket_config(interaction.guild.id)
        if not config or not config["channel_id"]:
            await interaction.response.send_message("❌ Сначала настройте канал командой `/ticket_setup_channel`", ephemeral=True)
            return
        channel = interaction.guild.get_channel(config["channel_id"])
        if not channel:
            await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
            return
        embed = discord.Embed(
            title="📜 Откровение",
            description="**И прогневался Господь, увидев, как человечество погрязло во грехе...**\n\nЕсли ты желаешь оправдать своё отсутствие на Зове, нажми на кнопку ниже и создай свиток покаяния.\nГосподь видит каждого. Не лги.",
            color=discord.Color.dark_red()
        )
        view = TicketView()
        message = await channel.send(embed=embed, view=view)
        await set_ticket_config(interaction.guild.id, message_id=message.id)
        await interaction.response.send_message("✅ Священное послание создано!", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        ticket_data = await get_active_ticket_by_channel(message.channel.id)
        if not ticket_data:
            return
        config = await get_ticket_config(message.guild.id)
        is_admin = False
        if config and config["admin_role_id"]:
            admin_role = message.guild.get_role(config["admin_role_id"])
            if admin_role and admin_role in message.author.roles:
                is_admin = True
        if message.author.id == ticket_data["user_id"] and not is_admin:
            content = message.content.strip()
            date_pattern = r'^(\d{2}\.\d{2}\.\d{4})(?:-(\d{2}\.\d{2}\.\d{4}))?'
            match = re.match(date_pattern, content)
            today = datetime.datetime.now(MOSCOW_TZ).strftime("%Y-%m-%d")
            start_date = today
            end_date = today
            reason = content
            if match:
                start_str = match.group(1)
                end_str = match.group(2) if match.group(2) else start_str
                start_date = datetime.datetime.strptime(start_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                end_date = datetime.datetime.strptime(end_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                reason = content[match.end():].strip()
                if not reason:
                    reason = "Не указана"
            else:
                start_date = today
                end_date = today
                reason = content
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            delta = (end_dt - start_dt).days
            if delta > 7:
                await message.channel.send("❌ Максимальный срок отсрочки — 7 дней. Если нужно больше, обратись к Митрополиту.")
                return
            await add_excused_absence(message.guild.id, message.author.id, start_date, end_date, reason, message.author.id, message.channel.id)
            await delete_active_ticket(message.channel.id)
            overwrites = message.channel.overwrites
            for target, perms in overwrites.items():
                if isinstance(target, discord.Member) and target.id == ticket_data["user_id"]:
                    perms.send_messages = False
                    break
            await message.channel.edit(overwrites=overwrites)
            embed = discord.Embed(
                title="✅ Свиток запечатан",
                description=f"Твоё оправдание принято на период с {start_date} по {end_date}.\nПричина: {reason}",
                color=discord.Color.green()
            )
            view = DeleteTicketView()
            await message.channel.send(embed=embed, view=view)
            await message.delete()

    @app_commands.command(name="excused_list", description="Показать список душ, отсутствующих по уважительной причине")
    @app_commands.default_permissions(administrator=True)
    async def excused_list(self, interaction: discord.Interaction):
        absences = await get_excused_absences(interaction.guild.id)
        if not absences:
            await interaction.response.send_message("Нет оправданных отсутствий.", ephemeral=True)
            return
        users_absences = {}
        for a in absences:
            user_id = a["user_id"]
            if user_id not in users_absences:
                users_absences[user_id] = []
            users_absences[user_id].append(a)
        pages = []
        current_page = ""
        for user_id, abs_list in users_absences.items():
            user = interaction.guild.get_member(user_id)
            user_name = user.mention if user else f"<@{user_id}>"
            block = f"**{user_name}**\n"
            for a in abs_list:
                block += f"  • {a['start_date']} — {a['end_date']}: {a['reason']}\n"
            if len(current_page) + len(block) > 1800:
                pages.append(current_page)
                current_page = block
            else:
                current_page += block
        if current_page:
            pages.append(current_page)
        await self.paginate(interaction, pages)

    async def paginate(self, interaction: discord.Interaction, pages: list):
        if not pages:
            await interaction.response.send_message("Нет данных.", ephemeral=True)
            return
        current = 0
        embed = discord.Embed(title="📋 Оправданные души", description=pages[0], color=discord.Color.blue())
        embed.set_footer(text=f"Страница {current+1}/{len(pages)}")
        view = PaginationView(pages, current, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="excused_add", description="Добавить душу в список оправданных отсутствий (служитель)")
    @app_commands.default_permissions(administrator=True)
    async def excused_add(self, interaction: discord.Interaction, user: discord.Member, start_date: str, end_date: str = None, reason: str = "По решению Митрополита"):
        try:
            start_dt = datetime.datetime.strptime(start_date, "%d.%m.%Y")
            end_dt = datetime.datetime.strptime(end_date, "%d.%m.%Y") if end_date else start_dt
            if (end_dt - start_dt).days > 7:
                await interaction.response.send_message("❌ Максимальный срок — 7 дней.", ephemeral=True)
                return
            start_str = start_dt.strftime("%Y-%m-%d")
            end_str = end_dt.strftime("%Y-%m-%d")
        except:
            await interaction.response.send_message("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ", ephemeral=True)
            return
        await add_excused_absence(interaction.guild.id, user.id, start_str, end_str, reason, interaction.user.id, None)
        await interaction.response.send_message(f"✅ {user.mention} добавлен в список оправданных душ с {start_str} по {end_str}. Причина: {reason}", ephemeral=True)

    @app_commands.command(name="excused_remove", description="Удалить душу из списка оправданных отсутствий (служитель)")
    @app_commands.default_permissions(administrator=True)
    async def excused_remove(self, interaction: discord.Interaction, user: discord.Member, date: str = None):
        if date:
            try:
                date_dt = datetime.datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")
            except:
                await interaction.response.send_message("❌ Неверный формат даты.", ephemeral=True)
                return
            await delete_excused_absences_by_user(interaction.guild.id, user.id, date_dt)
            await interaction.response.send_message(f"✅ Удалены оправдания для {user.mention} на дату {date}.", ephemeral=True)
        else:
            await delete_excused_absences_by_user(interaction.guild.id, user.id)
            await interaction.response.send_message(f"✅ Удалены все оправдания для {user.mention}.", ephemeral=True)

class PaginationView(discord.ui.View):
    def __init__(self, pages, current, author_id):
        super().__init__(timeout=60)
        self.pages = pages
        self.current = current
        self.author_id = author_id

    async def update(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📋 Оправданные души", description=self.pages[self.current], color=discord.Color.blue())
        embed.set_footer(text=f"Страница {self.current+1}/{len(self.pages)}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Эта кнопка не для тебя.", ephemeral=True)
            return
        if self.current > 0:
            self.current -= 1
            await self.update(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Эта кнопка не для тебя.", ephemeral=True)
            return
        if self.current < len(self.pages) - 1:
            self.current += 1
            await self.update(interaction)

async def setup(bot):
    await bot.add_cog(TicketAbsence(bot))