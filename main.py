import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import os

TOKEN = "7555068676:AAGPHintUgIJYmgyTnJPkDrKEYco3dsqwA4"
ADMIN_IDS = [6909254042]

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

LANGUAGES = {
    "ru": {"back": "⬅️ Назад", "choose": "Выберите тип вагона"},
    "pl": {"back": "⬅️ Wróć", "choose": "Wybierz typ wagonu"}
}

user_language = {}

class ReportStates(StatesGroup):
    waiting_for_dates = State()

class AddDefect(StatesGroup):
    waiting_for_data = State()

class DeleteDefect(StatesGroup):
    waiting_for_id = State()

async def init_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS defects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wagon_type TEXT,
                wagon_number TEXT,
                description TEXT,
                fixed_by TEXT,
                fixed_at TEXT
            )
        """)
        await db.commit()

@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Русский", "Polski")
    await message.answer("Выберите язык / Wybierz język:", reply_markup=keyboard)

@dp.message(lambda m: m.text in ["Русский", "Polski"])
async def set_lang(message: types.Message):
    lang = "ru" if message.text == "Русский" else "pl"
    user_language[message.from_user.id] = lang
    await show_main_menu(message)

async def show_main_menu(message: types.Message):
    lang = user_language.get(message.from_user.id, "ru")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("P3", "P4", "P5", LANGUAGES[lang]["back"])
    await message.answer(LANGUAGES[lang]["choose"], reply_markup=kb)

@dp.message(lambda m: m.text in ["P3", "P4", "P5"])
async def show_wagons(message: types.Message):
    wagon_type = message.text
    lang = user_language.get(message.from_user.id, "ru")
    kb = types.InlineKeyboardMarkup()
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT wagon_number, COUNT(*), SUM(CASE WHEN fixed_at IS NOT NULL THEN 1 ELSE 0 END) FROM defects WHERE wagon_type=? GROUP BY wagon_number", (wagon_type,)) as cursor:
            async for row in cursor:
                label = f"{row[0]} ({row[2]}/{row[1]})"
                kb.add(types.InlineKeyboardButton(text=label, callback_data=f"wagon:{wagon_type}:{row[0]}"))
    await message.answer(f"Вагоны типа {wagon_type}:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("wagon:"))
async def show_defects(callback: types.CallbackQuery):
    _, wagon_type, wagon_number = callback.data.split(":")
    lang = user_language.get(callback.from_user.id, "ru")
    kb = types.InlineKeyboardMarkup()
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT id, description, fixed_at FROM defects WHERE wagon_type=? AND wagon_number=?", (wagon_type, wagon_number)) as cursor:
            async for row in cursor:
                status = "✔" if row[2] else "❌"
                kb.add(types.InlineKeyboardButton(text=f"{status} {row[1]}", callback_data=f"fix:{row[0]}"))
    kb.add(types.InlineKeyboardButton(text=LANGUAGES[lang]["back"], callback_data="back"))
    await callback.message.edit_text(f"Поломки вагона {wagon_number}:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("fix:"))
async def mark_fixed(callback: types.CallbackQuery):
    defect_id = int(callback.data.split(":")[1])
    async with aiosqlite.connect("database.db") as db:
        await db.execute("UPDATE defects SET fixed_by=?, fixed_at=? WHERE id=?", (callback.from_user.full_name, datetime.now().strftime("%Y-%m-%d %H:%M"), defect_id))
        await db.commit()
    await callback.answer("Отмечено как сделано.")
    await callback.message.delete()

@dp.callback_query(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    await show_main_menu(callback.message)

# Отчёт
@dp.message(Command("report"))
async def report_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Нет доступа.")
    await message.answer("Введите даты: <code>2024-05-01 2024-05-06</code>")
    await state.set_state(ReportStates.waiting_for_dates)

@dp.message(ReportStates.waiting_for_dates)
async def process_report(message: types.Message, state: FSMContext):
    try:
        start_date, end_date = message.text.split()
        async with aiosqlite.connect("database.db") as db:
            async with db.execute("""SELECT wagon_number, description, fixed_by, fixed_at 
                                     FROM defects 
                                     WHERE fixed_at BETWEEN ? AND ? 
                                     ORDER BY fixed_at""", (start_date, end_date)) as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    await message.answer("Нет записей за указанный период.")
                else:
                    report_lines = [f"{r[3]} — {r[2]} починил {r[0]}: {r[1]}" for r in rows]
                    with open("report.txt", "w", encoding="utf-8") as f:
                        f.write("\n".join(report_lines))
                    await message.answer_document(FSInputFile("report.txt"), caption="Отчет по ремонту")
                    os.remove("report.txt")
    except Exception:
        await message.answer("Ошибка. Используй формат: YYYY-MM-DD YYYY-MM-DD")
    finally:
        await state.clear()

# Добавление поломки
@dp.message(Command("add"))
async def add_defect_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Нет доступа.")
    await message.answer("Введи поломку в формате:\n<code>P3 117-5 Проблема с тормозами</code>")
    await state.set_state(AddDefect.waiting_for_data)

@dp.message(AddDefect.waiting_for_data)
async def process_add(message: types.Message, state: FSMContext):
    try:
        wagon_type, wagon_number, description = message.text.split(maxsplit=2)
        async with aiosqlite.connect("database.db") as db:
            await db.execute("INSERT INTO defects (wagon_type, wagon_number, description) VALUES (?, ?, ?)", (wagon_type, wagon_number, description))
            await db.commit()
        await message.answer("Добавлено.")
    except Exception:
        await message.answer("Ошибка. Используй формат: P3 117-5 описание")
    finally:
        await state.clear()

# Удаление поломки
@dp.message(Command("delete"))
async def delete_defect_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Нет доступа.")
    await message.answer("Введи ID поломки для удаления:")
    await state.set_state(DeleteDefect.waiting_for_id)

@dp.message(DeleteDefect.waiting_for_id)
async def process_delete(message: types.Message, state: FSMContext):
    try:
        defect_id = int(message.text)
        async with aiosqlite.connect("database.db") as db:
            await db.execute("DELETE FROM defects WHERE id=?", (defect_id,))
            await db.commit()
        await message.answer("Удалено.")
    except Exception:
        await message.answer("Ошибка. Введи числовой ID.")
    finally:
        await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())