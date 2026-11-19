"""
Единственное место регистрации хендлеров и инициализации хранилища.

И polling-режим (main.py), и webhook-режим (web_app.py) собирают бота этой
функцией, поэтому набор хендлеров всегда одинаковый.
"""

import logging

import telebot

from config import MONGODB_DB, MONGODB_URI, effective_token
from handlers.callbacks import (
    handle_answer,
    handle_legacy_answer,
    show_leaderboard,
    show_main_menu,
    show_stats,
    start_training,
)
from handlers.start import cmd_count, cmd_help, cmd_start, cmd_top
from handlers.text_handler import handle_text_check
from utils.data_manager import data_manager, init_data_manager
from utils.mongo_database import MongoDatabase

logger = logging.getLogger(__name__)


def init_storage(storage=None, manager=data_manager):
    """
    Подключает MongoDB как единственное хранилище статистики.

    SQLite и in-memory кэш удалены намеренно: ник, username, число верных
    ответов и лучшая серия живут только в MongoDB.
    """
    if storage is None:
        storage = MongoDatabase(MONGODB_URI, db_name=MONGODB_DB)
    init_data_manager(storage, manager=manager)
    return storage


def shutdown_storage(storage=None):
    """Закрывает соединение с MongoDB. Идемпотентно."""
    if storage is not None:
        storage.close()


def register_handlers(bot: telebot.TeleBot) -> telebot.TeleBot:
    """Регистрирует команды, текстовый обработчик и callback-обработчики."""

    @bot.message_handler(commands=["start"])
    def _start(message):
        cmd_start(message, bot)

    @bot.message_handler(commands=["help"])
    def _help(message):
        cmd_help(message, bot)

    @bot.message_handler(commands=["top"])
    def _top(message):
        cmd_top(message, bot)

    @bot.message_handler(commands=["count"])
    def _count(message):
        cmd_count(message, bot)

    @bot.message_handler(func=lambda m: True, content_types=["text"])
    def _text(message):
        if not message.text.startswith("/"):
            handle_text_check(message, bot)

    @bot.callback_query_handler(func=lambda call: call.data == "main_menu")
    def _main_menu(call):
        show_main_menu(call, bot)

    @bot.callback_query_handler(func=lambda call: call.data == "training_start")
    def _training(call):
        start_training(call, bot)

    @bot.callback_query_handler(func=lambda call: call.data == "stats")
    def _stats(call):
        show_stats(call, bot)

    @bot.callback_query_handler(func=lambda call: call.data == "leaderboard")
    def _leaderboard(call):
        show_leaderboard(call, bot)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("a:"))
    def _answer(call):
        handle_answer(call, bot)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("answer_"))
    def _legacy(call):
        handle_legacy_answer(call, bot)

    return bot


def build_bot(token: str | None = None) -> telebot.TeleBot:
    """Создаёт бота с зарегистрированными хендлерами."""
    # Без реального токена подставляется валидная заглушка: модули можно
    # импортировать и собирать Flask-приложение в тестах и CI.
    bot = telebot.TeleBot(token or effective_token(), threaded=False)
    return register_handlers(bot)
