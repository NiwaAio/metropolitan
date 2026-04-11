import aiosqlite
import asyncio
import sqlite3

DB_PATH = "data/bot.db"

# ---------- Инициализация ----------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Предупреждения
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                user_id INTEGER,
                guild_id INTEGER,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        # Временные роли
        await db.execute("""
            CREATE TABLE IF NOT EXISTS temp_roles (
                user_id INTEGER,
                guild_id INTEGER,
                role_id INTEGER,
                until REAL,
                PRIMARY KEY (user_id, guild_id, role_id)
            )
        """)
        # Реакционные роли
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                message_id INTEGER,
                emoji TEXT,
                role_id INTEGER,
                PRIMARY KEY (message_id, emoji)
            )
        """)
        # Настройки сервера
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                filter_enabled BOOLEAN DEFAULT 1,
                log_channel_id INTEGER,
                verify_role_id INTEGER,
                auto_role_id INTEGER,
                welcome_channel_id INTEGER
            )
        """)
        # Вики (ключ-значение)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wiki_entries (
                guild_id INTEGER,
                item_id TEXT,
                info TEXT,
                PRIMARY KEY (guild_id, item_id)
            )
        """)
        # Ежедневное сообщение (сбор кв)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS raid_notify
                         (
                             guild_id
                             INTEGER
                             PRIMARY
                             KEY,
                             channel_id
                             INTEGER,
                             role_id
                             INTEGER,
                             days
                             TEXT
                             DEFAULT
                             '1,2,3,4,5,6,7',
                             enabled
                             BOOLEAN
                             DEFAULT
                             0,
                             postpone_until
                             REAL
                         )
                         """)
        await db.commit()
        # Работа со временем
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS raid_notify
                         (
                             guild_id
                             INTEGER
                             PRIMARY
                             KEY,
                             channel_id
                             INTEGER,
                             role_id
                             INTEGER,
                             days
                             TEXT
                             DEFAULT
                             '1,2,3,4,5,6,7',
                             times
                             TEXT
                             DEFAULT
                             '19:40,19:45,19:50,19:55',
                             enabled
                             BOOLEAN
                             DEFAULT
                             0,
                             postpone_until
                             REAL
                         )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS attendance_settings
                         (
                             guild_id
                             INTEGER
                             PRIMARY
                             KEY,
                             enabled
                             BOOLEAN
                             DEFAULT
                             0,
                             voice_channel_id
                             INTEGER,
                             role_id
                             INTEGER,
                             report_channel_id
                             INTEGER,
                             times
                             TEXT -- 6 времен через запятую
                         )
                         """)

        await db.execute("""
                         CREATE TABLE IF NOT EXISTS attendance_records
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             guild_id
                             INTEGER,
                             date
                             TEXT,   
                             check_time
                             TEXT,   
                             stage
                             INTEGER,
                             present
                             TEXT,   
                             absent
                             TEXT    
                         )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS ticket_config
                         (
                             guild_id
                             INTEGER
                             PRIMARY
                             KEY,
                             channel_id
                             INTEGER,
                             category_id
                             INTEGER,
                             admin_role_id
                             INTEGER,
                             message_id
                             INTEGER
                         )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS active_tickets
                         (
                             ticket_id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             guild_id
                             INTEGER,
                             user_id
                             INTEGER,
                             channel_id
                             INTEGER,
                             created_at
                             REAL
                         )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS excused_absences
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             guild_id
                             INTEGER,
                             user_id
                             INTEGER,
                             start_date
                             TEXT, -- YYYY-MM-DD
                             end_date
                             TEXT, -- YYYY-MM-DD
                             reason
                             TEXT,
                             created_by
                             INTEGER,
                             ticket_channel_id
                             INTEGER,
                             created_at
                             REAL
                         )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS ign_links
                         (
                             user_id
                             INTEGER
                             PRIMARY
                             KEY,
                             ign
                             TEXT
                             NOT
                             NULL,
                             guild_id
                             INTEGER,
                             created_at
                             REAL
                         )
                         """)
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS reg_tickets
                         (
                             ticket_id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             guild_id
                             INTEGER,
                             user_id
                             INTEGER,
                             channel_id
                             INTEGER,
                             created_at
                             REAL
                         )
                         """)
        columns = await db.execute_fetchall("PRAGMA table_info(raid_notify)")
        existing = [col[1] for col in columns]
        if 'times' not in existing:
            await db.execute("ALTER TABLE raid_notify ADD COLUMN times TEXT DEFAULT '19:40,19:45,19:50,19:55'")
        if 'days' not in existing:
            await db.execute("ALTER TABLE raid_notify ADD COLUMN days TEXT DEFAULT '1,2,3,4,5,6,7'")
        if 'enabled' not in existing:
            await db.execute("ALTER TABLE raid_notify ADD COLUMN enabled BOOLEAN DEFAULT 0")
        if 'postpone_until' not in existing:
            await db.execute("ALTER TABLE raid_notify ADD COLUMN postpone_until REAL")
        await db.commit()
        try:
            await db.execute("ALTER TABLE raid_notify ADD COLUMN last_bonus_date TEXT")
        except:
            pass


# ---------- Предупреждения ----------
async def get_warnings(user_id: int, guild_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT count FROM warnings WHERE user_id=? AND guild_id=?", (user_id, guild_id)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def add_warning(user_id: int, guild_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO warnings (user_id, guild_id, count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET count = count + 1
        """, (user_id, guild_id))
        await db.commit()
        return await get_warnings(user_id, guild_id)

async def clear_warnings(user_id: int, guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM warnings WHERE user_id=? AND guild_id=?", (user_id, guild_id))
        await db.commit()

# ---------- Временные роли ----------
async def add_temp_role(user_id: int, guild_id: int, role_id: int, until_timestamp: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO temp_roles (user_id, guild_id, role_id, until)
            VALUES (?, ?, ?, ?)
        """, (user_id, guild_id, role_id, until_timestamp))
        await db.commit()

async def get_expired_temp_roles(current_time: float):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, guild_id, role_id FROM temp_roles WHERE until <= ?", (current_time,)) as cursor:
            rows = await cursor.fetchall()
            return rows

async def remove_temp_role(user_id: int, guild_id: int, role_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM temp_roles WHERE user_id=? AND guild_id=? AND role_id=?", (user_id, guild_id, role_id))
        await db.commit()

# ---------- Реакционные роли ----------
async def add_reaction_role(message_id: int, emoji: str, role_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO reaction_roles VALUES (?, ?, ?)", (message_id, emoji, role_id))
        await db.commit()

async def get_role_for_reaction(message_id: int, emoji: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?", (message_id, emoji)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_all_reaction_roles(message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT emoji, role_id FROM reaction_roles WHERE message_id=?", (message_id,)) as cursor:
            return await cursor.fetchall()

async def remove_reaction_role(message_id: int, emoji: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reaction_roles WHERE message_id=? AND emoji=?", (message_id, emoji))
        await db.commit()

# ---------- Настройки сервера ----------
async def get_guild_setting(guild_id: int, setting: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"SELECT {setting} FROM guild_settings WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def set_guild_setting(guild_id: int, setting: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"""
            INSERT INTO guild_settings (guild_id, {setting})
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {setting}=excluded.{setting}
        """, (guild_id, value))
        await db.commit()

# ---------- Вики ----------
async def add_wiki_entry(guild_id: int, item_id: str, info: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO wiki_entries VALUES (?, ?, ?)", (guild_id, item_id, info))
        await db.commit()

async def get_wiki_entry(guild_id: int, item_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT info FROM wiki_entries WHERE guild_id=? AND item_id=?", (guild_id, item_id)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def delete_wiki_entry(guild_id: int, item_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM wiki_entries WHERE guild_id=? AND item_id=?", (guild_id, item_id))
        await db.commit()

# ---------- Функции для raid_notify ----------
async def get_raid_settings(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channel_id, role_id, days, times, enabled, postpone_until FROM raid_notify WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "channel_id": row[0],
                    "role_id": row[1],
                    "days": row[2].split(',') if row[2] else [],
                    "times": row[3].split(',') if row[3] else ["19:40", "19:45", "19:50", "19:55"],
                    "enabled": bool(row[4]),
                    "postpone_until": row[5]
                }
            return None

async def set_raid_times(guild_id: int, times_list: list):
    times_str = ','.join(times_list)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO raid_notify (guild_id, times)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET times=excluded.times
        """, (guild_id, times_str))
        await db.commit()

async def reset_raid_times(guild_id: int):
    """Сброс на стандартное время"""
    await set_raid_times(guild_id, ["19:40", "19:45", "19:50", "19:55"])

async def set_raid_channel(guild_id: int, channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO raid_notify (guild_id, channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id
        """, (guild_id, channel_id))
        await db.commit()

async def set_raid_role(guild_id: int, role_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO raid_notify (guild_id, role_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET role_id=excluded.role_id
        """, (guild_id, role_id))
        await db.commit()

async def set_raid_days(guild_id: int, days: list):
    """days: список чисел от 1 (пн) до 7 (вс)"""
    days_str = ','.join(map(str, days))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO raid_notify (guild_id, days)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET days=excluded.days
        """, (guild_id, days_str))
        await db.commit()

async def set_raid_enabled(guild_id: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO raid_notify (guild_id, enabled)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET enabled=excluded.enabled
        """, (guild_id, enabled))
        await db.commit()

async def set_raid_postpone(guild_id: int, until_timestamp: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO raid_notify (guild_id, postpone_until)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET postpone_until=excluded.postpone_until
        """, (guild_id, until_timestamp))
        await db.commit()

async def cancel_raid_postpone(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE raid_notify SET postpone_until = NULL WHERE guild_id = ?", (guild_id,))
        await db.commit()
async def get_last_bonus_date(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT last_bonus_date FROM raid_notify WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def set_last_bonus_date(guild_id: int, date_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE raid_notify SET last_bonus_date = ? WHERE guild_id = ?", (date_str, guild_id))
        await db.commit()
# ---------- Настройки attendance ----------
async def get_attendance_settings(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT enabled, voice_channel_id, role_id, report_channel_id, times FROM attendance_settings WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "enabled": bool(row[0]),
                    "voice_channel_id": row[1],
                    "role_id": row[2],
                    "report_channel_id": row[3],
                    "times": row[4].split(',') if row[4] else []
                }
            return None

async def _get_attendance_row(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT enabled, voice_channel_id, role_id, report_channel_id, times FROM attendance_settings WHERE guild_id=?", (guild_id,)) as cursor:
            return await cursor.fetchone()

async def set_attendance_enabled(guild_id: int, enabled: bool):
    row = await _get_attendance_row(guild_id)
    if row:
        # Обновляем существующую запись
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE attendance_settings SET enabled = ? WHERE guild_id = ?", (enabled, guild_id))
            await db.commit()
    else:
        # Создаём новую запись с дефолтами
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO attendance_settings (guild_id, enabled) VALUES (?, ?)", (guild_id, enabled))
            await db.commit()

async def set_attendance_voice_channel(guild_id: int, channel_id: int):
    row = await _get_attendance_row(guild_id)
    if row:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE attendance_settings SET voice_channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
            await db.commit()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO attendance_settings (guild_id, voice_channel_id) VALUES (?, ?)", (guild_id, channel_id))
            await db.commit()

async def set_attendance_role(guild_id: int, role_id: int):
    row = await _get_attendance_row(guild_id)
    if row:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE attendance_settings SET role_id = ? WHERE guild_id = ?", (role_id, guild_id))
            await db.commit()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO attendance_settings (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
            await db.commit()

async def set_attendance_report_channel(guild_id: int, channel_id: int):
    row = await _get_attendance_row(guild_id)
    if row:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE attendance_settings SET report_channel_id = ? WHERE guild_id = ?", (channel_id, guild_id))
            await db.commit()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO attendance_settings (guild_id, report_channel_id) VALUES (?, ?)", (guild_id, channel_id))
            await db.commit()

async def set_attendance_times(guild_id: int, times_list: list):
    times_str = ','.join(times_list)
    row = await _get_attendance_row(guild_id)
    if row:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE attendance_settings SET times = ? WHERE guild_id = ?", (times_str, guild_id))
            await db.commit()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO attendance_settings (guild_id, times) VALUES (?, ?)", (guild_id, times_str))
            await db.commit()
async def save_attendance_record(guild_id: int, date: str, check_time: str, stage: int, present_ids: list, absent_ids: list):
    present_str = ','.join(map(str, present_ids))
    absent_str = ','.join(map(str, absent_ids))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO attendance_records (guild_id, date, check_time, stage, present, absent)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (guild_id, date, check_time, stage, present_str, absent_str))
        await db.commit()

async def get_last_attendance_record(guild_id: int, date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT stage, present, absent FROM attendance_records
            WHERE guild_id=? AND date=? ORDER BY stage DESC LIMIT 1
        """, (guild_id, date)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "stage": row[0],
                    "present": list(map(int, row[1].split(','))) if row[1] else [],
                    "absent": list(map(int, row[2].split(','))) if row[2] else []
                }
            return None
# ---------- Настройки тикетов ----------
async def get_ticket_config(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channel_id, category_id, admin_role_id, message_id FROM ticket_config WHERE guild_id=?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"channel_id": row[0], "category_id": row[1], "admin_role_id": row[2], "message_id": row[3]}
            return None

async def set_ticket_config(guild_id: int, channel_id: int = None, category_id: int = None, admin_role_id: int = None, message_id: int = None):
    existing = await get_ticket_config(guild_id)
    async with aiosqlite.connect(DB_PATH) as db:
        if existing:
            await db.execute("UPDATE ticket_config SET channel_id=COALESCE(?,channel_id), category_id=COALESCE(?,category_id), admin_role_id=COALESCE(?,admin_role_id), message_id=COALESCE(?,message_id) WHERE guild_id=?",
                             (channel_id, category_id, admin_role_id, message_id, guild_id))
        else:
            await db.execute("INSERT INTO ticket_config (guild_id, channel_id, category_id, admin_role_id, message_id) VALUES (?,?,?,?,?)",
                             (guild_id, channel_id, category_id, admin_role_id, message_id))
        await db.commit()

# ---------- Активные тикеты ----------
async def create_active_ticket(guild_id: int, user_id: int, channel_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO active_tickets (guild_id, user_id, channel_id, created_at) VALUES (?,?,?,?)",
                                  (guild_id, user_id, channel_id, asyncio.get_event_loop().time()))
        await db.commit()
        return cursor.lastrowid

async def get_active_ticket_by_user(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ticket_id, channel_id FROM active_tickets WHERE guild_id=? AND user_id=?", (guild_id, user_id)) as cursor:
            row = await cursor.fetchone()
            return {"ticket_id": row[0], "channel_id": row[1]} if row else None

async def get_active_ticket_by_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ticket_id, guild_id, user_id FROM active_tickets WHERE channel_id=?", (channel_id,)) as cursor:
            row = await cursor.fetchone()
            return {"ticket_id": row[0], "guild_id": row[1], "user_id": row[2]} if row else None

async def delete_active_ticket(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM active_tickets WHERE channel_id=?", (channel_id,))
        await db.commit()

# ---------- Оправданные отсутствия ----------
async def add_excused_absence(guild_id: int, user_id: int, start_date: str, end_date: str, reason: str, created_by: int, ticket_channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO excused_absences (guild_id, user_id, start_date, end_date, reason, created_by, ticket_channel_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
                         (guild_id, user_id, start_date, end_date, reason, created_by, ticket_channel_id, asyncio.get_event_loop().time()))
        await db.commit()

async def get_excused_absences(guild_id: int, user_id: int = None, date: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id and date:
            async with db.execute("SELECT id, user_id, start_date, end_date, reason, created_by, ticket_channel_id FROM excused_absences WHERE guild_id=? AND user_id=? AND date(?) BETWEEN start_date AND end_date", (guild_id, user_id, date)) as cursor:
                rows = await cursor.fetchall()
        elif user_id:
            async with db.execute("SELECT id, user_id, start_date, end_date, reason, created_by, ticket_channel_id FROM excused_absences WHERE guild_id=? AND user_id=? ORDER BY start_date DESC", (guild_id, user_id)) as cursor:
                rows = await cursor.fetchall()
        elif date:
            async with db.execute("SELECT id, user_id, start_date, end_date, reason, created_by, ticket_channel_id FROM excused_absences WHERE guild_id=? AND date(?) BETWEEN start_date AND end_date", (guild_id, date)) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute("SELECT id, user_id, start_date, end_date, reason, created_by, ticket_channel_id FROM excused_absences WHERE guild_id=? ORDER BY start_date DESC", (guild_id,)) as cursor:
                rows = await cursor.fetchall()
        return [{"id": r[0], "user_id": r[1], "start_date": r[2], "end_date": r[3], "reason": r[4], "created_by": r[5], "ticket_channel_id": r[6]} for r in rows]

async def delete_excused_absence(absence_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM excused_absences WHERE id=?", (absence_id,))
        await db.commit()

async def delete_excused_absences_by_user(guild_id: int, user_id: int, date: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if date:
            await db.execute("DELETE FROM excused_absences WHERE guild_id=? AND user_id=? AND date(?) BETWEEN start_date AND end_date", (guild_id, user_id, date))
        else:
            await db.execute("DELETE FROM excused_absences WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await db.commit()
async def set_ign_link(user_id: int, guild_id: int, ign: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO ign_links (user_id, guild_id, ign, created_at) VALUES (?, ?, ?, ?)",
                         (user_id, guild_id, ign, asyncio.get_event_loop().time()))
        await db.commit()

async def get_ign_by_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ign FROM ign_links WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_user_by_ign(ign: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM ign_links WHERE ign=?", (ign,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_all_ign_links(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, ign FROM ign_links WHERE guild_id=?", (guild_id,)) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

async def delete_ign_link(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM ign_links WHERE user_id=?", (user_id,))
        await db.commit()
async def get_attendance_record_by_time(guild_id: int, date: str, check_time: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT present, absent FROM attendance_records WHERE guild_id=? AND date=? AND check_time=?", (guild_id, date, check_time)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "present": list(map(int, row[0].split(','))) if row[0] else [],
                    "absent": list(map(int, row[1].split(','))) if row[1] else []
                }
            return None
async def create_reg_ticket(guild_id: int, user_id: int, channel_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO reg_tickets (guild_id, user_id, channel_id, created_at) VALUES (?,?,?,?)",
                                  (guild_id, user_id, channel_id, asyncio.get_event_loop().time()))
        await db.commit()
        return cursor.lastrowid

async def get_reg_ticket_by_user(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ticket_id, channel_id FROM reg_tickets WHERE guild_id=? AND user_id=?", (guild_id, user_id)) as cursor:
            row = await cursor.fetchone()
            return {"ticket_id": row[0], "channel_id": row[1]} if row else None

async def get_reg_ticket_by_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT ticket_id, guild_id, user_id FROM reg_tickets WHERE channel_id=?", (channel_id,)) as cursor:
            row = await cursor.fetchone()
            return {"ticket_id": row[0], "guild_id": row[1], "user_id": row[2]} if row else None

async def delete_reg_ticket(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reg_tickets WHERE channel_id=?", (channel_id,))
        await db.commit()