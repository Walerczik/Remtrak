import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = '7555068676:AAGPHintUgIJYmgyTnJPkDrKEYco3dsqwA4'
ADMIN_ID = 6909254042

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

dp.middleware.setup(LoggingMiddleware())  # Это будет работать без ошибок

# Главная клавиатура
main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("Русский"),
    KeyboardButton("Polski"),
)

# Клавиатура для выбора типа вагона
wagon_type_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("P3"),
    KeyboardButton("P4"),
    KeyboardButton("P5"),
    KeyboardButton("Назад")
)

# Клавиатура для возврата назад
back_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("Назад")
)

# Хранение информации о вагонах (на время работы)
wagons = {
    "P3": ["117-5 (1/3)", "118-6 (2/3)"],
    "P4": ["120-1 (0/3)", "121-2 (1/3)"],
    "P5": ["122-7 (0/3)", "123-3 (1/3)"]
}

# Функция выбора языка
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Привет! Выберите язык / Change language.", reply_markup=main_keyboard)

# Функция смены языка
@dp.message_handler(lambda message: message.text in ['Русский', 'Polski'])
async def set_language(message: types.Message):
    language = message.text
    if language == 'Русский':
        await message.reply("Вы выбрали русский язык.", reply_markup=wagon_type_keyboard)
    else:
        await message.reply("Вы wybrali język polski.", reply_markup=wagon_type_keyboard)

# Функция выбора типа вагона (P3, P4, P5)
@dp.message_handler(lambda message: message.text in ['P3', 'P4', 'P5'])
async def choose_wagon(message: types.Message):
    wagon_type = message.text
    wagons_list = "\n".join(wagons[wagon_type])
    await message.reply(f"Список вагонов типа {wagon_type}:\n{wagons_list}", reply_markup=back_keyboard)

# Обработка кнопки назад
@dp.message_handler(lambda message: message.text == "Назад")
async def go_back(message: types.Message):
    await message.reply("Выберите язык / Choose language.", reply_markup=main_keyboard)

# Функция для обработки конкретного вагона
@dp.message_handler(lambda message: message.text in [wagon.split(' ')[0] for wagon_list in wagons.values() for wagon in wagon_list])
async def wagon_details(message: types.Message):
    wagon_id = message.text
    for wagon_type, wagon_list in wagons.items():
        for wagon in wagon_list:
            if wagon.startswith(wagon_id):
                parts = wagon.split(' ')
                broken_parts = parts[1]  # Поломки, например (1/3)
                await message.reply(f"Вагон: {wagon_id}\nПоломки: {broken_parts}\nОтметьте, если работа выполнена.", reply_markup=back_keyboard)

# Обработка отметки о выполнении работы
@dp.message_handler(lambda message: message.text == 'Сделано')
async def mark_done(message: types.Message):
    done_date = "2025-05-06"  # Можем использовать дату выполнения работы
    done_worker = message.from_user.full_name  # Имя пользователя, который выполнил
    await message.reply(f"Работа выполнена!\nДата: {done_date}\nИсполнитель: {done_worker}", reply_markup=back_keyboard)

if __name__ == '__main__':
    from aiogram.utils import executor
    executor.start_polling(dp, skip_updates=True)