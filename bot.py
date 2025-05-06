import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.executor import start_webhook
from aiogram.types import ParseMode
import sqlite3
from database import add_wagon, add_fault, get_faults, mark_fault_done

# Токен и ID администратора
API_TOKEN = '7555068676:AAGPHintUgIJYmgyTnJPkDrKEYco3dsqwA4'
ADMIN_ID = 6909254042

# Логирование
logging.basicConfig(level=logging.INFO)

# Создаем объект бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Подключение к базе данных (например, SQLite)
from database import create_connection

# Обработчик команды старт
@dp.message_handler(commands=['start'])
async def on_start(message: types.Message):
    await message.reply("Привет! Выберите язык / Change language.", reply_markup=types.ReplyKeyboardMarkup([
        [types.KeyboardButton('Русский'), types.KeyboardButton('Polski')]
    ]))

# Показать главное меню
async def show_main_menu(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('P3'), types.KeyboardButton('P4'), types.KeyboardButton('P5'))
    await message.reply("Главное меню. Выберите тип вагона", reply_markup=keyboard)

# Админский доступ к добавлению вагона
@dp.message_handler(commands=['add_wagon'])
async def add_wagon_command(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Введите номер вагона и тип вагона (например: 117-5 P3)")

@dp.message_handler(lambda message: message.text.count(" ") == 1)
async def add_wagon_info(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        wagon_number, type_ = message.text.split()
        add_wagon(wagon_number, type_)
        await message.reply(f"Вагон {wagon_number} типа {type_} добавлен в базу данных.")

# Админский доступ к добавлению поломки
@dp.message_handler(commands=['add_fault'])
async def add_fault_command(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Введите номер вагона и описание поломки (например: 117-5 Отсутствует тормоз)")

@dp.message_handler(lambda message: message.text.count(" ") == 1)
async def add_fault_info(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        wagon_number, fault_description = message.text.split(" ", 1)
        
        # Получаем ID вагона по номеру
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT id FROM wagons WHERE wagon_number = ?''', (wagon_number,))
        row = cursor.fetchone()
        conn.close()

        if row:
            wagon_id = row[0]
            add_fault(wagon_id, fault_description)
            await message.reply(f"Поломка для вагона {wagon_number} добавлена в базу данных.")
        else:
            await message.reply(f"Вагон с номером {wagon_number} не найден.")

# Админский доступ для просмотра всех поломок
@dp.message_handler(commands=['view_faults'])
async def view_faults(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT wagon_number FROM wagons''')
        wagons = cursor.fetchall()
        conn.close()

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for wagon in wagons:
            keyboard.add(types.KeyboardButton(wagon[0]))
        
        await message.reply("Выберите вагон для просмотра поломок:", reply_markup=keyboard)

# Просмотр поломок для вагона
@dp.message_handler(lambda message: message.text in [wagon[0] for wagon in wagons])
async def view_faults_for_wagon(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT id FROM wagons WHERE wagon_number = ?''', (message.text,))
        row = cursor.fetchone()
        conn.close()

        if row:
            wagon_id = row[0]
            faults = get_faults(wagon_id)
            response = f"Поломки для вагона {message.text}:\n"
            for fault in faults:
                status = "Выполнено" if fault[3] else "Не выполнено"
                response += f"Поломка: {fault[2]}, Статус: {status}, Работник: {fault[4] if fault[4] else 'Не указан'}\n"
            
            await message.reply(response)
        else:
            await message.reply(f"Вагон с номером {message.text} не найден.")

# Обработчик для отметки выполненной поломки
@dp.message_handler(commands=['mark_done'])
async def mark_done_command(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Введите номер поломки и имя работника (например: 1 Иванов):")

@dp.message_handler(lambda message: message.text.count(" ") == 1)
async def mark_done_info(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        fault_id, worker = message.text.split()
        try:
            fault_id = int(fault_id)
            mark_fault_done(fault_id, worker)
            await message.reply(f"Поломка {fault_id} отмечена как выполненная.")
        except ValueError:
            await message.reply("Некорректный ввод.")

if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path="/webhook",
        on_start=None,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080))
    )
