"""
Конфигурационный файл бота.
Здесь хранятся настройки и токен бота.
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Пути к файлам
DATA_FILE = "data/paronyms.json"
STATS_FILE = "data/user_stats.json"
