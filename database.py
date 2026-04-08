import aiosqlite
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