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

# MongoDB URI (по умолчанию отключено для Render)
MONGODB_URI = os.getenv("MONGODB_URI", None)

# Использовать MongoDB или SQLite (по умолчанию SQLite для Render)
USE_MONGODB = os.getenv("USE_MONGODB", "false").lower() == "true" and MONGODB_URI is not None

# Пути к файлам
QUESTIONS_FILE = "data/questions.json"
ANSWERS_FILE = "data/answers.json"
STATS_FILE = "data/user_stats.json"
