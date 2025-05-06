import aiosqlite
from datetime import date

DATABASE = "wagons.db"

async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wagons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS defects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wagon_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                done_by TEXT,
                done_at TEXT,
                FOREIGN KEY(wagon_id) REFERENCES wagons(id)
            )
        """)
        await db.commit()

async def add_wagon(number: str, wtype: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT OR IGNORE INTO wagons (number, type) VALUES (?, ?)",
            (number, wtype)
        )
        await db.commit()

async def get_wagons_by_type(wtype: str):
    async with aiosqlite.connect(DATABASE) as db:
        return await db.execute_fetchall(
            "SELECT id, number FROM wagons WHERE type = ?",
            (wtype,)
        )

async def add_defect(wagon_number: str, description: str) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        row = await db.execute_fetchone(
            "SELECT id FROM wagons WHERE number = ?",
            (wagon_number,)
        )
        if not row:
            return False
        wid = row[0]
        await db.execute(
            "INSERT INTO defects (wagon_id, description) VALUES (?, ?)",
            (wid, description)
        )
        await db.commit()
        return True

async def get_defects_by_wagon(wagon_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        return await db.execute_fetchall("""
            SELECT id, description, status, done_by, done_at
              FROM defects WHERE wagon_id = ?
        """, (wagon_id,))

async def mark_defect_done(defect_id: int, user_fullname: str):
    today = date.today().isoformat()
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            UPDATE defects
               SET status = 'done', done_by = ?, done_at = ?
             WHERE id = ?
        """, (user_fullname, today, defect_id))
        await db.commit()

async def get_wagon_number(wagon_id: int) -> str | None:
    async with aiosqlite.connect(DATABASE) as db:
        row = await db.execute_fetchone(
            "SELECT number FROM wagons WHERE id = ?",
            (wagon_id,)
        )
        return row[0] if row else None