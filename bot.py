import asyncio
import logging
import html

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.executor import start_webhook

import config
import database

# — Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# — Тексты (локализация)
LANGS = {
    "ru": {
        "choose_language": "Выберите язык / Wybierz język",
        "choose_type": "Выберите тип ремонта:",
        "back": "⬅ Назад",
        "choose_wagon": "Вагоны типа {type}:",
        "defects_list": "Поломки вагона {number}:",
        "done": "Отмечено как выполнено",
        "add_help": "Добавить вагон: /add_wagon <номер> <тип>\nДобавить поломку: /add_defect <номер> <описание>",
        "change_language": "Сменить язык"
    },
    "pl": {
        "choose_language": "Wybierz język / Выберите язык",
        "choose_type": "Wybierz typ naprawy:",
        "back": "⬅ Powrót",
        "choose_wagon": "Wagony typu {type}:",
        "defects_list": "Usterki wagonu {number}:",
        "done": "Oznaczono jako naprawione",
        "add_help": "Dodaj wagon: /add_wagon <numer> <typ>\nDodaj usterkę: /add_defect <numer> <opis>",
        "change_language": "Zmień język"
    }
}

# — Хранилище выбора языка пользователей
user_lang: dict[int, str] = {}

# — Инициализация бота и диспетчера
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# — Сброс старого вебхука и создание БД
async def on_startup(_):
    logger.info("Инициализация базы данных...")
    await database.init_db()
    # Устанавливаем вебхук
    await bot.set_webhook(config.WEBHOOK_URL)

# — Очистка вебхука при остановке
async def on_shutdown(_):
    logger.warning("Завершаем работу, удаляем вебхук...")
    await bot.delete_webhook(drop_pending_updates=True)

# — Команда /start — выбор языка
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("Polski", callback_data="lang_pl")],
    ])
    await message.answer(
        LANGS["ru"]["choose_language"],
        reply_markup=kb
    )

# — Переключение языка
@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_", 1)[1]
    user_lang[callback.from_user.id] = lang
    # Показать меню выбора типа
    await show_main_menu(callback.message, callback.from_user.id)
    await callback.answer()

# — Меню: выбор типа ремонта
async def show_main_menu(message: types.Message, user_id: int):
    lang = user_lang.get(user_id, "ru")
    text = LANGS[lang]["choose_type"]
    if user_id in config.ADMIN_IDS:
        text += "\n\n" + LANGS[lang]["add_help"]
    kb = InlineKeyboardMarkup()
    for t in config.REPAIR_TYPES:
        kb.add(InlineKeyboardButton(t, callback_data=f"type_{t}"))
    kb.add(InlineKeyboardButton(LANGS[lang]["change_language"], callback_data="lang_select"))
    await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "lang_select")
async def lang_select(callback: types.CallbackQuery):
    # вернемся к выбору языка
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("Polski", callback_data="lang_pl")],
    ])
    await callback.message.edit_text(
        LANGS["ru"]["choose_language"],
        reply_markup=kb
    )
    await callback.answer()

# — Список вагонов по типу
@dp.callback_query(F.data.startswith("type_"))
async def show_wagons(callback: types.CallbackQuery):
    t = callback.data.split("_", 1)[1]
    lang = user_lang.get(callback.from_user.id, "ru")
    rows = await database.get_wagons_by_type(t)
    kb = InlineKeyboardMarkup()
    for wid, number in rows:
        defects = await database.get_defects_by_wagon(wid)
        total = len(defects)
        done = sum(1 for d in defects if d[2] == "done")
        kb.add(InlineKeyboardButton(
            f"{html.escape(number)} ({done}/{total})",
            callback_data=f"wagon_{wid}"
        ))
    kb.add(InlineKeyboardButton(LANGS[lang]["back"], callback_data="main_menu"))
    await callback.message.edit_text(
        LANGS[lang]["choose_wagon"].format(type=html.escape(t)),
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data == "main_menu")
async def back_main(callback: types.CallbackQuery):
    await show_main_menu(callback.message, callback.from_user.id)
    await callback.answer()

# — Поломки конкретного вагона
@dp.callback_query(F.data.startswith("wagon_"))
async def show_defects(callback: types.CallbackQuery):
    wid = int(callback.data.split("_", 1)[1])
    lang = user_lang.get(callback.from_user.id, "ru")
    number = await database.get_wagon_number(wid) or "–"
    defects = await database.get_defects_by_wagon(wid)

    msg = LANGS[lang]["defects_list"].format(number=html.escape(number)) + "\n\n"
    kb = InlineKeyboardMarkup()
    for did, desc, status, done_by, done_at in defects:
        status_txt = "✔" if status == "done" else "✖"
        note = f" ({html.escape(done_by)}, {done_at})" if status == "done" else ""
        msg += f"{did}. {html.escape(desc)} — {status_txt}{note}\n"
        if status != "done":
            kb.add(InlineKeyboardButton(
                f"✅ {html.escape(desc)}",
                callback_data=f"done_{did}"
            ))
    kb.add(InlineKeyboardButton(LANGS[lang]["back"], callback_data="type_back"))
    await callback.message.edit_text(msg, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "type_back")
async def back_to_types(callback: types.CallbackQuery):
    # просто покажем главное меню (типы)
    await show_main_menu(callback.message, callback.from_user.id)
    await callback.answer()

# — Отметить поломку сделанной
@dp.callback_query(F.data.startswith("done_"))
async def mark_done(callback: types.CallbackQuery):
    did = int(callback.data.split("_", 1)[1])
    await database.mark_defect_done(did, callback.from_user.full_name)
    lang = user_lang.get(callback.from_user.id, "ru")
    await callback.answer(LANGS[lang]["done"])
    # вернём пользователя в главное меню
    await show_main_menu(callback.message, callback.from_user.id)

# — Админ: добавить вагон
@dp.message(F.text.startswith("/add_wagon"))
async def cmd_add_wagon(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return await message.reply("Нет доступа.")
    parts = message.text.split()
    if len(parts) != 3 or parts[2] not in config.REPAIR_TYPES:
        return await message.reply("Формат: /add_wagon <номер> <тип> (P3, P4, P5)")
    await database.add_wagon(parts[1], parts[2])
    await message.reply(f"Вагон {parts[1]} ({parts[2]}) добавлен.")

# — Админ: добавить поломку
@dp.message(F.text.startswith("/add_defect"))
async def cmd_add_defect(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return await message.reply("Нет доступа.")
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.reply("Формат: /add_defect <номер_вагона> <описание>")
    ok = await database.add_defect(parts[1], parts[2])
    if not ok:
        return await message.reply("Вагон не найден.")
    await message.reply("Поломка добавлена.")

# — Запуск
if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=config.WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
    )