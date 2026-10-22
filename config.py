"""
Конфигурационный файл бота.
Здесь хранятся настройки и токен бота.
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# URL для вебхука (для Render)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app.onrender.com")

# MongoDB URI
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")

# Пути к файлам
DATA_FILE = "data/paronyms.json"
STATS_FILE = "data/user_stats.json"
