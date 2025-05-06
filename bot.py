# bot.py
from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from db import add_repair, get_repairs_by_wagon, mark_repair_done

async def start(message: types.Message):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(InlineKeyboardButton("P3", callback_data="p3"),
               InlineKeyboardButton("P4", callback_data="p4"),
               InlineKeyboardButton("P5", callback_data="p5"))
    await message.answer("Выберите тип вагона:", reply_markup=markup)

async def handle_wagon_selection(call: types.CallbackQuery):
    wagon_type = call.data
    # Здесь добавляем логику получения вагонов для типа (P3, P4, P5)
    wagons = ['117-5', '118-3']  # Примерные данные
    markup = InlineKeyboardMarkup(row_width=1)
    for wagon in wagons:
        markup.add(InlineKeyboardButton(wagon, callback_data=f"wagon_{wagon}"))
    await call.message.answer(f"Выберите вагон для {wagon_type}:", reply_markup=markup)

async def handle_wagon_details(call: types.CallbackQuery):
    wagon_number = call.data.split("_")[1]
    repairs = get_repairs_by_wagon(wagon_number)
    message = f"Поломки для вагона {wagon_number}:\n"
    for repair in repairs:
        message += f"- {repair[2]} (статус: {'выполнено' if repair[3] else 'не выполнено'})\n"
    await call.message.answer(message)

async def handle_repair_done(call: types.CallbackQuery):
    repair_id = int(call.data.split("_")[1])  # Получаем ID поломки
    # Ожидаем имя работника
    await call.message.answer("Введите ваше имя для отметки выполнения работы:")

# Настройка обработчиков
def setup_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands="start")
    dp.register_callback_query_handler(handle_wagon_selection, lambda call: call.data in ['p3', 'p4', 'p5'])
    dp.register_callback_query_handler(handle_wagon_details, lambda call: call.data.startswith("wagon_"))
    dp.register_callback_query_handler(handle_repair_done, lambda call: call.data.startswith("done_"))
