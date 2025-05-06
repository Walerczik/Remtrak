import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import os

TOKEN = "7555068676:AAGPHintUgIJYmgyTnJPkDrKEYco3dsqwA4"
ADMIN_IDS = [6909254042]

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())


class Form(StatesGroup):
    task = State()


async def init_db():
    async with aiosqlite.connect("tasks.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            task TEXT,
            timestamp TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )""")
        for admin_id in ADMIN_IDS:
            await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,))
        await db.commit()


async def is_admin(user_id):
    async with aiosqlite.connect("tasks.db") as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone() is not None


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Отправь /add чтобы добавить задачу.")


@dp.message(Command("add"))
async def add_task(message: types.Message, state: FSMContext):
    await message.answer("Введите задачу:")
    await state.set_state(Form.task)


@dp.message(Form.task)
async def save_task(message: types.Message, state: FSMContext):
    task_text = message.text
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect("tasks.db") as db:
        await db.execute("INSERT INTO tasks (user_id, username, task, timestamp) VALUES (?, ?, ?, ?)",
                         (message.from_user.id, message.from_user.username or "", task_text, timestamp))
        await db.commit()
    await message.answer("Задача сохранена!")
    await state.clear()


@dp.message(Command("delete"))
async def delete_task(message: types.Message):
    async with aiosqlite.connect("tasks.db") as db:
        await db.execute("DELETE FROM tasks WHERE user_id = ?", (message.from_user.id,))
        await db.commit()
    await message.answer("Ваши задачи удалены.")


@dp.message(Command("report"))
async def send_report(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("У вас нет прав для этой команды.")

    report_lines = []
    async with aiosqlite.connect("tasks.db") as db:
        async with db.execute("SELECT user_id, username, task, timestamp FROM tasks ORDER BY timestamp") as cursor:
            async for row in cursor:
                user_id, username, task, timestamp = row
                report_lines.append(
                    f"[{timestamp}] @{username or 'NoUsername'} (ID: {user_id}):\n{task}\n"
                )

    if not report_lines:
        return await message.answer("Нет данных за период.")

    filename = "report.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    await message.answer_document(FSInputFile(filename))
    os.remove(filename)


@dp.message(Command("add_admin"))
async def add_admin_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("У вас нет прав.")

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.answer("Формат: /add_admin user_id")

    user_id = int(parts[1])
    async with aiosqlite.connect("tasks.db") as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        await db.commit()

    await message.answer(f"Админ {user_id} добавлен.")


@dp.message(Command("remove_admin"))
async def remove_admin_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("У вас нет прав.")

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.answer("Формат: /remove_admin user_id")

    user_id = int(parts[1])
    async with aiosqlite.connect("tasks.db") as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()

    await message.answer(f"Админ {user_id} удалён.")


async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())