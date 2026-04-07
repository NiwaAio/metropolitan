import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import datetime
import pytz
from database import (
    get_raid_settings, set_raid_channel, set_raid_role,
    set_raid_days, set_raid_enabled, set_raid_postpone
)

MOSCOW_TZ = pytz.timezone('Europe/Moscow')
NOTIFY_TIMES = ["19:40", "19:45", "19:50", "19:55"]

class RaidNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduler_task = None

    async def cog_load(self):
        # Запускаем фоновую задачу при загрузке кога
        self.scheduler_task = asyncio.create_task(self.raid_scheduler())

    async def cog_unload(self):
        if self.scheduler_task:
            self.scheduler_task.cancel()

    async def raid_scheduler(self):
        """Каждую минуту проверяет, нужно ли отправлять уведомления"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now_moscow = datetime.datetime.now(MOSCOW_TZ)
            current_time_str = now_moscow.strftime("%H:%M")
            current_weekday = now_moscow.isoweekday()  # 1=пн, 7=вс

            if current_time_str in NOTIFY_TIMES:
                # Проходим по всем серверам, где есть настройки
                for guild in self.bot.guilds:
                    settings = await get_raid_settings(guild.id)
                    if not settings:
                        continue
                    # Проверяем, включено ли, не отложено ли, день недели
                    if not settings["enabled"]:
                        continue
                    if settings["postpone_until"] and now_moscow.timestamp() < settings["postpone_until"]:
                        continue
                    if settings["days"] and current_weekday not in map(int, settings["days"]):
                        continue
                    if not settings["channel_id"] or not settings["role_id"]:
                        continue
                    channel = guild.get_channel(settings["channel_id"])
                    role = guild.get_role(settings["role_id"])
                    if not channel or not role:
                        continue
                    # Отправляем 5 сообщений с задержкой 1 секунда
                    for _ in range(5):
                        await channel.send(f"{role.mention}, сбор на кв!")
                        await asyncio.sleep(1)
            # Ждём 60 секунд до следующей проверки
            await asyncio.sleep(60)

    # ---------- Команды настройки ----------
    @app_commands.command(name="raid_channel", description="Установить канал для уведомлений о сборе")
    @app_commands.default_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_raid_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"Канал уведомлений установлен: {channel.mention}", ephemeral=True)

    @app_commands.command(name="raid_role", description="Установить роль для пинга в уведомлениях")
    @app_commands.default_permissions(administrator=True)
    async def set_role(self, interaction: discord.Interaction, role: discord.Role):
        await set_raid_role(interaction.guild.id, role.id)
        await interaction.response.send_message(f"Роль для пинга: {role.mention}", ephemeral=True)

    @app_commands.command(name="raid_days", description="Установить дни недели для уведомлений (1=пн...7=вс)")
    @app_commands.default_permissions(administrator=True)
    async def set_days(self, interaction: discord.Interaction, days: str):
        """Пример: /raid_days 4,5,6 (чт,пт,сб)"""
        try:
            days_list = [int(d.strip()) for d in days.split(',') if 1 <= int(d.strip()) <= 7]
            if not days_list:
                raise ValueError
            await set_raid_days(interaction.guild.id, days_list)
            await interaction.response.send_message(f"Дни недели установлены: {', '.join(map(str, days_list))}", ephemeral=True)
        except:
            await interaction.response.send_message("Ошибка: введите номера дней через запятую (1-7)", ephemeral=True)

    @app_commands.command(name="raid_enable", description="Включить/отключить автоматические уведомления")
    @app_commands.default_permissions(administrator=True)
    async def set_enable(self, interaction: discord.Interaction, enabled: bool):
        await set_raid_enabled(interaction.guild.id, enabled)
        status = "включены" if enabled else "выключены"
        await interaction.response.send_message(f"Уведомления {status}.", ephemeral=True)

    @app_commands.command(name="raid_postpone", description="Отложить следующий сбор на 1 день")
    @app_commands.default_permissions(administrator=True)
    async def postpone(self, interaction: discord.Interaction):
        now = datetime.datetime.now(MOSCOW_TZ)
        until = now + datetime.timedelta(days=1)
        await set_raid_postpone(interaction.guild.id, until.timestamp())
        await interaction.response.send_message(f"Уведомления отложены до {until.strftime('%Y-%m-%d %H:%M')} МСК.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RaidNotify(bot))