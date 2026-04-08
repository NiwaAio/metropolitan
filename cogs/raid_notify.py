import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import datetime
import pytz
from database import (
    get_raid_settings, set_raid_channel, set_raid_role,
    set_raid_days, set_raid_enabled, set_raid_postpone,
    set_raid_times, reset_raid_times, cancel_raid_postpone
)

MOSCOW_TZ = pytz.timezone('Europe/Moscow')
DEFAULT_TIMES = ["19:40", "19:45", "19:50", "19:55"]

class RaidNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_sent = {}

    async def cog_load(self):
        self.raid_loop.start()
        print("RaidNotify: цикл уведомлений запущен")

    def cog_unload(self):
        self.raid_loop.cancel()

    @tasks.loop(minutes=1)
    async def raid_loop(self):
        await self.bot.wait_until_ready()
        now_moscow = datetime.datetime.now(MOSCOW_TZ)
        current_time_str = now_moscow.strftime("%H:%M")
        current_weekday = now_moscow.isoweekday()

        for guild in self.bot.guilds:
            settings = await get_raid_settings(guild.id)
            if not settings or not settings["enabled"]:
                continue
            if settings["postpone_until"] and now_moscow.timestamp() < settings["postpone_until"]:
                continue
            if settings["days"] and current_weekday not in map(int, settings["days"]):
                continue
            if current_time_str not in settings["times"]:
                continue

            channel = guild.get_channel(settings["channel_id"])
            role = guild.get_role(settings["role_id"])
            if not channel or not role:
                continue

            last = self.last_sent.get(guild.id)
            if last == now_moscow.strftime("%Y-%m-%d %H:%M"):
                continue
            self.last_sent[guild.id] = now_moscow.strftime("%Y-%m-%d %H:%M")

            print(f"🔔 RaidNotify: отправка на сервер {guild.name} в {current_time_str}")
            for _ in range(5):
                await channel.send(f"{role.mention}, сбор на кв!")
                await asyncio.sleep(1)

    # ---------- Команды настройки ----------
    @app_commands.command(name="raid_channel", description="Установить канал для уведомлений")
    @app_commands.default_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_raid_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"📢 Канал: {channel.mention}", ephemeral=True)

    @app_commands.command(name="raid_role", description="Установить роль для пинга")
    @app_commands.default_permissions(administrator=True)
    async def set_role(self, interaction: discord.Interaction, role: discord.Role):
        await set_raid_role(interaction.guild.id, role.id)
        await interaction.response.send_message(f"👥 Роль: {role.mention}", ephemeral=True)

    @app_commands.command(name="raid_days", description="Установить дни недели (1=пн...7=вс) через запятую")
    @app_commands.default_permissions(administrator=True)
    async def set_days(self, interaction: discord.Interaction, days: str):
        try:
            days_list = [int(d.strip()) for d in days.split(',') if 1 <= int(d.strip()) <= 7]
            if not days_list:
                raise ValueError
            await set_raid_days(interaction.guild.id, days_list)
            await interaction.response.send_message(f"📅 Дни: {', '.join(map(str, days_list))}", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Ошибка: введите числа от 1 до 7 через запятую", ephemeral=True)

    @app_commands.command(name="raid_times", description="Установить время уведомлений (например: 19:40,19:45,19:50,19:55)")
    @app_commands.default_permissions(administrator=True)
    async def set_times(self, interaction: discord.Interaction, times: str):
        times_list = [t.strip() for t in times.split(',')]
        # Валидация формата HH:MM
        valid = True
        for t in times_list:
            if len(t) != 5 or t[2] != ':' or not t[:2].isdigit() or not t[3:].isdigit():
                valid = False
                break
            h, m = int(t[:2]), int(t[3:])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                valid = False
                break
        if not valid:
            await interaction.response.send_message("❌ Неверный формат времени. Используйте HH:MM через запятую, например: 19:40,19:45,19:50", ephemeral=True)
            return
        await set_raid_times(interaction.guild.id, times_list)
        await interaction.response.send_message(f"⏰ Время уведомлений: {', '.join(times_list)}", ephemeral=True)

    @app_commands.command(name="raid_reset_times", description="Сбросить время уведомлений на 19:40,19:45,19:50,19:55")
    @app_commands.default_permissions(administrator=True)
    async def reset_times(self, interaction: discord.Interaction):
        await reset_raid_times(interaction.guild.id)
        await interaction.response.send_message(f"⏰ Время уведомлений сброшено на стандартное: {', '.join(DEFAULT_TIMES)}", ephemeral=True)

    @app_commands.command(name="raid_enable", description="Включить/отключить уведомления")
    @app_commands.default_permissions(administrator=True)
    async def set_enable(self, interaction: discord.Interaction, enabled: bool):
        await set_raid_enabled(interaction.guild.id, enabled)
        status = "включены ✅" if enabled else "выключены ❌"
        await interaction.response.send_message(f"Уведомления {status}.", ephemeral=True)

    @app_commands.command(name="raid_postpone", description="Отложить следующий сбор на 1 день")
    @app_commands.default_permissions(administrator=True)
    async def postpone(self, interaction: discord.Interaction):
        now = datetime.datetime.now(MOSCOW_TZ)
        until = now + datetime.timedelta(days=1)
        await set_raid_postpone(interaction.guild.id, until.timestamp())
        await interaction.response.send_message(f"⏸️ Отложено до {until.strftime('%Y-%m-%d %H:%M')} МСК.", ephemeral=True)

    @app_commands.command(name="raid_cancel_postpone",
                          description="Отменить отложенный сбор")
    @app_commands.default_permissions(administrator=True)
    async def cancel_postpone(self, interaction: discord.Interaction):
        await cancel_raid_postpone(interaction.guild.id)
        await interaction.response.send_message("✅ Отложенный сбор отменён. Уведомления вернутся в обычный режим.", ephemeral=True)

    @app_commands.command(name="raid_settings", description="Показать текущие настройки")
    @app_commands.default_permissions(administrator=True)
    async def show_settings(self, interaction: discord.Interaction):
        settings = await get_raid_settings(interaction.guild.id)
        if not settings or not settings["channel_id"]:
            await interaction.response.send_message("❌ Настройки не заданы.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(settings["channel_id"])
        role = interaction.guild.get_role(settings["role_id"])
        days = settings["days"] if settings["days"] else []
        times = settings["times"] if settings["times"] else DEFAULT_TIMES
        enabled = "✅ Включено" if settings["enabled"] else "❌ Выключено"

        embed = discord.Embed(title="📋 Настройки уведомлений о сборе", color=discord.Color.blue())
        embed.add_field(name="Канал", value=channel.mention if channel else "❌ Не найден", inline=False)
        embed.add_field(name="Роль", value=role.mention if role else "❌ Не найдена", inline=False)
        embed.add_field(name="Дни недели", value=", ".join(map(str, days)) if days else "Все дни", inline=False)
        embed.add_field(name="Время", value=", ".join(times), inline=False)
        embed.add_field(name="Статус", value=enabled, inline=False)
        if settings["postpone_until"]:
            dt = datetime.datetime.fromtimestamp(settings["postpone_until"], tz=MOSCOW_TZ)
            embed.add_field(name="Отложено до", value=dt.strftime('%Y-%m-%d %H:%M МСК'), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="sync", description="Принудительная синхронизация слеш-команд (только администраторы)")
    @app_commands.default_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        synced = await self.bot.tree.sync()
        await interaction.followup.send(f"✅ Синхронизировано {len(synced)} команд.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RaidNotify(bot))