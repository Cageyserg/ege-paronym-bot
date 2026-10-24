"""
Обработчики команд бота.
"""

import logging
from keyboards.inline import get_main_menu_keyboard, get_leaderboard_keyboard, get_back_to_menu_keyboard
from handlers.callbacks import show_stats, leaderboard_message_ids
from utils.data_manager import DataManager

logger = logging.getLogger(__name__)
data_manager = DataManager()


def cmd_start(message, bot):
    """Обрабатывает команду /start и показывает главное меню."""
    try:
        logger.info(f"Получена команда /start от user_id={message.from_user.id}")
        bot.send_message(
            message.chat.id,
            "👋 Добро пожаловать в бота для подготовки к ЕГЭ!\n\n"
            "Этот бот поможет вам освоить паронимы и лексические нормы (Задание 5).\n\n"
            "*Выберите режим работы:*",
            reply_markup=get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
        logger.info(f"Сообщение отправлено в chat_id={message.chat.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}", exc_info=True)


def cmd_top(message, bot):
    """Обрабатывает команду /top и показывает таблицу лидеров (топ 20)."""
    try:
        logger.info(f"Получена команда /top от user_id={message.from_user.id}")
        chat_id = message.chat.id
        leaderboard = data_manager.get_leaderboard(limit=20)

        # Удаляем старое сообщение таблицы лидеров, если оно есть
        if chat_id in leaderboard_message_ids:
            try:
                bot.delete_message(chat_id, leaderboard_message_ids[chat_id])
            except Exception as e:
                pass  # Сообщение уже удалено или недоступно
            del leaderboard_message_ids[chat_id]

        if not leaderboard:
            msg = bot.send_message(
                chat_id,
                "*Таблица лидеров*\n\n"
                "Пока нет участников. Станьте первым!",
                reply_markup=get_main_menu_keyboard(),
                parse_mode='Markdown'
            )
            leaderboard_message_ids[chat_id] = msg.message_id
            return

        text = "*Таблица лидеров (топ 20)*\n\n"
        for entry in leaderboard:
            username = entry['username'] or f"User {entry['user_id']}"
            text += f"{entry['rank']}. {username} — {entry['correct_answers']}\n"

        msg = bot.send_message(
            chat_id,
            text,
            reply_markup=get_leaderboard_keyboard(),
            parse_mode='Markdown'
        )
        leaderboard_message_ids[chat_id] = msg.message_id
        logger.info(f"Таблица лидеров отправлена в chat_id={chat_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке таблицы лидеров: {e}", exc_info=True)


def cmd_count(message, bot):
    """Обрабатывает команду /count и показывает количество правильных ответов."""
    try:
        logger.info(f"Получена команда /count от user_id={message.from_user.id}")
        user_id = message.from_user.id
        username = message.from_user.username
        firstname = message.from_user.first_name
        stats = data_manager.get_user_stats(user_id, username, firstname)

        correct = stats['correct_answers']
        display_username = stats.get('username', username or 'Anonymous')
        display_firstname = stats.get('firstname', firstname or '')

        if display_firstname:
            user_info = f"@{display_username} ({display_firstname})"
        else:
            user_info = f"@{display_username}"

        text = (
            f"*Ваша статистика*\n\n"
            f"Пользователь: {user_info}\n"
            f"Правильных ответов: {correct}"
        )

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=get_back_to_menu_keyboard(),
            parse_mode='Markdown'
        )
        logger.info(f"Статистика отправлена в chat_id={message.chat.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке статистики: {e}", exc_info=True)
