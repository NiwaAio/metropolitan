import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import asyncio
import pytz
from database import (
    get_attendance_settings,
    set_attendance_enabled,
    set_attendance_voice_channel,
    set_attendance_role,
    set_attendance_report_channel,
    set_attendance_times,
    save_attendance_record,
    get_last_attendance_record,
    get_excused_absences
)

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

class Attendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.checking_today = set()

    async def cog_load(self):
        self.attendance_loop.start()
        print("✅ Attendance: цикл проверки запущен")

    def cog_unload(self):
        self.attendance_loop.cancel()

    @tasks.loop(minutes=1)
    async def attendance_loop(self):
        await self.bot.wait_until_ready()
        now_moscow = datetime.datetime.now(MOSCOW_TZ)
        current_time_str = now_moscow.strftime("%H:%M")
        today_str = now_moscow.strftime("%Y-%m-%d")

        for guild in self.bot.guilds:
            settings = await get_attendance_settings(guild.id)
            if not settings or not settings.get("enabled"):
                continue
            times_list = settings.get("times", [])
            if not times_list or current_time_str not in times_list:
                continue

            key = (guild.id, today_str, current_time_str)
            if key in self.checking_today:
                continue
            self.checking_today.add(key)

            voice_channel = guild.get_channel(settings["voice_channel_id"])
            report_channel = guild.get_channel(settings["report_channel_id"])
            role = guild.get_role(settings["role_id"])
            if not voice_channel or not report_channel or not role:
                print(f"⚠️ Attendance: на сервере {guild.name} не настроены каналы или роль")
                continue

            try:
                idx = times_list.index(current_time_str)
                if idx < 2:
                    stage = 1
                elif idx < 4:
                    stage = 2
                else:
                    stage = 3
            except ValueError:
                continue

            members_with_role = [m for m in guild.members if role in m.roles]
            present = []
            for member in members_with_role:
                if member.voice and member.voice.channel == voice_channel:
                    present.append(member.id)
            absent = [m.id for m in members_with_role if m.id not in present]

            await save_attendance_record(guild.id, today_str, current_time_str, stage, present, absent)

            last_record = await get_last_attendance_record(guild.id, today_str)

            excused_users = set()
            for uid in absent:
                excuses = await get_excused_absences(guild.id, user_id=uid, date=today_str)
                if excuses:
                    excused_users.add(uid)

            late_users = set()
            if last_record:
                prev_present_set = set(last_record.get("present", []))
                for uid in present:
                    if uid not in prev_present_set:
                        excuses = await get_excused_absences(guild.id, user_id=uid, date=today_str)
                        if not excuses:
                            late_users.add(uid)

            present_mentions = []
            for uid in present:
                mention = f"<@{uid}>"
                if uid in late_users:
                    mention += " (О)"
                present_mentions.append(mention)

            absent_mentions = []
            for uid in absent:
                mention = f"<@{uid}>"
                if uid in excused_users:
                    mention += " (У)"
                absent_mentions.append(mention)

            changes_text = ""
            if last_record:
                prev_present_set = set(last_record.get("present", []))
                prev_absent_set = set(last_record.get("absent", []))
                new_present_set = set(present)
                new_absent_set = set(absent)
                appeared = new_present_set - prev_present_set
                disappeared = prev_present_set - new_present_set
                if appeared:
                    changes_text += f"➕ Обрели благодать: {', '.join(f'<@{uid}>' for uid in appeared)}\n"
                if disappeared:
                    changes_text += f"➖ Отвергнуты: {', '.join(f'<@{uid}>' for uid in disappeared)}\n"
                if late_users:
                    changes_text += f"⏰ Преткнулись: {', '.join(f'<@{uid}>' for uid in late_users)}\n"

            embed = discord.Embed(
                title=f"📜 Книга страданий — этап {stage}/3",
                description=f"Час страданий: {current_time_str} МСК\nСан: {role.mention}\nПридел: {voice_channel.mention}",
                color=discord.Color.blue()
            )
            embed.add_field(name="✅ В Зоне", value=", ".join(present_mentions) if present_mentions else "Никого", inline=False)
            embed.add_field(name="❌ Вне Зоны", value=", ".join(absent_mentions) if absent_mentions else "Все в страдании", inline=False)
            if changes_text:
                embed.add_field(name="🔄 Изменения с прошлой проповеди", value=changes_text, inline=False)
            embed.set_footer(text=f"Печать братства: {guild.id}")

            await report_channel.send(embed=embed)
            print(f"📢 Attendance: отчёт отправлен для {guild.name}, этап {stage}")

            await asyncio.sleep(1)

    @app_commands.command(name="attendance_enable", description="Включить/выключить мониторинг посещаемости")
    @app_commands.default_permissions(administrator=True)
    async def set_enable(self, interaction: discord.Interaction, enabled: bool):
        await set_attendance_enabled(interaction.guild.id, enabled)
        status = "включён ✅" if enabled else "выключен ❌"
        await interaction.response.send_message(f"Мониторинг посещаемости {status}.", ephemeral=True)

    @app_commands.command(name="attendance_voice", description="Установить голосовой канал для проверки")
    @app_commands.default_permissions(administrator=True)
    async def set_voice(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        await set_attendance_voice_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"🎙️ Голосовой канал: {channel.mention}", ephemeral=True)

    @app_commands.command(name="attendance_role", description="Установить роль, которая проверяется")
    @app_commands.default_permissions(administrator=True)
    async def set_role(self, interaction: discord.Interaction, role: discord.Role):
        await set_attendance_role(interaction.guild.id, role.id)
        await interaction.response.send_message(f"👥 Роль для проверки: {role.mention}", ephemeral=True)

    @app_commands.command(name="attendance_report", description="Установить канал для отчётов")
    @app_commands.default_permissions(administrator=True)
    async def set_report(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_attendance_report_channel(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"📄 Канал отчётов: {channel.mention}", ephemeral=True)

    @app_commands.command(name="attendance_times", description="Установить 6 времён проверки (ЧЧ:ММ через запятую)")
    @app_commands.default_permissions(administrator=True)
    async def set_times(self, interaction: discord.Interaction, times: str):
        times_list = [t.strip() for t in times.split(',')]
        if len(times_list) != 6:
            await interaction.response.send_message("❌ Нужно указать ровно 6 времён через запятую, например: 20:00,20:30,21:00,21:30,22:00,22:10", ephemeral=True)
            return
        for t in times_list:
            if len(t) != 5 or t[2] != ':' or not t[:2].isdigit() or not t[3:].isdigit():
                await interaction.response.send_message(f"❌ Неверный формат: {t}. Используйте ЧЧ:ММ", ephemeral=True)
                return
            h, m = int(t[:2]), int(t[3:])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                await interaction.response.send_message(f"❌ Неверное время: {t}", ephemeral=True)
                return
        await set_attendance_times(interaction.guild.id, times_list)
        stage1 = ", ".join(times_list[0:2])
        stage2 = ", ".join(times_list[2:4])
        stage3 = ", ".join(times_list[4:6])
        await interaction.response.send_message(f"⏰ Времена проверок:\n**1 этап:** {stage1}\n**2 этап:** {stage2}\n**3 этап:** {stage3}", ephemeral=True)

    @app_commands.command(name="attendance_settings", description="Показать текущие настройки мониторинга")
    @app_commands.default_permissions(administrator=True)
    async def show_settings(self, interaction: discord.Interaction):
        settings = await get_attendance_settings(interaction.guild.id)
        if not settings or not settings.get("voice_channel_id"):
            await interaction.response.send_message("❌ Настройки не заданы. Используйте `/attendance_voice`, `/attendance_role`, `/attendance_report`, `/attendance_times`, затем `/attendance_enable true`.", ephemeral=True)
            return
        voice_channel = interaction.guild.get_channel(settings["voice_channel_id"])
        report_channel = interaction.guild.get_channel(settings["report_channel_id"])
        role = interaction.guild.get_role(settings["role_id"])
        enabled = "✅ Включено" if settings.get("enabled") else "❌ Выключено"
        times = settings.get("times", [])
        times_str = ", ".join(times) if times else "Не заданы"

        embed = discord.Embed(title="📋 Настройки мониторинга посещаемости", color=discord.Color.green())
        embed.add_field(name="Статус", value=enabled, inline=False)
        embed.add_field(name="Голосовой канал", value=voice_channel.mention if voice_channel else "❌ Не найден", inline=False)
        embed.add_field(name="Роль", value=role.mention if role else "❌ Не найдена", inline=False)
        embed.add_field(name="Канал отчётов", value=report_channel.mention if report_channel else "❌ Не найден", inline=False)
        embed.add_field(name="Времена проверок (6)", value=times_str, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="attendance_test", description="Ручной запуск проверки (без сохранения в историю)")
    @app_commands.default_permissions(administrator=True)
    async def test_check(self, interaction: discord.Interaction):
        settings = await get_attendance_settings(interaction.guild.id)
        if not settings or not settings.get("voice_channel_id"):
            await interaction.response.send_message("❌ Настройки не заданы.", ephemeral=True)
            return
        voice_channel = interaction.guild.get_channel(settings["voice_channel_id"])
        report_channel = interaction.guild.get_channel(settings["report_channel_id"])
        role = interaction.guild.get_role(settings["role_id"])
        if not voice_channel or not report_channel or not role:
            await interaction.response.send_message("❌ Канал или роль не найдены. Проверьте настройки.", ephemeral=True)
            return

        members_with_role = [m for m in interaction.guild.members if role in m.roles]
        present = []
        for member in members_with_role:
            if member.voice and member.voice.channel == voice_channel:
                present.append(member.id)
        absent = [m.id for m in members_with_role if m.id not in present]

        present_mentions = [f"<@{uid}>" for uid in present]
        absent_mentions = [f"<@{uid}>" for uid in absent]

        embed = discord.Embed(title="🧪 Испытание веры", color=discord.Color.gold())
        embed.add_field(name="✅ В Зоне", value=", ".join(present_mentions) if present_mentions else "Никого", inline=False)
        embed.add_field(name="❌ Вне Зоны", value=", ".join(absent_mentions) if absent_mentions else "Все в страдании", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot):
    await bot.add_cog(Attendance(bot))