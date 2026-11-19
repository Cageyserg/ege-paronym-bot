"""
Webhook-режим для Render: Flask + gunicorn.

Запуск: gunicorn -w 1 --threads 8 web_app:app

Статистика хранится только в MongoDB, поэтому несколько воркеров безопасны:
каждый ответ пишется атомарным апдейтом, кэша в памяти нет.
"""

import atexit
import logging
import signal

import telebot
from flask import Flask, jsonify, request

from config import ADMIN_TOKEN, WEBHOOK_SECRET, WEBHOOK_URL, is_configured
from core.bot_core import build_bot, init_storage, shutdown_storage
from utils.mongo_database import StorageUnavailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def webhook_authorized(headers) -> bool:
    """Проверяет секретный заголовок Telegram, если секрет настроен."""
    if not WEBHOOK_SECRET:
        return True
    return headers.get("X-Telegram-Bot-Api-Secret-Token") == WEBHOOK_SECRET


def admin_authorized(headers, args) -> bool:
    """Админ-маршруты доступны только при заданном ADMIN_TOKEN."""
    if not ADMIN_TOKEN:
        return False
    token = headers.get("X-Admin-Token") or args.get("token", "")
    return token == ADMIN_TOKEN


def create_app(bot: telebot.TeleBot) -> Flask:
    """Собирает Flask-приложение вокруг готового бота (удобно тестировать)."""
    app = Flask(__name__)

    @app.route("/webhook", methods=["POST"])
    def webhook():
        if not webhook_authorized(request.headers):
            logger.warning("Webhook: неверный секретный заголовок")
            return "", 403
        if request.headers.get("content-type") != "application/json":
            logger.warning("Webhook: неверный content-type %s",
                           request.headers.get("content-type"))
            return "Bad Request", 400
        try:
            update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
            bot.process_new_updates([update])
            return "", 200
        except Exception as e:
            logger.error("Webhook error: %s", e, exc_info=True)
            return "Internal Server Error", 500

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/")
    def index():
        return "Bot working! 🤖"

    @app.route("/set-webhook", methods=["POST"])
    def set_webhook():
        if not admin_authorized(request.headers, request.args):
            return "Forbidden", 403
        if not WEBHOOK_URL:
            return "WEBHOOK_URL не задан", 400
        url = f"{WEBHOOK_URL.rstrip('/')}/webhook"
        bot.remove_webhook()
        bot.set_webhook(url=url, secret_token=WEBHOOK_SECRET or None,
                        allowed_updates=["message", "callback_query"])
        logger.info("Webhook установлен: %s", url)
        return f"Webhook set to {url}"

    @app.route("/delete-webhook", methods=["POST"])
    def delete_webhook():
        if not admin_authorized(request.headers, request.args):
            return "Forbidden", 403
        bot.remove_webhook()
        return "Webhook removed"

    return app


# Модульные объекты для gunicorn: bot создаётся и хранилище инициализируется один раз.
bot = build_bot()
storage = None
try:
    storage = init_storage()
except StorageUnavailable as e:
    # Сервер поднимается, чтобы отдавать /health и лог ошибки; хендлеры
    # статистики будут отвечать ошибкой, пока MONGODB_URI не задан.
    logger.error("MongoDB недоступна: %s", e)

if not is_configured():
    logger.error("BOT_TOKEN не задан: сервер поднимется, но бот не будет отвечать.")
if storage is not None:
    atexit.register(shutdown_storage, storage)


def _signal_handler(signum, frame):
    raise SystemExit(0)


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

app = create_app(bot)


if __name__ == "__main__":
    if not is_configured():
        logger.error("BOT_TOKEN не задан — webhook-сервер не запущен.")
        raise SystemExit(1)
    app.run(host="0.0.0.0", port=5000)
