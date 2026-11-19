"""
Конфигурация бота. Все значения берутся из переменных окружения (.env).
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Токен бота от @BotFather (обязателен для запуска).
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Заглушка формально валидного токена: позволяет импортировать модули и
# собирать Flask-приложение без реальных секретов (тесты, CI, локальная отладка).
PLACEHOLDER_TOKEN = "0:PLACEHOLDER"


def effective_token() -> str:
    """Токен для конструктора TeleBot: реальный или валидная заглушка."""
    return BOT_TOKEN if is_configured() else PLACEHOLDER_TOKEN

# Публичный адрес приложения на Render (используется в webhook-режиме).
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")

# Секрет для проверки заголовка X-Telegram-Bot-Api-Secret-Token.
# Пустая строка = проверка выключена (не рекомендуется для публичного деплоя).
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# Токен для ручного вызова /set-webhook. Пусто = маршрут отключён.
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# MongoDB — единственное хранилище статистики (ник, username, верные ответы,
# лучшая серия). Обязателен всегда: локального фолбэка нет.
MONGODB_URI = os.getenv("MONGODB_URI") or None

# Имя базы внутри кластера MongoDB.
MONGODB_DB = os.getenv("MONGODB_DB", "ege_paronym_bot")

# Максимальное число активных тренировок в памяти (это состояние игры, а не
# статистика; статистика целиком в MongoDB).
MAX_TRACKED_USERS = int(os.getenv("MAX_TRACKED_USERS", "50000"))


def is_configured() -> bool:
    """True, если задан настоящий токен бота (а не заглушка)."""
    return bool(BOT_TOKEN) and BOT_TOKEN != "YOUR_BOT_TOKEN_HERE"


def is_storage_configured() -> bool:
    """True, если задан MONGODB_URI — без него статистику хранить негде."""
    return bool(MONGODB_URI)
