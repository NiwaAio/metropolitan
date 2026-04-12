import discord
import json
from discord.ext import commands
from discord import app_commands
import datetime
import gspread
from google.oauth2.service_account import Credentials
from database import (
    get_attendance_settings,
    get_attendance_record_by_time,
    get_excused_absences,
    get_all_ign_links,
    get_ign_by_user,
)
import config
import pytz
import re

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

def _column_letter(col: int) -> str:
    result = ""
    while col > 0:
        col -= 1
        result = chr(65 + col % 26) + result
        col //= 26
    return result

class ReportGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gc = None
        self.init_google_sheets()

    def init_google_sheets(self):
        try:
            if config.GOOGLE_CREDENTIALS_JSON:
                creds_dict = json.loads(config.GOOGLE_CREDENTIALS_JSON)
                creds = Credentials.from_service_account_info(
                    creds_dict,
                    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                )
            else:
                creds = Credentials.from_service_account_file(
                    config.GOOGLE_CREDENTIALS_FILE,
                    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                )
            self.gc = gspread.authorize(creds)
            print("✅ Google Sheets клиент инициализирован")
        except Exception as e:
            print(f"❌ Ошибка инициализации Google Sheets: {e}")

    @app_commands.command(name="generate_report", description="Создать отчёт по посещаемости в Google Sheets")
    @app_commands.default_permissions(administrator=True)
    async def generate_report(self, interaction: discord.Interaction, month: int, year: int):
        if not self.gc:
            await interaction.response.send_message("❌ Google Sheets не настроен.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            current += datetime.timedelta(days=1)

        settings = await get_attendance_settings(interaction.guild.id)
        if not settings or not settings.get("times"):
            await interaction.followup.send("❌ Настройки посещаемости не заданы.", ephemeral=True)
            return
        times_list = settings["times"]
        if len(times_list) != 6:
            await interaction.followup.send("❌ Должно быть 6 времён проверки.", ephemeral=True)
            return

        main_role_id = settings["role_id"]
        main_role = interaction.guild.get_role(main_role_id)
        if not main_role:
            await interaction.followup.send("❌ Роль не найдена.", ephemeral=True)
            return

        backup_role = discord.utils.get(interaction.guild.roles, name="Запасные")

        linked_users = await get_all_ign_links(interaction.guild.id)
        all_user_ids = set()
        for m in interaction.guild.members:
            if main_role in m.roles:
                all_user_ids.add(m.id)
        all_user_ids.update(linked_users.keys())

        participants = []
        for uid in all_user_ids:
            member = interaction.guild.get_member(uid)
            if not member:
                continue
            ign = linked_users.get(uid) or await get_ign_by_user(uid) or member.display_name
            has_main_role = main_role in member.roles
            is_backup = backup_role and backup_role in member.roles
            participants.append({
                "user_id": uid,
                "ign": ign,
                "member": member,
                "has_main_role": has_main_role,
                "is_backup": is_backup
            })
        participants.sort(key=lambda x: (x["is_backup"], x["ign"].lower()))

        records_by_date = {}
        for dt in dates:
            date_str = dt.strftime("%Y-%m-%d")
            records = []
            for i, time_str in enumerate(times_list):
                rec = await get_attendance_record_by_time(interaction.guild.id, date_str, time_str)
                if rec:
                    rec["stage"] = (i // 2) + 1
                    rec["time"] = time_str
                    records.append(rec)
            records_by_date[date_str] = records

        excused_absences = await get_excused_absences(interaction.guild.id)
        excused_map = {}
        for exc in excused_absences:
            start = datetime.datetime.strptime(exc["start_date"], "%Y-%m-%d").date()
            end = datetime.datetime.strptime(exc["end_date"], "%Y-%m-%d").date()
            cur = start
            while cur <= end:
                date_str = cur.strftime("%Y-%m-%d")
                excused_map.setdefault(exc["user_id"], set()).add(date_str)
                cur += datetime.timedelta(days=1)

        try:
            sh = self.gc.open_by_key(config.GOOGLE_SHEET_ID)
        except Exception as e:
            await interaction.followup.send(f"❌ Не удалось открыть таблицу: {e}", ephemeral=True)
            return

        sheet_name = f"{start_date.strftime('%B_%Y')}"
        try:
            old_ws = sh.worksheet(sheet_name)
            sh.del_worksheet(old_ws)
        except:
            pass
        worksheet = sh.add_worksheet(title=sheet_name, rows=len(participants)+10, cols=len(dates)+5)

        day_names = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        headers = ["Игроки"]
        for dt in dates:
            weekday_name = day_names[dt.weekday()]
            headers.append(f"{weekday_name} ({dt.strftime('%d.%m')})")
        last_col = _column_letter(len(headers))
        range_headers = f"A1:{last_col}1"
        worksheet.update(range_headers, [headers], value_input_option='USER_ENTERED')

        row_num = 2
        for p in participants:
            row = [p["ign"]]
            if p["is_backup"]:
                for _ in dates:
                    row.append("З")
                range_row = f"A{row_num}:{last_col}{row_num}"
                worksheet.update(range_row, [row], value_input_option='USER_ENTERED')
                row_num += 1
                continue

            for dt in dates:
                date_str = dt.strftime("%Y-%m-%d")
                records = records_by_date.get(date_str, [])
                if not records:
                    row.append("?")
                    continue

                stage_attendance = [False, False, False]
                stage_late = [False, False, False]
                for stage in range(1, 4):
                    stage_records = [r for r in records if r["stage"] == stage]
                    if len(stage_records) == 2:
                        first = p["user_id"] in stage_records[0].get("present", [])
                        second = p["user_id"] in stage_records[1].get("present", [])
                        stage_attendance[stage-1] = first or second
                        if not first and second:
                            stage_late[stage-1] = True
                    elif len(stage_records) == 1:
                        stage_attendance[stage-1] = p["user_id"] in stage_records[0].get("present", [])

                present_count = sum(stage_attendance)
                has_excuse = date_str in excused_map.get(p["user_id"], set())

                if present_count == 0:
                    cell = "У" if has_excuse else "Н"
                else:
                    cell = f"{present_count}/3"
                    suffix = ""
                    if present_count in (1, 2):
                        if has_excuse:
                            suffix += " (У)"
                        if any(stage_late):
                            suffix += " (О)"
                        suffix = suffix.strip()
                        if suffix:
                            cell += " " + suffix
                row.append(cell)

            range_row = f"A{row_num}:{last_col}{row_num}"
            worksheet.update(range_row, [row], value_input_option='USER_ENTERED')
            row_num += 1

        COLOR_MAP = {
            "Лидер": (1.0, 0.95, 0.7),
            "Полковник": (1.0, 0.7, 0.7),
            "Офицер": (0.7, 1.0, 0.7),
            "Сержант": (0.8, 0.6, 0.4),
            "Боец": (0.3, 0.3, 0.3),
        }
        DEFAULT_COLOR = (0.95, 0.95, 0.95)

        requests = []
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": worksheet.id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 250},
                "fields": "pixelSize"
            }
        })
        last_col_index = len(headers) - 1
        if last_col_index >= 1:
            requests.append({
                "updateDimensionProperties": {
                    "range": {"sheetId": worksheet.id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": last_col_index},
                    "properties": {"pixelSize": 70},
                    "fields": "pixelSize"
                }
            })

        body_range = {
            "sheetId": worksheet.id,
            "startRowIndex": 0,
            "endRowIndex": row_num - 1,
            "startColumnIndex": 0,
            "endColumnIndex": len(headers)
        }
        requests.append({
            "repeatCell": {
                "range": body_range,
                "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}},
                "fields": "userEnteredFormat.backgroundColor"
            }
        })

        if last_col_index >= 1:
            requests.append({
                "updateBorders": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": 0,
                        "endRowIndex": row_num - 1,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2
                    },
                    "left": {"style": "SOLID_THICK", "color": {"red": 0, "green": 0, "blue": 0}}
                }
            })

        for col_idx in range(1, last_col_index):
            header_text = headers[col_idx]
            try:
                match = re.search(r'\((\d{2})\.(\d{2})\)', header_text)
                if match:
                    day = int(match.group(1))
                    month_num = int(match.group(2))
                    year_for_date = start_date.year
                    if month_num == 1 and start_date.month == 12:
                        year_for_date = start_date.year + 1
                    date_obj = datetime.date(year_for_date, month_num, day)
                    if date_obj.weekday() == 6:
                        requests.append({
                            "updateBorders": {
                                "range": {
                                    "sheetId": worksheet.id,
                                    "startRowIndex": 0,
                                    "endRowIndex": row_num - 1,
                                    "startColumnIndex": col_idx,
                                    "endColumnIndex": col_idx + 1
                                },
                                "right": {"style": "SOLID_THICK", "color": {"red": 0, "green": 0, "blue": 0}}
                            }
                        })
            except:
                pass

        requests.append({
            "updateBorders": {
                "range": {
                    "sheetId": worksheet.id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": len(headers)
                },
                "bottom": {"style": "SOLID_THICK", "color": {"red": 0, "green": 0, "blue": 0}}
            }
        })

        requests.append({
            "updateBorders": {
                "range": body_range,
                "top": {"style": "SOLID_THICK", "color": {"red": 0, "green": 0, "blue": 0}},
                "bottom": {"style": "SOLID_THICK", "color": {"red": 0, "green": 0, "blue": 0}},
                "left": {"style": "SOLID_THICK", "color": {"red": 0, "green": 0, "blue": 0}},
                "right": {"style": "SOLID_THICK", "color": {"red": 0, "green": 0, "blue": 0}}
            }
        })

        for idx, p in enumerate(participants):
            color = DEFAULT_COLOR
            for role_name, role_id in config.ROLE_COLORS.items():
                role = interaction.guild.get_role(role_id)
                if role and role in p["member"].roles:
                    color = COLOR_MAP.get(role_name, DEFAULT_COLOR)
                    break
            row_index = 2 + idx
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": row_index - 1,
                        "endRowIndex": row_index,
                        "startColumnIndex": 0,
                        "endColumnIndex": 1
                    },
                    "cell": {"userEnteredFormat": {"backgroundColor": {"red": color[0], "green": color[1], "blue": color[2]}}},
                    "fields": "userEnteredFormat.backgroundColor"
                }
            })

        if requests:
            sh.batch_update({"requests": requests})

        await interaction.followup.send(f"✅ Отчёт добавлен новым листом **{sheet_name}**\n{sh.url}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ReportGenerator(bot))