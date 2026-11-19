"""
Команды бота: /start, /top, /count, /help.
"""

import logging

from handlers.callbacks import send_leaderboard, stats_text
from keyboards.inline import get_back_to_menu_keyboard, get_main_menu_keyboard
from utils.data_manager import data_manager

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "👋 Добро пожаловать в бота для подготовки к ЕГЭ!\n\n"
    "Этот бот поможет вам освоить паронимы и лексические нормы (Задание 5).\n\n"
    "*Выберите режим работы:*"
)

HELP_TEXT = (
    "*Команды бота*\n\n"
    "/start — главное меню\n"
    "/top — таблица лидеров (топ-20)\n"
    "/count — ваша статистика\n"
    "/help — эта справка"
)


def _notify_failure(bot, chat_id: int, text: str) -> None:
    """Сообщает пользователю о сбое хранилища, не падая повторно."""
    try:
        bot.send_message(chat_id, text)
    except Exception as e:
        logger.error("Не удалось отправить сообщение об ошибке: %s", e)


def cmd_start(message, bot):
    """Показывает приветствие и главное меню."""
    try:
        logger.info("/start от user_id=%s", message.from_user.id)
        bot.send_message(
            message.chat.id,
            WELCOME_TEXT,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Ошибка отправки приветствия: %s", e, exc_info=True)


def cmd_help(message, bot):
    """Показывает справку по командам."""
    try:
        bot.send_message(
            message.chat.id,
            HELP_TEXT,
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Ошибка отправки справки: %s", e, exc_info=True)


def cmd_top(message, bot):
    """Показывает таблицу лидеров (топ-20)."""
    try:
        logger.info("/top от user_id=%s", message.from_user.id)
        send_leaderboard(bot, message.chat.id)
    except Exception as e:
        logger.error("Ошибка отправки таблицы лидеров: %s", e, exc_info=True)
        _notify_failure(bot, message.chat.id, "Таблица лидеров временно недоступна.")


def cmd_count(message, bot):
    """Показывает статистику пользователя."""
    try:
        logger.info("/count от user_id=%s", message.from_user.id)
        user = message.from_user
        stats = data_manager.get_user_stats(user.id, user.username, user.first_name)
        bot.send_message(
            message.chat.id,
            stats_text(stats),
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Ошибка отправки статистики: %s", e, exc_info=True)
        _notify_failure(bot, message.chat.id, "Статистика временно недоступна. Попробуйте позже.")
