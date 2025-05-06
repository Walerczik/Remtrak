# main.py
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

API_TOKEN = '7555068676:AAGPHintUgIJYmgyTnJPkDrKEYco3dsqwA4'
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = 'https://your-render-url.onrender.com' + WEBHOOK_PATH  # Заменить на свой URL

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Устанавливаем базовое логирование
logging.basicConfig(level=logging.INFO)

# Модели и обработчики команд
@dp.message()
async def echo(message: types.Message):
    await message.answer("Бот работает!")

# Ставим вебхук
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

# Удаляем вебхук
async def on_shutdown():
    await bot.delete_webhook()

# Основной объект приложения FastAPI
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "API is working"}

# Настройка aiohttp для работы с вебхуками
async def create_app():
    aiohttp_app = web.Application()
    aiohttp_app["bot"] = bot

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(aiohttp_app, path=WEBHOOK_PATH)
    setup_application(aiohttp_app, dp, on_startup=on_startup, on_shutdown=on_shutdown)

    return aiohttp_app

if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=10000)
