import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io
import re
from PIL import Image
import pytesseract
import datetime
import pytz
from database import (
    get_attendance_settings,
    get_attendance_record_by_time,
    get_ign_by_user,
    get_all_ign_links,
    set_ign_link,
    delete_ign_link
)
import config

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

class PaginationView(discord.ui.View):
    def __init__(self, embeds, author_id, timeout=60):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current = 0
        self.author_id = author_id

    async def update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Эта кнопка не для вас.", ephemeral=True)
            return
        if self.current > 0:
            self.current -= 1
            await self.update(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Эта кнопка не для вас.", ephemeral=True)
            return
        if self.current < len(self.embeds) - 1:
            self.current += 1
            await self.update(interaction)

class OCRAttendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ign_link", description="Привязать игровой никнейм к пользователю")
    @app_commands.default_permissions(administrator=True)
    async def ign_link(self, interaction: discord.Interaction, user: discord.Member, ign: str):
        await set_ign_link(user.id, interaction.guild.id, ign)
        await interaction.response.send_message(f"✅ {user.mention} теперь связан с никнеймом `{ign}`.", ephemeral=True)

    @app_commands.command(name="ign_unlink", description="Удалить привязку игрового никнейма")
    @app_commands.default_permissions(administrator=True)
    async def ign_unlink(self, interaction: discord.Interaction, user: discord.Member):
        await delete_ign_link(user.id)
        await interaction.response.send_message(f"✅ Привязка для {user.mention} удалена.", ephemeral=True)

    @app_commands.command(name="ign_list", description="Показать список всех привязанных никнеймов")
    @app_commands.default_permissions(administrator=True)
    async def ign_list(self, interaction: discord.Interaction):
        links = await get_all_ign_links(interaction.guild.id)
        if not links:
            await interaction.response.send_message("Нет привязанных никнеймов.", ephemeral=True)
            return
        lines = [f"<@{uid}> → `{ign}`" for uid, ign in links.items()]
        pages = [lines[i:i+20] for i in range(0, len(lines), 20)]
        embeds = []
        for i, page in enumerate(pages, 1):
            embed = discord.Embed(title="📋 Список привязанных никнеймов", description="\n".join(page), color=discord.Color.blue())
            embed.set_footer(text=f"Страница {i}/{len(pages)}")
            embeds.append(embed)
        view = PaginationView(embeds, interaction.user.id)
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

    @app_commands.command(name="check_screenshot", description="Распознать никнеймы с изображения и сравнить с присутствием на этапе (2,4,6)")
    @app_commands.default_permissions(administrator=True)
    async def check_screenshot(self, interaction: discord.Interaction, stage: int, image: discord.Attachment):
        if stage not in [2, 4, 6]:
            await interaction.response.send_message("❌ Этап должен быть 2, 4 или 6.", ephemeral=True)
            return

        settings = await get_attendance_settings(interaction.guild.id)
        if not settings or not settings.get("times"):
            await interaction.response.send_message("❌ Сначала настройте мониторинг посещаемости (команды /attendance_...).", ephemeral=True)
            return
        times_list = settings["times"]
        if len(times_list) < stage:
            await interaction.response.send_message(f"❌ Этап {stage} не существует (доступно только {len(times_list)} времён).", ephemeral=True)
            return

        target_time = times_list[stage-1]
        now_moscow = datetime.datetime.now(MOSCOW_TZ)
        today_str = now_moscow.strftime("%Y-%m-%d")
        record = await get_attendance_record_by_time(interaction.guild.id, today_str, target_time)
        if not record:
            await interaction.response.send_message(f"❌ Нет данных о посещаемости на время {target_time} сегодня. Возможно, проверка ещё не проходила.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        img_data = await image.read()
        img = Image.open(io.BytesIO(img_data))
        text = pytesseract.image_to_string(img, lang='rus+eng')
        raw_words = re.findall(r'[A-Za-zА-Яа-я0-9_]+', text)
        recognized = list(set([w for w in raw_words if len(w) >= 3]))
        if not recognized:
            await interaction.followup.send("❌ Не удалось распознать ни одного никнейма на изображении.", ephemeral=True)
            return

        present_ids = record.get("present", [])
        absent_ids = record.get("absent", [])

        present_igns = set()
        absent_igns = set()
        for uid in present_ids:
            ign = await get_ign_by_user(uid)
            if ign:
                present_igns.add(ign)
        for uid in absent_ids:
            ign = await get_ign_by_user(uid)
            if ign:
                absent_igns.add(ign)

        recognized_set = set(recognized)

        in_both = recognized_set & present_igns
        only_in_screenshot = recognized_set - present_igns - absent_igns
        only_in_voice = present_igns - recognized_set
        not_in_any = (recognized_set - present_igns) & absent_igns

        embed = discord.Embed(title="📊 Сравнение списков (скриншот vs ГС)", color=discord.Color.gold())
        embed.add_field(name="🎮 Распознанные никнеймы", value=", ".join(recognized) if recognized else "Нет", inline=False)
        embed.add_field(name="✅ В ГС и на скрине", value=", ".join(in_both) if in_both else "Нет", inline=False)
        embed.add_field(name="📸 Только на скрине (не в ГС)", value=", ".join(only_in_screenshot) if only_in_screenshot else "Нет", inline=False)
        embed.add_field(name="🎤 Только в ГС (не на скрине)", value=", ".join(only_in_voice) if only_in_voice else "Нет", inline=False)
        embed.add_field(name="⚠️ На скрине, но отсутствуют в ГС (без уважительной причины)", value=", ".join(not_in_any) if not_in_any else "Нет", inline=False)
        embed.set_footer(text=f"Этап {stage} • Время {target_time}")

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(OCRAttendance(bot))