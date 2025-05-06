import os

# Токен бота (или задайте в ENV)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7555068676:AAGPHintUgIJYmgyTnJPkDrKEYco3dsqwA4")

# ID админов
ADMIN_IDS = [6909254042]

# Вебхук-конфиг для Render
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://yourapp.onrender.com")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Типы ремонтов
REPAIR_TYPES = ["P3", "P4", "P5"]
