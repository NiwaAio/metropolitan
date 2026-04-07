import aiosqlite

DB_PATH = "data/bot.db"

# ---------- Инициализация ----------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Предупреждения (варны)
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
        await db.commit()

# ---------- Предупреждения (варны) ----------
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