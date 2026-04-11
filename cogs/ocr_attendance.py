import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io
import re
import datetime
import pytz
import easyocr
import numpy as np
from PIL import Image, ImageEnhance
from database import (
    get_attendance_settings,
    get_attendance_record_by_time,
    get_ign_by_user,
    get_all_ign_links,
    set_ign_link,
    delete_ign_link
)
import warnings
warnings.filterwarnings("ignore", message="'pin_memory' argument is set as true")

# Инициализация EasyOCR
reader = easyocr.Reader(['ru', 'en'], gpu=False, verbose=False)

# Таблица замен для похожих букв (для нормализации)
SIMILAR_CHARS = {
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x', 'к': 'k', 'м': 'm', 'н': 'h',
    'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X'
}
REVERSE_SIMILAR = {v: k for k, v in SIMILAR_CHARS.items()}

def normalize_for_comparison(s: str) -> str:
    """Приводит строку к нижнему регистру и заменяет похожие буквы латиницей."""
    s = s.lower()
    # Заменяем кириллицу на латиницу, где возможно
    for cyr, lat in SIMILAR_CHARS.items():
        s = s.replace(cyr, lat)
    # Удаляем подчёркивания для сравнения (но сохраняем оригинал)
    s = s.replace('_', '')
    return s

def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        current = [i + 1]
        for j, cb in enumerate(b):
            insert = previous[j + 1] + 1
            delete = current[j] + 1
            replace = previous[j] + (ca != cb)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]

def find_best_match(word: str, known_dict: dict, threshold=3) -> tuple:
    """
    Ищет среди известных никнеймов (значения) наиболее похожий.
    Возвращает (лучший_никнейм, расстояние) или (None, None).
    known_dict: {user_id: nickname}
    """
    word_norm = normalize_for_comparison(word)
    best = None
    best_dist = 100
    for nick in known_dict.values():
        nick_norm = normalize_for_comparison(nick)
        dist = levenshtein(word_norm, nick_norm)
        if dist < best_dist:
            best_dist = dist
            best = nick
        # Если разница в длине больше threshold*2, можно пропустить? не будем.
    if best and best_dist <= threshold:
        return best, best_dist
    return None, None

def merge_split_parts(words: list, known_nicknames: set) -> set:
    """Пытается объединить соседние слова в известный никнейм."""
    merged = set()
    used = set()
    for i in range(len(words) - 1):
        combined = words[i] + '_' + words[i+1]
        if combined in known_nicknames:
            merged.add(combined)
            used.add(i)
            used.add(i+1)
        else:
            combined = words[i] + words[i+1]
            if combined in known_nicknames:
                merged.add(combined)
                used.add(i)
                used.add(i+1)
    # Добавляем неиспользованные слова
    for i, w in enumerate(words):
        if i not in used:
            merged.add(w)
    return merged

def preprocess_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'L':
        img = img.convert('L')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    # Увеличиваем размер
    new_size = (img.width * 2, img.height * 2)
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    return np.array(img, dtype=np.uint8)

class PaginationView(discord.ui.View):
    def __init__(self, embeds, author_id, timeout=60):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current = 0
        self.author_id = author_id
    async def update(self, interaction):
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction, button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Не ваша кнопка.", ephemeral=True)
            return
        if self.current > 0:
            self.current -= 1
            await self.update(interaction)
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next(self, interaction, button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Не ваша кнопка.", ephemeral=True)
            return
        if self.current < len(self.embeds) - 1:
            self.current += 1
            await self.update(interaction)

class OCRAttendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ign_link", description="Привязать игровой никнейм")
    @app_commands.default_permissions(administrator=True)
    async def ign_link(self, interaction, user: discord.Member, ign: str):
        if not re.fullmatch(r'^[\w]{3,32}$', ign):
            await interaction.response.send_message("❌ Никнейм только буквы/цифры/_, 3-32 символа.", ephemeral=True)
            return
        await set_ign_link(user.id, interaction.guild.id, ign)
        await interaction.response.send_message(f"✅ {user.mention} → `{ign}`", ephemeral=True)

    @app_commands.command(name="ign_unlink", description="Удалить привязку")
    @app_commands.default_permissions(administrator=True)
    async def ign_unlink(self, interaction, user: discord.Member):
        await delete_ign_link(user.id)
        await interaction.response.send_message(f"✅ Привязка {user.mention} удалена.", ephemeral=True)

    @app_commands.command(name="ign_list", description="Список привязанных никнеймов")
    @app_commands.default_permissions(administrator=True)
    async def ign_list(self, interaction):
        links = await get_all_ign_links(interaction.guild.id)
        if not links:
            await interaction.response.send_message("Нет привязок.", ephemeral=True)
            return
        lines = [f"<@{uid}> → `{ign}`" for uid, ign in links.items()]
        pages = [lines[i:i+20] for i in range(0, len(lines), 20)]
        embeds = []
        for i, page in enumerate(pages, 1):
            embed = discord.Embed(title="📋 Список привязанных никнеймов", description="\n".join(page), color=discord.Color.blue())
            embed.set_footer(text=f"Стр. {i}/{len(pages)}")
            embeds.append(embed)
        view = PaginationView(embeds, interaction.user.id)
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

    @app_commands.command(name="check_screenshot", description="Распознать и сравнить с этапом 2,4,6")
    @app_commands.default_permissions(administrator=True)
    async def check_screenshot(self, interaction, stage: int, image: discord.Attachment):
        if stage not in (2,4,6):
            await interaction.response.send_message("Этап 2,4 или 6.", ephemeral=True)
            return
        settings = await get_attendance_settings(interaction.guild.id)
        if not settings or not settings.get("times"):
            await interaction.response.send_message("Сначала /attendance_times и /attendance_enable", ephemeral=True)
            return
        times_list = settings["times"]
        if len(times_list) < stage:
            await interaction.response.send_message(f"Нет времени для этапа {stage}", ephemeral=True)
            return
        target_time = times_list[stage-1]
        now_moscow = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
        today_str = now_moscow.strftime("%Y-%m-%d")
        record = await get_attendance_record_by_time(interaction.guild.id, today_str, target_time)
        if not record:
            await interaction.response.send_message(f"Нет данных за {target_time} сегодня.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        # Получаем базу известных никнеймов
        all_links = await get_all_ign_links(interaction.guild.id)
        known_nicknames = set(all_links.values())

        # Распознавание
        img_bytes = await image.read()
        img_np = preprocess_image(img_bytes)
        result = reader.readtext(img_np, detail=0, paragraph=False)
        raw_text = '\n'.join(result)
        # Разбиваем на слова
        words = re.findall(r'[\w]+', raw_text)
        # Удаляем слишком короткие
        words = [w for w in words if len(w) >= 3]
        # Объединяем разбитые части
        merged_words = merge_split_parts(words, known_nicknames)
        # Коррекция через базу
        corrected = set()
        for w in merged_words:
            best, dist = find_best_match(w, all_links, threshold=2)  # порог 2
            if best:
                corrected.add(best)
            else:
                # Проверяем, не является ли w частью какого-то известного никнейма (с подчёркиванием)
                for nick in known_nicknames:
                    if w in nick.replace('_', '') and len(w) >= len(nick.replace('_', '')) * 0.7:
                        corrected.add(nick)
                        break
                else:
                    corrected.add(w)  # оставляем как есть

        recognized = list(corrected)
        if not recognized:
            await interaction.followup.send("Не распознано ни одного никнейма.", ephemeral=True)
            return

        # Данные из attendance
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
        only_screenshot = recognized_set - present_igns - absent_igns
        only_voice = present_igns - recognized_set
        absent_without_excuse = (recognized_set - present_igns) & absent_igns

        embed = discord.Embed(title="📊 Сравнение (скриншот vs ГС)", color=discord.Color.gold())
        embed.add_field(name="🎮 Распознанные никнеймы", value=", ".join(recognized) if recognized else "—", inline=False)
        embed.add_field(name="✅ В ГС и на скрине", value=", ".join(in_both) if in_both else "—", inline=False)
        embed.add_field(name="📸 Только на скрине (не в ГС)", value=", ".join(only_screenshot) if only_screenshot else "—", inline=False)
        embed.add_field(name="🎤 Только в ГС (не на скрине)", value=", ".join(only_voice) if only_voice else "—", inline=False)
        embed.add_field(name="⚠️ На скрине, но отсутствуют без уваж. причины", value=", ".join(absent_without_excuse) if absent_without_excuse else "—", inline=False)
        embed.set_footer(text=f"Этап {stage} • Время {target_time}")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(OCRAttendance(bot))