import asyncio
import logging
import datetime
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.client.default import DefaultBotProperties

# Данные
TOKEN = '7555068676:AAGPHintUgIJYmgyTnJPkDrKEYco3dsqwA4'
ADMIN_IDS = [6909254042]

# Локализация
LANGS = {
    "ru": {
        "choose_type": "Выбери тип ремонта:",
        "back": "⬅ Назад",
        "choose_wagon": "Вагоны типа {type}:",
        "defects_list": "Поломки вагона {number}:",
        "done": "Отмечено как выполнено",
        "add_help": "Добавить вагон: /add_wagon <номер> <тип> (P3, P4, P5)\nДобавить поломку: /add_defect <номер> <описание>",
        "choose_lang": "Выберите язык / Wybierz język",
    },
    "pl": {
        "choose_type": "Wybierz typ naprawy:",
        "back": "⬅ Powrót",
        "choose_wagon": "Wagony typu {type}:",
        "defects_list": "Usterki wagonu {number}:",
        "done": "Oznaczono jako naprawione",
        "add_help": "Dodaj wagon: /add_wagon <numer> <typ> (P3, P4, P5)\nDodaj usterkę: /add_defect <numer> <opis)",
        "choose_lang": "Выберите язык / Wybierz język",
    }
}
user_lang = {}

# Инициализация
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
REPAIR_TYPES = ['P3', 'P4', 'P5']


class LangState(StatesGroup):
    choosing = State()


async def init_db():
    async with aiosqlite.connect("wagons.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS wagons (
            id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, type TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, wagon_id INTEGER, description TEXT,
            status TEXT, done_by TEXT, done_at TEXT)""")
        await db.commit()


def get_text(user_id, key, **kwargs):
    lang = user_lang.get(user_id, "ru")
    return LANGS[lang][key].format(**kwargs)


@dp.message(F.text == '/start')
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(LangState.choosing)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="Polski", callback_data="lang_pl")]
        ]
    )
    await message.answer(LANGS["ru"]["choose_lang"], reply_markup=kb)


@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    user_lang[callback.from_user.id] = lang
    await state.clear()
    await show_main_menu(callback.message, callback.from_user.id)


async def show_main_menu(message, user_id):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=typ, callback_data=f"type_{typ}")] for typ in REPAIR_TYPES]
    )
    text = get_text(user_id, "choose_type")
    if user_id in ADMIN_IDS:
        text += f"\n\n{get_text(user_id, 'add_help')}"
    await message.answer(text, reply_markup=kb)


@dp.callback_query(F.data.startswith("type_"))
async def show_wagons(callback: CallbackQuery):
    repair_type = callback.data.split("_")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    async with aiosqlite.connect("wagons.db") as db:
        wagons = await db.execute_fetchall("SELECT id, number FROM wagons WHERE type = ?", (repair_type,))
        for wid, number in wagons:
            total = await db.execute_fetchone("SELECT COUNT(*) FROM defects WHERE wagon_id = ?", (wid,))
            done = await db.execute_fetchone("SELECT COUNT(*) FROM defects WHERE wagon_id = ? AND status = 'done'", (wid,))
            kb.inline_keyboard.append([
                InlineKeyboardButton(text=f"{number} ({done[0]}/{total[0]})", callback_data=f"wagon_{wid}")
            ])
    kb.inline_keyboard.append([InlineKeyboardButton(text=get_text(callback.from_user.id, "back"), callback_data="back_main")])
    await callback.message.edit_text(get_text(callback.from_user.id, "choose_wagon", type=repair_type), reply_markup=kb)


@dp.callback_query(F.data.startswith("wagon_"))
async def show_defects(callback: CallbackQuery):
    wagon_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect("wagons.db") as db:
        number = await db.execute_fetchone("SELECT number FROM wagons WHERE id = ?", (wagon_id,))
        defects = await db.execute_fetchall("SELECT id, description, status, done_by, done_at FROM defects WHERE wagon_id = ?", (wagon_id,))
    msg = f"{get_text(callback.from_user.id, 'defects_list', number=number[0])}\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for d_id, desc, status, done_by, done_at in defects:
        status_text = "✔" if status == "done" else "✖"
        note = f" ({done_by}, {done_at})" if done_by else ""
        msg += f"{d_id}. {desc} — {status_text}{note}\n"
        if status != "done":
            kb.inline_keyboard.append([
                InlineKeyboardButton(text=f"✅ {desc}", callback_data=f"done_{d_id}")
            ])
    kb.inline_keyboard.append([InlineKeyboardButton(text=get_text(callback.from_user.id, "back"), callback_data="back_main")])
    await callback.message.edit_text(msg, reply_markup=kb)


@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await show_main_menu(callback.message, callback.from_user.id)


@dp.callback_query(F.data.startswith("done_"))
async def mark_done(callback: CallbackQuery):
    defect_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect("wagons.db") as db:
        await db.execute("""
            UPDATE defects SET status = 'done', done_by = ?, done_at = ? WHERE id = ?
        """, (callback.from_user.full_name, datetime.date.today().isoformat(), defect_id))
        await db.commit()
    await callback.answer(get_text(callback.from_user.id, "done"))
    await callback.message.delete()
    await show_main_menu(callback.message, callback.from_user.id)


@dp.message(F.text.startswith('/add_wagon'))
async def add_wagon(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Нет доступа.")
    args = message.text.split()
    if len(args) != 3:
        return await message.answer("Формат: /add_wagon <номер> <тип>")
    number, wtype = args[1], args[2]
    async with aiosqlite.connect("wagons.db") as db:
        await db.execute("INSERT INTO wagons (number, type) VALUES (?, ?)", (number, wtype))
        await db.commit()
    await message.answer(f"Вагон {number} добавлен.")


@dp.message(F.text.startswith('/add_defect'))
async def add_defect(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Нет доступа.")
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.answer("Формат: /add_defect <номер_вагона> <описание>")
    number, desc = parts[1], parts[2]
    async with aiosqlite.connect("wagons.db") as db:
        wagon = await db.execute_fetchone("SELECT id FROM wagons WHERE number = ?", (number,))
        if not wagon:
            return await message.answer("Вагон не найден.")
        await db.execute("INSERT INTO defects (wagon_id, description, status) VALUES (?, ?, 'pending')", (wagon[0], desc))
        await db.commit()
    await message.answer("Поломка добавлена.")


# Запуск
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
