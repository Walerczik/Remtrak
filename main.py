import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.types.bot_command import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram import F

from datetime import datetime

TOKEN = "YOUR_BOT_TOKEN"
SUPER_ADMIN_ID = 123456789  # замените на свой Telegram ID

bot = Bot(token=TOKEN, default=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    description = State()

# Инициализация базы
async def init_db():
    conn = await aiosqlite.connect("db.sqlite")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            timestamp TEXT
        )
    """)
    await conn.commit()
    await conn.close()

async def log_action(user_id: int, action: str):
    conn = await aiosqlite.connect("db.sqlite")
    await conn.execute("INSERT INTO logs (user_id, action, timestamp) VALUES (?, ?, ?)", (user_id, action, datetime.now().isoformat()))
    await conn.commit()
    await conn.close()

async def is_admin(user_id: int):
    conn = await aiosqlite.connect("db.sqlite")
    cursor = await conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    await conn.close()
    return row is not None

async def set_commands(bot: Bot):
    user_cmds = [
        BotCommand(command="/start", description="Начать"),
        BotCommand(command="/add", description="Добавить задачу"),
        BotCommand(command="/delete", description="Удалить свои задачи")
    ]
    admin_cmds = user_cmds + [
        BotCommand(command="/report", description="Отчет о задачах")
    ]
    super_cmds = admin_cmds + [
        BotCommand(command="/add_admin", description="Добавить админа"),
        BotCommand(command="/remove_admin", description="Удалить админа")
    ]
    await bot.set_my_commands(user_cmds, scope=BotCommandScopeDefault())

    conn = await aiosqlite.connect('db.sqlite')
    async with conn.execute("SELECT user_id FROM admins") as cursor:
        for row in await cursor.fetchall():
            uid = row[0]
            if uid == SUPER_ADMIN_ID:
                await bot.set_my_commands(super_cmds, scope=BotCommandScopeChat(chat_id=uid))
            else:
                await bot.set_my_commands(admin_cmds, scope=BotCommandScopeChat(chat_id=uid))
    await conn.close()

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Привет! Используй меню или команды для взаимодействия с ботом.")

@dp.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    await message.answer("Отправь описание задачи:")
    await state.set_state(Form.description)

@dp.message(Form.description)
async def save_description(message: Message, state: FSMContext):
    desc = message.text
    conn = await aiosqlite.connect("db.sqlite")
    await conn.execute(
        "INSERT INTO tasks (user_id, description, created_at) VALUES (?, ?, ?)",
        (message.from_user.id, desc, datetime.now().isoformat())
    )
    await conn.commit()
    await conn.close()
    await log_action(message.from_user.id, f"Добавил задачу: {desc}")
    await message.answer("Задача добавлена!")
    await state.clear()

@dp.message(Command("delete"))
async def delete_tasks(message: Message):
    conn = await aiosqlite.connect("db.sqlite")
    await conn.execute("DELETE FROM tasks WHERE user_id = ?", (message.from_user.id,))
    await conn.commit()
    await conn.close()
    await log_action(message.from_user.id, "Удалил все свои задачи")
    await message.answer("Все твои задачи удалены.")

@dp.message(Command("report"))
async def report_cmd(message: Message):
    if not await is_admin(message.from_user.id) and message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("У тебя нет доступа к отчету.")
        return

    conn = await aiosqlite.connect("db.sqlite")
    cursor = await conn.execute("""
        SELECT tasks.id, tasks.user_id, tasks.description, tasks.status, tasks.created_at, logs.timestamp
        FROM tasks
        LEFT JOIN logs ON logs.action LIKE '%задачу%' AND logs.user_id = tasks.user_id
        ORDER BY tasks.created_at DESC
    """)
    rows = await cursor.fetchall()
    await conn.close()

    if not rows:
        await message.answer("Нет задач.")
        return

    report_lines = ["Отчет по задачам:\n"]
    for row in rows:
        task_id, uid, desc, status, created, log_time = row
        report_lines.append(f"[{task_id}] user_id: {uid} | {desc} | {status} | {created}")

    report_text = "\n".join(report_lines)
    await message.answer(f"<pre>{report_text}</pre>")

@dp.message(Command("add_admin"))
async def add_admin(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("Только суперадмин может добавлять админов.")
        return

    try:
        new_admin_id = int(message.text.split()[1])
    except:
        await message.answer("Использование: /add_admin ID")
        return

    conn = await aiosqlite.connect("db.sqlite")
    await conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_admin_id,))
    await conn.commit()
    await conn.close()

    await set_commands(bot)
    await log_action(message.from_user.id, f"Добавил админа {new_admin_id}")
    await message.answer(f"Пользователь {new_admin_id} теперь админ.")

@dp.message(Command("remove_admin"))
async def remove_admin(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("Только суперадмин может удалять админов.")
        return

    try:
        admin_id = int(message.text.split()[1])
    except:
        await message.answer("Использование: /remove_admin ID")
        return

    conn = await aiosqlite.connect("db.sqlite")
    await conn.execute("DELETE FROM admins WHERE user_id = ?", (admin_id,))
    await conn.commit()
    await conn.close()

    await set_commands(bot)
    await log_action(message.from_user.id, f"Удалил админа {admin_id}")
    await message.answer(f"Админ {admin_id} удален.")

async def main():
    await init_db()
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())