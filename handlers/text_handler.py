"""
Обработчик текстовых сообщений для тренировки.
"""

import logging
from keyboards.inline import get_main_menu_keyboard
from utils.data_manager import DataManager

data_manager = DataManager()
logger = logging.getLogger(__name__)

# Хранилище текущих вопросов пользователей (импортируем из callbacks)
current_questions = {}


def handle_text_check(message, bot):
    """Обрабатывает текстовое сообщение - теперь не используется, ответы через кнопки."""
    bot.send_message(
        message.chat.id,
        "Пожалуйста, используйте кнопки для выбора ответа.",
        reply_markup=get_main_menu_keyboard()
    )


def set_current_questions(questions_dict):
    """Устанавливает словарь текущих вопросов."""
    global current_questions
    current_questions = questions_dict
